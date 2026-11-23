from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    efos_block_invoicing = fields.Boolean(
        string='Bloquear facturación a EFOS',
        config_parameter='l10n_mx_partner_validator.efos_block_invoicing',
        help='Si está activo, no se podrá confirmar facturas de clientes marcados como EFOS.',
        default=True
    )

    efos_allow_vendor_bills = fields.Boolean(
        string='Permitir facturas de proveedores EFOS',
        config_parameter='l10n_mx_partner_validator.efos_allow_vendor_bills',
        help='Por defecto no se pueden confirmar facturas de proveedores marcados como EFOS, '
             'porque sus comprobantes no son deducibles. Actívalo solo si necesitas registrarlas.',
    )

    efos_list_url = fields.Char(
        string='URL Lista 69-B SAT',
        config_parameter='l10n_mx_partner_validator.efos_list_url',
        help='URL para descargar el CSV oficial del SAT',
        default='http://omawww.sat.gob.mx/cifras_sat/Documents/Listado_Completo_69-B.csv'
    )
