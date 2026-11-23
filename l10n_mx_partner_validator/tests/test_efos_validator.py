from unittest.mock import patch

import requests

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged

from ..models.res_partner import normalize_rfc

# Réplica reducida del CSV real del SAT: latin-1, dos renglones de título
# antes del encabezado y las cuatro situaciones posibles.
SAT_CSV = (
    '"Información actualizada al 31 de diciembre de 2025",,,,\n'
    'Listado completo de contribuyentes (Artículo 69-B del CFF),,,,\n'
    'No,RFC,Nombre del Contribuyente,Situación del contribuyente,Otra columna\n'
    '1,EFO010101AA1,"EMPRESA FANTASMA, S.A. DE C.V.",Definitivo,x\n'
    '2,PRE010101AA1,EMPRESA PRESUNTA SA DE CV,Presunto,x\n'
    '3,DES010101AA1,EMPRESA DESVIRTUADA SA DE CV,Desvirtuado,x\n'
    '4,SEN010101AA1,EMPRESA CON SENTENCIA SA DE CV,Sentencia Favorable,x\n'
    '5,XAXX010101000,RFC GENERICO MAL CAPTURADO,Definitivo,x\n'
).encode('latin-1')

PARTNER_MODEL = 'odoo.addons.l10n_mx_partner_validator.models.res_partner.ResPartner'


@tagged('post_install', '-at_install')
class TestEfosValidator(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env['res.partner']
        cls.partner_generic = Partner.create({'name': 'Público en General', 'vat': 'XAXX010101000'})
        cls.partner_foreign = Partner.create({'name': 'Cliente Extranjero', 'vat': 'XEXX010101000'})
        cls.partner_efos = Partner.create({'name': 'Empresa Fantasma', 'vat': 'mx efo-010101-aa1'})
        cls.partner_presunto = Partner.create({'name': 'Empresa Presunta', 'vat': 'PRE010101AA1'})
        cls.partner_sentencia = Partner.create({'name': 'Empresa Sentencia', 'vat': 'SEN010101AA1'})
        cls.partner_clean = Partner.create({'name': 'Empresa Limpia', 'vat': 'LIM010101AB1'})
        cls.all_partners = (cls.partner_generic | cls.partner_foreign | cls.partner_efos
                            | cls.partner_presunto | cls.partner_sentencia | cls.partner_clean)
        cls.env['ir.config_parameter'].sudo().set_param(
            'l10n_mx_partner_validator.efos_block_invoicing', 'True')

    def _sync_with(self, csv_content=SAT_CSV, side_effect=None):
        situations = None if side_effect else self.env['res.partner']._parse_efos_csv(csv_content)
        with patch(f'{PARTNER_MODEL}._download_efos_list',
                   return_value=situations, side_effect=side_effect):
            return self.all_partners._sync_efos('Test')

    def _last_log(self):
        return self.env['partner.rfc.validation.log'].search([], limit=1, order='id desc')

    # ------------------------------------------------------------------
    # Parseo y normalización
    # ------------------------------------------------------------------
    def test_normalize_rfc(self):
        self.assertEqual(normalize_rfc(' mx efo-010101-aa1 '), 'EFO010101AA1')
        self.assertEqual(normalize_rfc('MXAAAA800101AB1'), 'AAAA800101AB1')
        self.assertEqual(normalize_rfc(False), '')

    def test_parse_sat_csv(self):
        result = self.env['res.partner']._parse_efos_csv(SAT_CSV)
        self.assertEqual(result, {
            'EFO010101AA1': 'definitivo',
            'PRE010101AA1': 'presunto',
            'DES010101AA1': 'desvirtuado',
            'SEN010101AA1': 'sentencia_favorable',
        })

    def test_parse_duplicates_definitivo_prevails(self):
        csv_dup = (
            'No,RFC,Nombre,Situación del contribuyente\n'
            '1,FFF010101AA1,EMPRESA F,Definitivo\n'
            '2,FFF010101AA1,EMPRESA F,Sentencia Favorable\n'
            '3,GGG010101AA1,EMPRESA G,Presunto\n'
            '4,GGG010101AA1,EMPRESA G,Desvirtuado\n'
            '5,XXXXXXXXXXXX,RELLENO,Definitivo\n'
        ).encode('latin-1')
        result = self.env['res.partner']._parse_efos_csv(csv_dup)
        self.assertEqual(result, {'FFF010101AA1': 'definitivo', 'GGG010101AA1': 'presunto'})

    def test_parse_rejects_unexpected_file(self):
        with self.assertRaises(ValueError):
            self.env['res.partner']._parse_efos_csv(b'<html>Servicio no disponible</html>')

    # ------------------------------------------------------------------
    # Sincronización
    # ------------------------------------------------------------------
    def test_generic_rfcs_never_marked(self):
        """Regresión: los RFC genéricos del SAT no deben marcarse como EFOS."""
        self._sync_with()
        self.assertFalse(self.partner_generic.is_efos)
        self.assertFalse(self.partner_foreign.is_efos)
        self.assertFalse(self.partner_generic.l10n_mx_efos_situation)

    def test_sync_marks_only_definitivos(self):
        self.assertTrue(self._sync_with())
        self.assertTrue(self.partner_efos.is_efos)
        self.assertEqual(self.partner_efos.l10n_mx_efos_situation, 'definitivo')
        self.assertFalse(self.partner_presunto.is_efos)
        self.assertEqual(self.partner_presunto.l10n_mx_efos_situation, 'presunto')
        self.assertFalse(self.partner_clean.is_efos)
        self.assertFalse(self.partner_clean.l10n_mx_efos_situation)
        self.assertTrue(self.partner_clean.last_validation_date)
        log = self._last_log()
        self.assertEqual(log.status, 'success')
        self.assertEqual(log.partners_affected, 1)

    def test_sync_unmarks_partner_with_favorable_ruling(self):
        self.partner_sentencia.is_efos = True
        self._sync_with()
        self.assertFalse(self.partner_sentencia.is_efos)
        self.assertEqual(self.partner_sentencia.l10n_mx_efos_situation, 'sentencia_favorable')

    def test_download_error_keeps_partners_untouched(self):
        self.partner_efos.is_efos = True
        result = self._sync_with(side_effect=requests.ConnectionError('timeout'))
        self.assertFalse(result)
        self.assertTrue(self.partner_efos.is_efos)
        self.assertFalse(self.partner_clean.last_validation_date)
        self.assertEqual(self._last_log().status, 'error')

    def test_empty_list_keeps_partners_untouched(self):
        self.partner_efos.is_efos = True
        header_only = b'No,RFC,Nombre del Contribuyente,Situaci\xf3n del contribuyente\n'
        self.assertFalse(self._sync_with(csv_content=header_only))
        self.assertTrue(self.partner_efos.is_efos)
        self.assertEqual(self._last_log().status, 'error')

    def test_cron_checks_all_partners_with_rfc(self):
        situations = self.env['res.partner']._parse_efos_csv(SAT_CSV)
        with patch(f'{PARTNER_MODEL}._download_efos_list', return_value=situations):
            self.env['res.partner']._cron_check_efos_status()
        self.assertTrue(self.partner_efos.is_efos)
        self.assertFalse(self.partner_generic.is_efos)

    def test_manual_validation_flags_invalid_format(self):
        bad = self.env['res.partner'].create({'name': 'RFC Mal', 'vat': '123'})
        with patch(f'{PARTNER_MODEL}._download_efos_list') as download:
            bad.action_validate_rfc()
            download.assert_not_called()
        self.assertIn('no tiene un formato válido', bad.message_ids[0].body)

    # ------------------------------------------------------------------
    # Bloqueo de facturación
    # ------------------------------------------------------------------
    def test_block_invoice_to_efos(self):
        self.partner_efos.is_efos = True
        invoice = self.init_invoice('out_invoice', partner=self.partner_efos, amounts=[100.0])
        with self.assertRaises(UserError):
            invoice.action_post()

    def test_block_vendor_bill_from_efos_by_default(self):
        self.partner_efos.is_efos = True
        bill = self.init_invoice('in_invoice', partner=self.partner_efos, amounts=[100.0])
        self.assertTrue(bill.partner_is_efos)
        with self.assertRaisesRegex(UserError, 'no son deducibles'):
            bill.action_post()

    def test_vendor_bill_from_efos_allowed_when_enabled(self):
        self.partner_efos.is_efos = True
        self.env['ir.config_parameter'].sudo().set_param(
            'l10n_mx_partner_validator.efos_allow_vendor_bills', 'True')
        bill = self.init_invoice('in_invoice', partner=self.partner_efos, amounts=[100.0])
        bill.action_post()
        self.assertEqual(bill.state, 'posted')

    def test_block_uses_commercial_partner(self):
        """Una factura a un contacto hijo de la empresa EFOS también se bloquea."""
        self.partner_efos.is_efos = True
        contact = self.env['res.partner'].create({
            'name': 'Contador de la empresa', 'parent_id': self.partner_efos.id, 'type': 'invoice'})
        bill = self.init_invoice('in_invoice', partner=contact, amounts=[100.0])
        with self.assertRaises(UserError):
            bill.action_post()

    def test_customer_block_can_be_disabled(self):
        self.partner_efos.is_efos = True
        self.env['ir.config_parameter'].sudo().set_param(
            'l10n_mx_partner_validator.efos_block_invoicing', False)
        invoice = self.init_invoice('out_invoice', partner=self.partner_efos, amounts=[100.0])
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')

    def test_invoice_to_generic_partner_allowed(self):
        self._sync_with()
        invoice = self.init_invoice('out_invoice', partner=self.partner_generic, amounts=[100.0])
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')
