from odoo import models , fields , api , _
from odoo.exceptions import ValidationError

class PurchaseOrder(models.Model):
     _inherit="purchase_order"

     partner_ref= fields.Char(required=True)