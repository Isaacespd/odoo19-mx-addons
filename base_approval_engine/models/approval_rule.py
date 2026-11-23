from odoo import fields, models


class ApprovalRule(models.Model):
    _name = 'approval.rule'
    _description = 'Regla de Aprobación'

    name = fields.Char('Nombre', required=True)
    model_id = fields.Many2one('ir.model', string='Modelo', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model', readonly=True, store=True)
    domain = fields.Char('Condición (Dominio)', required=True, default="[]")
    step_ids = fields.One2many('approval.step', 'rule_id', string='Pasos de Aprobación')
    active = fields.Boolean(default=True)
