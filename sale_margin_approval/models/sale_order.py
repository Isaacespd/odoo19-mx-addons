from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection(
        selection_add=[('waiting_approval', 'Esperando Aprobación')],
        ondelete={'waiting_approval': 'set default'},
    )
    margin_percent_display = fields.Float(
        string='Margen (%)', compute='_compute_margin_percent_display',
        help='Margen sobre el subtotal sin impuestos.')

    @api.depends('margin', 'amount_untaxed')
    def _compute_margin_percent_display(self):
        for order in self:
            order.margin_percent_display = (
                order.margin / order.amount_untaxed * 100.0 if order.amount_untaxed else 0.0)

    def _needs_margin_approval(self):
        self.ensure_one()
        min_margin = self.company_id.min_margin_percentage
        return (
            min_margin > 0.0
            and self.state in ('draft', 'sent')
            and float_compare(self.margin_percent_display, min_margin, precision_digits=2) < 0
        )

    def action_confirm(self):
        if self.env.context.get('skip_margin_check'):
            return super().action_confirm()

        to_approve = self.filtered(lambda o: o._needs_margin_approval())
        for order in to_approve:
            order.state = 'waiting_approval'
            order.message_post(body=self.env._(
                'La cotización requiere aprobación gerencial por bajo margen. '
                'Margen actual: %(current).2f%% (mínimo requerido: %(minimum).2f%%).',
                current=order.margin_percent_display,
                minimum=order.company_id.min_margin_percentage,
            ))

        to_confirm = self - to_approve
        if to_confirm:
            return super(SaleOrder, to_confirm).action_confirm()
        return True

    def _check_margin_approver(self):
        if not self.env.user.has_group('sale_margin_approval.group_sale_margin_approver'):
            raise AccessError(self.env._('No tienes permisos para aprobar o rechazar márgenes de venta.'))

    def action_approve_margin(self):
        self._check_margin_approver()
        orders = self.filtered(lambda o: o.state == 'waiting_approval')
        # action_confirm solo acepta cotizaciones en borrador/enviadas.
        orders.write({'state': 'draft'})
        orders.with_context(skip_margin_check=True).action_confirm()
        for order in orders:
            order.message_post(body=self.env._(
                'Venta aprobada con margen de %(margin).2f%% por %(user)s.',
                margin=order.margin_percent_display, user=self.env.user.name))
        return True

    def action_reject_margin(self):
        self._check_margin_approver()
        orders = self.filtered(lambda o: o.state == 'waiting_approval')
        orders.write({'state': 'draft'})
        for order in orders:
            order.message_post(body=self.env._(
                'Venta rechazada por bajo margen por %s. Ajusta los precios y vuelve a confirmar.',
                self.env.user.name))
        return True
