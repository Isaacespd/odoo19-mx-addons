from odoo import fields, models
from odoo.tools.safe_eval import safe_eval


class ApprovalMixin(models.AbstractModel):
    """Agrega aprobaciones multinivel a cualquier modelo.

    Uso en el modelo concreto::

        class HrExpense(models.Model):
            _name = 'hr.expense'
            _inherit = ['hr.expense', 'approval.mixin']

            def action_submit(self):
                to_approve = self._request_approval()
                return super(HrExpense, self - to_approve).action_submit()

            def action_approval_granted(self):
                super().action_approval_granted()
                self.action_submit()
    """
    _name = 'approval.mixin'
    _description = 'Mixin de Aprobaciones'

    approval_state = fields.Selection([
        ('none', 'Sin aprobación'),
        ('pending', 'Aprobación Pendiente'),
        ('approved', 'Aprobado'),
    ], string='Estado de Aprobación', default='none', readonly=True, copy=False)
    approval_request_id = fields.Many2one(
        'approval.request', string='Solicitud Activa', readonly=True, copy=False)

    def _check_approval_rules(self):
        """Devuelve la primera regla activa cuyo dominio cumple el registro, o False."""
        self.ensure_one()
        rules = self.env['approval.rule'].sudo().search([
            ('model_name', '=', self._name),
            ('active', '=', True),
        ])
        for rule in rules:
            domain = safe_eval(rule.domain or '[]') + [('id', '=', self.id)]
            if self.sudo().search_count(domain):
                return rule
        return False

    def _create_approval_request(self, rule):
        self.ensure_one()
        request = self.env['approval.request'].sudo().create({
            'rule_id': rule.id,
            'res_id': self.id,
            'res_model': self._name,
            'current_step_id': rule.step_ids.sorted('sequence')[:1].id,
        })
        self.write({'approval_state': 'pending', 'approval_request_id': request.id})
        return request

    def _request_approval(self):
        """Crea solicitudes para los registros que lo requieren y los devuelve.

        Los registros ya aprobados, pendientes o sin regla aplicable no se incluyen,
        así el modelo concreto puede continuar su flujo normal con el resto.
        """
        to_approve = self.browse()
        for record in self.filtered(lambda r: r.approval_state == 'none'):
            rule = record._check_approval_rules()
            if rule:
                record._create_approval_request(rule)
                to_approve |= record
        return to_approve | self.filtered(lambda r: r.approval_state == 'pending')

    # Callbacks que el modelo concreto extiende.
    # La aprobación del motor ya es la autorización: los campos de control se
    # escriben con sudo para no exigir permisos de escritura al aprobador.
    def action_approval_granted(self):
        self.sudo().write({'approval_state': 'approved'})

    def action_approval_rejected(self):
        self.sudo().write({'approval_state': 'none', 'approval_request_id': False})
