=====================================
Control de Margen en Ventas
=====================================

Evita confirmar cotizaciones por debajo del margen mínimo de la empresa.

Funcionalidad
=============

* Margen mínimo (%) configurable por empresa en *Ventas > Ajustes*. En 0 el control
  está desactivado.
* Al confirmar, las cotizaciones con margen menor al mínimo pasan al estado
  **Esperando Aprobación** y se registra el margen en el chatter. En una confirmación
  por lote, las demás se confirman normalmente.
* Solo el grupo **Aprobador de Márgenes de Venta** puede aprobar (confirma la venta) o
  rechazar (regresa a borrador para ajustar precios).
* Aviso visible en la cotización mientras espera aprobación.

El margen se calcula con el campo ``margin`` de ``sale_margin`` sobre el subtotal sin
impuestos.
