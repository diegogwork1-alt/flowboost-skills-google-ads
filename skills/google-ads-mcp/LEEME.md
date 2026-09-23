# LEEME — `google-ads-mcp`

> Paquete **?**. Esto es lo que hay que tener en cuenta **antes** de usar la skill.
> Las instrucciones de trabajo están en `SKILL.md`; esto son las condiciones y los límites.

## Qué hace

Audita cuentas de Google Ads leyendo datos reales por MCP y cruzándolos con GA4 y Search Console. Saca las cuatro métricas que la interfaz no da - CPA marginal por tramo de presupuesto, cuota de impresiones perdida traducida a dinero y separada por presupuesto vs ranking, curva de maduración de conversiones y coste real del clic incremental - y cierra con un veredicto de una línea (escalar, arreglar antes de escalar, mantener o apagar) más acciones ordenadas por dinero al mes.

**Qué NO hace:** NO usar para Meta (eso es gestion-cuenta-meta) ni para planificar keywords desde el brief (eso es keywords-google-ads).

## Antes de empezar necesitás

- Nada externo: es autónoma.

## Accesos que toca

Google Drive del cliente (solo lectura salvo entregables).

## Reglas de la casa (valen para todas las skills)

- **Todo el texto para clientes en español de España** (tú/vosotros). Nunca voseo ni LATAM.
- **No se inventa nada**: cifras, testimonios, fechas, garantías o casos. Lo que falte se marca `[FALTA]` y se pide.
- **Las fechas salen del reloj del sistema** (`date +%d/%m/%Y`), nunca de memoria.
- **Los ficheros de un cliente van a `~/Desktop/CLIENTES/<cliente>/`**, nunca sueltos en Descargas.
- **El Drive del cliente es de SOLO LECTURA**, salvo los entregables en su subcarpeta correcta. No se mueve, borra ni renombra nada.
- **Nunca se sube un `.md` crudo al Drive del cliente**: se convierte a Google Doc.
- **Nunca se teclean contraseñas, claves de API ni tokens**, aunque te los den. Los pone Dirección.
- **Para avisar a Dirección se usa `avisar.py`** (`--nivel urgente|aviso|info`), no un mensaje suelto que nadie lee.

---

*Generado el 10-09-2026 desde el sistema de Flowboost. Se regenera con `gen_leeme.py`; no editar a mano.*
