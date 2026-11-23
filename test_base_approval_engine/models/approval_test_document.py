from odoo import fields, models


class ApprovalTestDocument(models.Model):
    _name = 'approval.test.document'
    _inherit = ['approval.mixin']
    _description = 'Documento de prueba para el motor de aprobaciones'

    name = fields.Char(required=True)
    amount = fields.Float()
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Confirmado'),
        ('refused', 'Rechazado'),
    ], default='draft')

    def action_confirm(self):
        """Ejemplo de integración: los documentos que requieren aprobación se detienen."""
        to_approve = self._request_approval()
        (self - to_approve).write({'state': 'done'})
        return True

    def action_approval_granted(self):
        res = super().action_approval_granted()
        self.sudo().action_confirm()
        return res

    def action_approval_rejected(self):
        res = super().action_approval_rejected()
        self.sudo().write({'state': 'refused'})
        return res
