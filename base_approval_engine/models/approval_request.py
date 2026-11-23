from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


class ApprovalRequest(models.Model):
    _name = 'approval.request'
    _description = 'Solicitud de Aprobación'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char('Referencia', required=True, readonly=True, copy=False, default=lambda self: self.env._('Nueva'))
    rule_id = fields.Many2one('approval.rule', required=True, readonly=True, ondelete='restrict')
    res_id = fields.Many2oneReference('ID del Documento', model_field='res_model', required=True, readonly=True)
    res_model = fields.Char('Modelo del Documento', required=True, readonly=True)
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ], default='pending', required=True, readonly=True, tracking=True)
    current_step_id = fields.Many2one('approval.step', 'Paso Actual', readonly=True, tracking=True)
    log_ids = fields.One2many('approval.log', 'request_id', readonly=True)
    can_review = fields.Boolean(compute='_compute_can_review')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == self.env._('Nueva'):
                vals['name'] = self.env['ir.sequence'].next_by_code('approval.request') or self.env._('Nueva')
        return super().create(vals_list)

    @api.depends_context('uid')
    @api.depends('state', 'current_step_id')
    def _compute_can_review(self):
        for request in self:
            request.can_review = request.state == 'pending' and request._user_can_review(self.env.user)

    # ------------------------------------------------------------------
    # Permisos
    # ------------------------------------------------------------------
    def _user_can_review(self, user):
        """Un usuario puede revisar el paso actual si es el usuario asignado, pertenece al
        grupo requerido, o es administrador de aprobaciones. Un paso sin usuario ni grupo
        lo puede revisar cualquier usuario de aprobaciones."""
        self.ensure_one()
        if user.has_group('base_approval_engine.group_approval_manager'):
            return True
        step = self.current_step_id
        if not step:
            return user.has_group('base_approval_engine.group_approval_user')
        if step.user_id:
            return step.user_id == user
        if step.group_id:
            return step.group_id in user.all_group_ids
        return user.has_group('base_approval_engine.group_approval_user')

    def _check_can_review(self):
        for request in self:
            if request.state != 'pending':
                raise UserError(self.env._('La solicitud %s ya no está pendiente.', request.name))
            if not request._user_can_review(self.env.user):
                raise AccessError(self.env._(
                    'No puedes revisar el paso "%(step)s" de la solicitud %(name)s.',
                    step=request.current_step_id.name or '-', name=request.name))

    # ------------------------------------------------------------------
    # Flujo
    # ------------------------------------------------------------------
    def _get_next_step(self):
        self.ensure_one()
        steps = self.rule_id.step_ids.sorted('sequence')
        if not self.current_step_id:
            return steps[:1]
        index = list(steps).index(self.current_step_id) if self.current_step_id in steps else -1
        return steps[index + 1] if 0 <= index < len(steps) - 1 else self.env['approval.step']

    def _get_target_record(self):
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id).exists()

    def action_approve(self, comment=False):
        self._check_can_review()
        for request in self:
            # Los usuarios solo tienen lectura sobre solicitudes y bitácora; las
            # escrituras pasan por aquí después de validar permisos.
            request_sudo = request.sudo()
            request_sudo.env['approval.log'].create({
                'request_id': request.id,
                'user_id': self.env.user.id,
                'step_id': request.current_step_id.id,
                'state': 'approved',
                'comment': comment,
            })
            next_step = request._get_next_step()
            if next_step:
                request_sudo.current_step_id = next_step
                request_sudo.message_post(body=self.env._('Paso aprobado por %(user)s. Siguiente paso: %(step)s.',
                                                 user=self.env.user.name, step=next_step.name))
                continue
            request_sudo.write({'state': 'approved', 'current_step_id': False})
            request_sudo.message_post(body=self.env._('Solicitud aprobada por %s.', self.env.user.name))
            target = request._get_target_record()
            if target and hasattr(target, 'action_approval_granted'):
                target.action_approval_granted()
        return True

    def action_reject(self, comment=False):
        self._check_can_review()
        for request in self:
            request_sudo = request.sudo()
            request_sudo.env['approval.log'].create({
                'request_id': request.id,
                'user_id': self.env.user.id,
                'step_id': request.current_step_id.id,
                'state': 'rejected',
                'comment': comment,
            })
            request_sudo.write({'state': 'rejected', 'current_step_id': False})
            request_sudo.message_post(body=self.env._('Solicitud rechazada por %s.', self.env.user.name))
            target = request._get_target_record()
            if target and hasattr(target, 'action_approval_rejected'):
                target.action_approval_rejected()
        return True
