# LEEME — `keywords-google-ads`

> Paquete **meta-ads**. Esto es lo que hay que tener en cuenta **antes** de usar la skill.
> Las instrucciones de trabajo están en `SKILL.md`; esto son las condiciones y los límites.

## Qué hace

Genera un .md de investigación de keywords bien curradas para Google Ads (campañas de Búsqueda) a partir del brief del cliente. SOLO se ejecuta si el cliente quiere publicitar en Google Ads (condicional, no es parte del funnel estándar de Meta).

## Antes de empezar necesitás

- Confirmación de que **el cliente quiere Google Ads**.

## Ojo con esto

- **Es condicional: NO forma parte del funnel estándar de Meta.** Solo se ejecuta si Dirección lo pide.

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
