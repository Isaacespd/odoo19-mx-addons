=========================
Motor de Aprobaciones
=========================

Mixin abstracto (``approval.mixin``) que agrega aprobaciones multinivel a cualquier
modelo de Odoo, configuradas por el usuario sin programar.

Funcionalidad
=============

* **Reglas por modelo y dominio**: p. ej. "Gastos con monto mayor a 10,000".
* **Pasos secuenciales**: cada paso lo aprueba un usuario específico o cualquier
  miembro de un grupo. El *Administrador de Aprobaciones* puede intervenir en cualquier paso.
* **Permisos reales**: solo quien corresponde al paso actual puede aprobar o rechazar.
  Los usuarios tienen acceso de solo lectura a solicitudes y bitácora; las escrituras
  pasan por ``action_approve`` / ``action_reject`` después de validar.
* **Bitácora** de quién aprobó o rechazó cada paso, con comentario, más chatter y
  secuencia ``APR/AAAA/00001``.

Uso desde otro módulo
=====================

.. code-block:: python

    class HrExpense(models.Model):
        _name = 'hr.expense'
        _inherit = ['hr.expense', 'approval.mixin']

        def action_submit(self):
            to_approve = self._request_approval()
            return super(HrExpense, self - to_approve).action_submit()

        def action_approval_granted(self):
            res = super().action_approval_granted()
            self.action_submit()
            return res

``_request_approval()`` crea las solicitudes que apliquen y devuelve los registros que
deben esperar; el resto sigue su flujo normal.

Tests
=====

Los tests viven en ``test_base_approval_engine``, que define un modelo de prueba que
hereda el mixin (mismo patrón que los módulos ``test_*`` del core de Odoo).
