from odoo import models, api


class StockPickingSummary(models.AbstractModel):
    _name = 'report.picking_summary_report.picking_summary_template'
    _description = 'Picking Summary Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        pickings = self.env['stock.picking'].browse(docids)

        # Build summary lines grouped by product category
        summary_lines = []
        serial = 1

        for picking in pickings:
            for move in picking.move_ids.sorted(
                key=lambda m: (
                    m.product_id.categ_id.complete_name or '',
                    m.product_id.name or ''
                )
            ):
                product = move.product_id
                category = product.categ_id

                summary_lines.append({
                    'sl_no': serial,
                    'picking_ref': picking.name,
                    'category': category.name or 'Uncategorised',
                    'source_location': picking.location_id.display_name or '',
                    'product': product.name or '',
                    'qty': move.product_uom_qty,
                    'uom': move.product_uom.name or '',
                    'destination': picking.location_dest_id.display_name or '',
                    'warehouse': picking.picking_type_id.warehouse_id.name or '',
                })
                serial += 1

        # Build a combined reference string for the header
        picking_refs = ', '.join(pickings.mapped('name'))

        # Unique warehouses
        warehouses = list(set(pickings.mapped(
            'picking_type_id.warehouse_id.name'
        )))

        return {
            'docs': pickings,
            'summary_lines': summary_lines,
            'picking_refs': picking_refs,
            'warehouses': warehouses,
            'total_lines': len(summary_lines),
        }
