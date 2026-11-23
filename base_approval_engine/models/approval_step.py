from odoo import fields, models


class ApprovalStep(models.Model):
    _name = 'approval.step'
    _description = 'Paso de Aprobación'
    _order = 'sequence, id'

    rule_id = fields.Many2one('approval.rule', required=True, ondelete='cascade')
    sequence = fields.Integer('Secuencia', default=10)
    name = fields.Char('Nombre del Paso', required=True)
    group_id = fields.Many2one('res.groups', string='Grupo Requerido')
    user_id = fields.Many2one('res.users', string='Usuario Requerido')
