from odoo import fields, models


class ApprovalLog(models.Model):
    _name = 'approval.log'
    _description = 'Historial de Aprobaciones'
    _order = 'create_date desc'

    request_id = fields.Many2one('approval.request', required=True, ondelete='cascade')
    step_id = fields.Many2one('approval.step', string='Paso', ondelete='set null')
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    state = fields.Selection([
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado')
    ], required=True)
    comment = fields.Text('Comentario')
