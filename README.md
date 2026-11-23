# Odoo 19 · Addons para México

[![CI](https://github.com/Isaacespd/odoo19-mx-addons/actions/workflows/ci.yml/badge.svg)](https://github.com/Isaacespd/odoo19-mx-addons/actions/workflows/ci.yml)
![Odoo](https://img.shields.io/badge/Odoo-19.0-714B67)
![License](https://img.shields.io/badge/license-LGPL--3-blue)

Módulos para Odoo 19 que resuelven problemas de operación y cumplimiento fiscal en empresas
mexicanas. Cada uno se diseñó a partir de una especificación (spec → plan → tareas) antes de
escribir código y tiene pruebas automatizadas que corren en cada push.

| Módulo | Qué resuelve | Tests |
|---|---|---|
| [`l10n_mx_partner_validator`](l10n_mx_partner_validator) | Sincroniza el listado 69-B del SAT (EFOS) y bloquea facturas de proveedores con operaciones simuladas, cuyos comprobantes no son deducibles. | 17 |
| [`base_approval_engine`](base_approval_engine) | Mixin que agrega aprobaciones multinivel a cualquier modelo: reglas por dominio, pasos por usuario o grupo, permisos y bitácora. | 12 |
| [`sale_margin_approval`](sale_margin_approval) | Detiene cotizaciones por debajo del margen mínimo de la empresa hasta que un gerente las apruebe. | 8 |

`test_base_approval_engine` es un módulo solo para pruebas: define un modelo que hereda el
mixin para probar el motor de punta a punta, igual que los módulos `test_*` del core de Odoo.

## Decisiones de diseño

**Validador EFOS**
- Lee el CSV oficial del SAT tal como se publica (latin-1, renglones de título antes del
  encabezado) y localiza las columnas por nombre, no por posición.
- Solo la situación *Definitivo* marca EFOS. Un RFC puede tener varios procedimientos; si
  alguno es Definitivo, prevalece, porque cada renglón es un procedimiento independiente.
- Los RFC genéricos `XAXX010101000` y `XEXX010101000` nunca se marcan.
- Si la descarga falla o el listado viene vacío no se modifica ningún contacto: un error de
  red no debe desmarcar a todos los EFOS.
- El bloqueo por defecto es en **facturas de proveedor**, que es donde está el riesgo fiscal;
  el bloqueo a clientes es opcional.

**Motor de aprobaciones**
- Los usuarios tienen acceso de solo lectura a solicitudes y bitácora. Toda escritura pasa
  por `action_approve` / `action_reject` después de validar que el usuario corresponde al
  paso actual; así nadie puede aprobar editando el registro.
- `_request_approval()` devuelve los registros que deben esperar, para que el modelo concreto
  continúe su flujo normal con el resto (también en operaciones por lote).

**Control de margen**
- Confirmación por lote: solo se detienen las cotizaciones con margen bajo.
- El margen exactamente igual al mínimo se acepta (`float_compare`, sin errores de redondeo).

## Correr los tests

```bash
docker run -d --name pg -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo postgres:16
docker run --rm --link pg:db -v "$PWD:/ws" odoo:19.0 \
  odoo --db_host db --db_user odoo --db_password odoo \
       --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/ws \
       -d test -i base_approval_engine,test_base_approval_engine,sale_margin_approval,l10n_mx_partner_validator \
       --test-tags /base_approval_engine,/test_base_approval_engine,/sale_margin_approval,/l10n_mx_partner_validator \
       --stop-after-init
```

El CI además corre `pylint-odoo` sobre todos los módulos.

## Autor

**Isaac Espinosa** · Desarrollador Python / Odoo · [isaacespd.github.io](https://isaacespd.github.io)

Licencia [LGPL-3](LICENSE).
