from odoo import models, fields

class PartnerRfcValidationLog(models.Model):
    _name = 'partner.rfc.validation.log'
    _description = 'Historial de Validaciones RFC'
    _order = 'create_date desc'

    name = fields.Char(string='Referencia', required=True, default='Validación Manual')
    date = fields.Datetime(string='Fecha', default=fields.Datetime.now, required=True)
    partners_affected = fields.Integer(string='Contactos Afectados')
    log_details = fields.Text(string='Detalles')
    status = fields.Selection([
        ('success', 'Éxito'),
        ('error', 'Error')
    ], string='Estado', default='success')
