from odoo import fields, models
from odoo.exceptions import UserError

CUSTOMER_TYPES = ('out_invoice', 'out_refund')
VENDOR_TYPES = ('in_invoice', 'in_refund')


class AccountMove(models.Model):
    _inherit = 'account.move'

    partner_is_efos = fields.Boolean(related='partner_id.commercial_partner_id.is_efos', string='Contacto EFOS')

    def action_post(self):
        params = self.env['ir.config_parameter'].sudo()
        block_customers = params.get_param('l10n_mx_partner_validator.efos_block_invoicing')
        # El bloqueo a proveedores está activo salvo que se permita explícitamente:
        # deducir facturas de un EFOS definitivo es el riesgo fiscal principal del 69-B.
        allow_vendors = params.get_param('l10n_mx_partner_validator.efos_allow_vendor_bills')

        for move in self:
            partner = move.partner_id.commercial_partner_id
            if not partner.is_efos:
                continue
            if block_customers and move.move_type in CUSTOMER_TYPES:
                raise UserError(self.env._('No se puede facturar a una empresa EFOS (69-B): %s', partner.name))
            if not allow_vendors and move.move_type in VENDOR_TYPES:
                raise UserError(self.env._(
                    'El proveedor %s está como Definitivo en el listado 69-B del SAT (EFOS). '
                    'Sus comprobantes no son deducibles. Si necesitas registrarla de todos modos, '
                    'activa "Permitir facturas de proveedores EFOS" en Ajustes de Contabilidad.',
                    partner.name))
        return super().action_post()
