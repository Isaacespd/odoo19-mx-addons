from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    min_margin_percentage = fields.Float(
        string='Margen Mínimo Permitido (%)',
        default=0.0,
        help="Si el margen de una cotización es inferior a este porcentaje, se requerirá aprobación gerencial."
    )
