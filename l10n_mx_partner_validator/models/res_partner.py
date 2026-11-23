import csv
import io
import logging
import re

import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

DEFAULT_EFOS_URL = 'http://omawww.sat.gob.mx/cifras_sat/Documents/Listado_Completo_69-B.csv'

# RFC genéricos del SAT (público en general / extranjeros). Nunca son EFOS.
GENERIC_RFCS = frozenset({'XAXX010101000', 'XEXX010101000'})

# Persona moral (12) o física (13): 3-4 letras, fecha AAMMDD, homoclave de 3.
RFC_PATTERN = re.compile(r'^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$')

# Texto de la columna "Situación del contribuyente" del listado 69-B.
SAT_SITUATIONS = {
    'presunto': 'presunto',
    'desvirtuado': 'desvirtuado',
    'definitivo': 'definitivo',
    'sentencia favorable': 'sentencia_favorable',
}

# Un RFC puede aparecer en varios procedimientos. Si alguno está como Definitivo,
# prevalece (criterio conservador); el orden del archivo no indica cronología.
SITUATION_PRIORITY = {
    'definitivo': 4,
    'sentencia_favorable': 3,
    'presunto': 2,
    'desvirtuado': 1,
}


def normalize_rfc(vat):
    """Normaliza un RFC: mayúsculas, sin espacios ni guiones, sin prefijo de país MX."""
    if not vat:
        return ''
    rfc = re.sub(r'[\s\-\.]', '', vat).upper()
    if rfc.startswith('MX') and len(rfc) in (14, 15):
        rfc = rfc[2:]
    return rfc


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_efos = fields.Boolean(
        string='Es EFOS (69-B)', default=False, tracking=True, copy=False,
        help='Indica si la empresa está listada como Definitivo en el listado 69-B del SAT.')
    l10n_mx_efos_situation = fields.Selection([
        ('presunto', 'Presunto'),
        ('desvirtuado', 'Desvirtuado'),
        ('definitivo', 'Definitivo'),
        ('sentencia_favorable', 'Sentencia Favorable'),
    ], string='Situación 69-B', copy=False, tracking=True, readonly=True,
        help='Situación del RFC en el último listado 69-B sincronizado. Vacío si no aparece.')
    last_validation_date = fields.Datetime(string='Última Validación RFC', copy=False, readonly=True)

    # ------------------------------------------------------------------
    # Descarga y parseo del listado del SAT
    # ------------------------------------------------------------------
    @api.model
    def _parse_efos_csv(self, content):
        """Convierte el CSV 69-B del SAT en {rfc: situación}.

        El archivo viene en latin-1 y trae renglones de título antes del
        encabezado, así que se localiza el renglón que contiene "RFC" y
        "Situación" en lugar de asumir una posición fija.
        """
        if isinstance(content, bytes):
            try:
                text = content.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = content.decode('latin-1')
        else:
            text = content

        reader = csv.reader(io.StringIO(text))
        rfc_idx = situation_idx = None
        result = {}
        for row in reader:
            if rfc_idx is None:
                cells = [c.strip().lower() for c in row]
                if 'rfc' in cells:
                    situation_idx = next(
                        (i for i, c in enumerate(cells) if c.startswith('situaci')), None)
                    if situation_idx is not None:
                        rfc_idx = cells.index('rfc')
                continue
            if len(row) <= max(rfc_idx, situation_idx):
                continue
            rfc = normalize_rfc(row[rfc_idx])
            situation = SAT_SITUATIONS.get(row[situation_idx].strip().lower())
            if not situation or rfc in GENERIC_RFCS or not RFC_PATTERN.match(rfc):
                continue
            current = result.get(rfc)
            if not current or SITUATION_PRIORITY[situation] > SITUATION_PRIORITY[current]:
                result[rfc] = situation
        if rfc_idx is None:
            raise ValueError(self.env._('El archivo no tiene el encabezado esperado (columnas RFC y Situación).'))
        return result

    @api.model
    def _download_efos_list(self):
        url = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_mx_partner_validator.efos_list_url') or DEFAULT_EFOS_URL
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        return self._parse_efos_csv(response.content)

    # ------------------------------------------------------------------
    # Aplicación del listado a contactos
    # ------------------------------------------------------------------
    def _apply_efos_list(self, situations):
        """Actualiza situación e is_efos de los contactos en `self` según `situations`.

        Devuelve el número de contactos cuyo estado EFOS cambió.
        """
        now = fields.Datetime.now()
        changed = 0
        for partner in self:
            rfc = normalize_rfc(partner.vat)
            situation = False if rfc in GENERIC_RFCS else situations.get(rfc, False)
            is_efos = situation == 'definitivo'
            vals = {'last_validation_date': now}
            if partner.l10n_mx_efos_situation != situation:
                vals['l10n_mx_efos_situation'] = situation
            if partner.is_efos != is_efos:
                vals['is_efos'] = is_efos
                changed += 1
            partner.write(vals)
            if 'is_efos' in vals:
                body = (self.env._('RFC %s aparece como Definitivo en el listado 69-B del SAT.', rfc) if is_efos
                        else self.env._('RFC %s ya no está como Definitivo en el listado 69-B del SAT.', rfc))
                partner.message_post(body=body)
        return changed

    @api.model
    def _efos_partners_domain(self):
        return [('vat', '!=', False), ('vat', 'not in', list(GENERIC_RFCS))]

    def _sync_efos(self, log_name):
        """Descarga el listado y lo aplica a `self` (o a todos los contactos con RFC si está vacío)."""
        Log = self.env['partner.rfc.validation.log'].sudo()
        partners = self or self.search(self._efos_partners_domain())
        try:
            situations = self._download_efos_list()
        except (requests.RequestException, ValueError) as exc:
            _logger.warning('No se pudo sincronizar el listado 69-B: %s', exc)
            Log.create({
                'name': log_name,
                'partners_affected': 0,
                'log_details': self.env._('No se pudo descargar o leer el listado 69-B: %s', exc),
                'status': 'error',
            })
            return False
        if not situations:
            # Un listado vacío casi siempre es un error de descarga: no desmarcamos a nadie.
            Log.create({
                'name': log_name,
                'partners_affected': 0,
                'log_details': self.env._('El listado 69-B descargado está vacío; no se modificó ningún contacto.'),
                'status': 'error',
            })
            return False
        changed = partners._apply_efos_list(situations)
        efos_count = sum(1 for s in situations.values() if s == 'definitivo')
        Log.create({
            'name': log_name,
            'partners_affected': changed,
            'log_details': self.env._(
                'Listado con %(total)s RFC (%(efos)s definitivos). Se revisaron %(checked)s contactos; '
                '%(changed)s cambiaron de estado EFOS.',
                total=len(situations), efos=efos_count, checked=len(partners), changed=changed),
            'status': 'success',
        })
        return True

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def action_validate_rfc(self):
        """Valida el formato del RFC de los contactos seleccionados y su situación 69-B."""
        invalid = self.filtered(lambda p: p.vat and not RFC_PATTERN.match(normalize_rfc(p.vat)))
        for partner in invalid:
            partner.message_post(body=self.env._('El RFC %s no tiene un formato válido.', partner.vat))
        to_check = (self - invalid).filtered(
            lambda p: p.vat and normalize_rfc(p.vat) not in GENERIC_RFCS)
        if to_check:
            to_check._sync_efos(self.env._('Validación Manual'))
        return True

    @api.model
    def _cron_check_efos_status(self):
        """Cron semanal: descarga el listado 69-B y actualiza todos los contactos con RFC."""
        return self.browse()._sync_efos(self.env._('Validación por CRON SAT'))
