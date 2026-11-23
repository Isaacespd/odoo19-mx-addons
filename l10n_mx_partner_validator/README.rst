=========================================
Validador EFOS (Artículo 69-B, SAT)
=========================================

Sincroniza el listado oficial del artículo 69-B del CFF (empresas que facturan
operaciones simuladas, EFOS) y lo aplica a los contactos con RFC.

Funcionalidad
=============

* **Sincronización semanal** (cron) del CSV oficial del SAT. El archivo viene en
  latin-1 y con renglones de título; el parser localiza el encabezado por nombre.
* **Situación 69-B** por contacto: Presunto, Desvirtuado, Definitivo o Sentencia
  Favorable. Solo **Definitivo** marca al contacto como EFOS.
* Un RFC puede aparecer en varios procedimientos: si alguno está como Definitivo,
  prevalece.
* Los RFC genéricos (``XAXX010101000``, ``XEXX010101000``) nunca se marcan.
* RFC normalizado (mayúsculas, sin espacios ni guiones, sin prefijo ``MX``).
* Si la descarga falla o el listado viene vacío, **no se modifica ningún contacto**
  y el error queda en la bitácora de validaciones.

Bloqueos en facturación
=======================

* **Proveedores EFOS**: no se pueden confirmar sus facturas (sus comprobantes no son
  deducibles). Activo por defecto; se puede permitir en *Contabilidad > Ajustes*.
* **Clientes EFOS**: bloqueo opcional.
* Se evalúa la empresa comercial del contacto, y la factura muestra un aviso cuando
  el contacto es EFOS.
