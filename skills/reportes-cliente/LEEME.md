# LEEME — `reportes-cliente`

> Paquete **meta-ads**. Esto es lo que hay que tener en cuenta **antes** de usar la skill.
> Las instrucciones de trabajo están en `SKILL.md`; esto son las condiciones y los límites.

## Qué hace

Los REPORTES DE RESULTADOS que ve el cliente, en su hoja de cálculo del Drive: **Meta Ads y Google Ads**, cada uno en su pestaña del MISMO archivo (`Reporte Meta` y `Reporte Google`), por semana y por mes, con coste por lead y ROAS. Se actualizan solas cada mañana —Meta a las 8:00 desde n8n, Google a las 6:00 desde un script de Google Ads—.

## Antes de empezar necesitás

- La skill **`gestion-cuenta-meta`** (paquete *meta-ads*): lee ficheros suyos.
- El **`ad_account_id`** del cliente y el **`sheet_id`** de su hoja, en la pestaña `clientes` de la maestra `Flowboost · Datos Meta`. Sin esos dos campos el flujo diario se salta al cliente.
- El **`META_TOKEN`** en el VPS (usuario del sistema, `ads_read` + «Ver rendimiento»). Sin él no se actualiza nada.

## Lo que NO se puede hacer

- ⛔ **Mandar el reporte por correo.** El envío está RETIRADO (Dirección, 10-09-2026): no se manda a nadie, ni de prueba. El cliente entra a su hoja.
- ⛔ **Enseñar cifras sin comprobar antes que la cuenta es la de ESE cliente.** Las cuentas no se identifican por las iniciales: se mira que las campañas encajen con su negocio.
- ⛔ **Regenerar una hoja que ya está en uso.** Borra los cierres, el ticket, el margen y las pestañas de Google. `montar_hoja_reportes.py` se planta; no forzarlo con `--rehacer` sin rescatar antes lo escrito.
- ⛔ **Escribir en Meta.** Solo lectura de insights: a Dirección le restringieron una cuenta por enlazar herramientas.

## Ojo con esto

- **Una semana a medias YA enseña sus datos.** No hay que esperar a que se cierren los 7 días: la fila en curso se rellena cada mañana. Pero una fila incompleta no sirve para decidir.
- **A mano van tres cosas una vez** —ticket medio, margen y **fee de agencia al mes** (viene con 1.100 € puesto)— **y el NÚMERO de cierres cada semana**, en la columna «Cierres (a mano)». Lo demás se calcula. Todo lo manual lleva «(a mano)» en el rótulo.
- **El ROAS se mide contra el COSTE TOTAL** (inversión + la parte del fee que toca a esa semana), no contra la inversión sola: el cliente paga las dos cosas. Ojo: el fee entero se carga a los DOS reportes, así que sumar las dos columnas «Coste total» lo cuenta dos veces.
- **El coste por lead que ve el cliente es BRUTO.** El real es del orden de 2,5×. Internamente nunca se decide con el bruto.
- **Ya no hay correo que empuje a mirar los números.** La hoja se actualiza en silencio: si nadie la abre, nadie se entera. Quien la mira es `gestion-cuenta-meta` en la revisión semanal.
- Un ratio del mes se calcula **sobre las sumas del mes**, nunca promediando los ratios de las semanas: las semanas que no han pasado valen cero y hunden la media.

## Scripts que trae

- `scripts/generar_reporte.py`

## Accesos que toca

Google Drive del cliente (solo lectura salvo entregables), cuenta de Meta Ads — **solo lectura** (insights) · Google Ads (script dentro de la cuenta, solo escribe en la hoja), VPS por SSH, n8n.

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
