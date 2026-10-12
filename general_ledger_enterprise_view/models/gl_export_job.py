# License: LGPL-3.0 or later
"""Background XLSX export for very large General Ledger / Trial Balance
reports.

Update: the workbook is now written to a TEMP FILE on disk (xlsxwriter
constant_memory + path) instead of io.BytesIO, so the worker no longer holds
the whole workbook twice in RAM. Only the final base64 copy for the Binary
field is in memory (unavoidable with a Binary field).

Operations note: the cron worker is subject to ``limit_time_real_cron``
(falls back to ``limit_time_real``, 120 s by default). For multi-100k-line
exports raise it in odoo.conf (e.g. ``limit_time_real_cron = 1800``) and
check ``limit_memory_hard``.
"""
import base64
import json
import logging
import os
import tempfile
import urllib.parse
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import config

_logger = logging.getLogger(__name__)

_MAX_OPEN_JOBS_PER_USER = 3
_MAX_FILTERS_SIZE = 100_000  # characters of JSON
_KEEP_DAYS = 3
_STALE_HOURS = 3  # a job "processing" longer than this lost its worker
_JOBS_PER_CRON_RUN = 1  # one big export per run: stays inside limit_time_real_cron


class GlExportJob(models.Model):
    _name = "gl.export.job"
    _description = "General Ledger background export"
    _order = "id desc"

    name = fields.Char(required=True, readonly=True)
    user_id = fields.Many2one(
        "res.users", string="Requested by", required=True, readonly=True,
        index=True, ondelete="cascade", default=lambda self: self.env.user,
    )
    company_id = fields.Many2one("res.company", readonly=True)
    report_type = fields.Selection(
        [("gl", "General Ledger"), ("tb", "Trial Balance")], readonly=True)
    export_format = fields.Selection([("xlsx", "XLSX")], default="xlsx", readonly=True)
    filters_json = fields.Text(readonly=True)
    row_estimate = fields.Integer(string="Lines", readonly=True)
    state = fields.Selection(
        [("queued", "Queued"), ("processing", "Processing"),
         ("done", "Done"), ("failed", "Failed")],
        default="queued", readonly=True, index=True,
    )
    file = fields.Binary(attachment=True, readonly=True)
    file_name = fields.Char(readonly=True)
    error_message = fields.Text(readonly=True)
    date_done = fields.Datetime(readonly=True)

    # ------------------------------------------------------------------
    # Queueing (called by the export_file route)
    # ------------------------------------------------------------------
    @api.model
    def _queue_export(self, filters, export_format, rows):
        """Create (or reuse) a queued job for the CURRENT user."""
        user = self.env.user
        payload = json.dumps(filters, sort_keys=True, default=str)
        if len(payload) > _MAX_FILTERS_SIZE:
            raise UserError(_("The export filters are too large."))
        Job = self.sudo()
        open_jobs = Job.search([
            ("user_id", "=", user.id), ("state", "in", ("queued", "processing")),
        ])
        same = open_jobs.filtered(
            lambda j: j.filters_json == payload and j.export_format == export_format)
        if same:
            return same[0]  # double click: do not queue the same export twice
        if len(open_jobs) >= _MAX_OPEN_JOBS_PER_USER:
            raise UserError(_(
                "You already have %(n)s exports waiting. Please wait until "
                "they are finished (Accounting > Reporting > Enterprise "
                "Reports > Export Files).", n=len(open_jobs)))
        company_id = filters.get("company_id")
        company = (self.env["res.company"].browse(int(company_id))
                   if company_id else self.env.company)
        report_type = filters.get("report_type", "gl")
        job = Job.create({
            "name": "%s %s → %s" % (
                "TB" if report_type == "tb" else "GL",
                filters.get("date_from"), filters.get("date_to")),
            "user_id": user.id,
            "company_id": company.id,
            "report_type": "tb" if report_type == "tb" else "gl",
            "export_format": export_format,
            "filters_json": payload,
            "row_estimate": rows,
        })
        try:
            cron = self.env.ref(
                "general_ledger_enterprise_view.ir_cron_gl_export_process",
                raise_if_not_found=False)
            if cron:
                cron.sudo()._trigger()  # run soon instead of waiting
        except Exception:  # noqa: BLE001 - the regular schedule still picks it up
            _logger.debug("Could not trigger the GL export cron", exc_info=True)
        return job

    # ------------------------------------------------------------------
    # Processing (cron)
    # ------------------------------------------------------------------
    def _check_user_can_export(self, user):
        if not user.has_group("account.group_account_user"):
            raise AccessError(_(
                "You do not have access to General Ledger. Accounting access required."))

    def _commit(self):
        """Persist progress between jobs (no-op while running tests)."""
        if not config["test_enable"]:
            self.env.cr.commit()  # pylint: disable=invalid-commit

    def _notify(self, title, message, notif_type):
        try:
            self.env["bus.bus"]._sendone(
                self.user_id.partner_id, "simple_notification",
                {"title": title, "message": message, "type": notif_type, "sticky": True},
            )
        except Exception:  # noqa: BLE001 - a lost toast must never fail the job
            _logger.debug("GL export notification failed", exc_info=True)

    def _build_file(self):
        """Build the workbook as the requesting user.

        Returns (bytes, filename). The workbook is written to a temp file on
        disk first, then read once; the temp dir is always removed.
        """
        # Imported here: the controller module is loaded after the models.
        from odoo.addons.general_ledger_enterprise_view.controllers import main as gl_main

        self.ensure_one()
        user = self.user_id
        self._check_user_can_export(user)
        filters = json.loads(self.filters_json or "{}")
        company = self.company_id or user.company_id
        env = self.with_user(user).with_context(
            allowed_company_ids=[company.id]).env
        report_type, data = gl_main._compute_streaming_xlsx_data(
            env, filters, in_background=True)
        controller = gl_main.GeneralLedgerEnterpriseController()
        with tempfile.TemporaryDirectory(prefix="gl_export_") as tmpdir:
            path = os.path.join(tmpdir, "report.xlsx")
            _none, filename = controller._build_xlsx(
                env, report_type, data, filters, path=path)
            with open(path, "rb") as fh:
                content = fh.read()
        return content, filename

    def _process(self):
        """Run ONE queued job. Never raises: failures are stored on the job."""
        self.ensure_one()
        self.flush_model(["state"])
        self.env.cr.execute(
            "SELECT id FROM gl_export_job WHERE id = %s AND state = 'queued' "
            "FOR UPDATE SKIP LOCKED", [self.id])
        if not self.env.cr.fetchone():
            return  # already taken by another worker
        self.write({"state": "processing"})
        self.env.flush_all()
        self._commit()
        try:
            with self.env.cr.savepoint():
                content, filename = self._build_file()
            encoded = base64.b64encode(content)
            del content  # free the raw copy before the write
            self.write({
                "state": "done",
                "file": encoded,
                "file_name": filename,
                "date_done": fields.Datetime.now(),
                "error_message": False,
            })
            del encoded
            self._notify(
                _("Export ready"),
                _("%(name)s is ready: Accounting > Reporting > Enterprise "
                  "Reports > Export Files.", name=self.name),
                "success")
        except Exception as exc:  # noqa: BLE001 - recorded, not raised
            _logger.exception("GL background export %s failed", self.id)
            self.write({
                "state": "failed",
                "error_message": str(exc)[:2000],
                "date_done": fields.Datetime.now(),
            })
            self._notify(
                _("Export failed"),
                _("%(name)s could not be created: %(err)s",
                  name=self.name, err=str(exc)[:200]),
                "danger")
        self._commit()

    @api.model
    def _cron_process_jobs(self):
        # A worker that died leaves a job in "processing": release it.
        limit = fields.Datetime.now() - timedelta(hours=_STALE_HOURS)
        stale = self.search([("state", "=", "processing"), ("write_date", "<", limit)])
        if stale:
            stale.write({
                "state": "failed",
                "error_message": _("The export was interrupted (server restart or time limit)."),
            })
            self._commit()
        for job in self.search([("state", "=", "queued")], order="id",
                               limit=_JOBS_PER_CRON_RUN):
            job._process()
        # Jobs still waiting: schedule the next run right away instead of
        # waiting for the 5-minute interval (each run handles one job).
        if self.search_count([("state", "=", "queued")]):
            try:
                cron = self.env.ref(
                    "general_ledger_enterprise_view.ir_cron_gl_export_process",
                    raise_if_not_found=False)
                if cron:
                    cron.sudo()._trigger()
                    self._commit()
            except Exception:  # noqa: BLE001 - the regular schedule still picks it up
                _logger.debug("Could not re-trigger the GL export cron", exc_info=True)

    @api.model
    def _cron_vacuum_jobs(self):
        limit = fields.Datetime.now() - timedelta(days=_KEEP_DAYS)
        self.search([("create_date", "<", limit),
                     ("state", "in", ("done", "failed"))]).unlink()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def action_download(self):
        self.ensure_one()
        if self.state != "done" or not self.file:
            raise UserError(_("This export is not ready yet."))
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s/%s/file/%s?download=true" % (
                self._name, self.id, urllib.parse.quote(self.file_name or "export.xlsx")),
            "target": "self",
        }