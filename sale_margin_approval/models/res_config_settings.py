from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    min_margin_percentage = fields.Float(
        related='company_id.min_margin_percentage',
        readonly=False,
        string='Margen Mínimo Permitido (%)'
    )
