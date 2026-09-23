# LEEME — `estacionalidad-google-ads`

> Paquete **google-ads**. Esto es lo que hay que tener en cuenta **antes** de usar la skill.
> Las instrucciones de trabajo están en `SKILL.md`; esto son las condiciones y los límites.

## Qué hace

Dice en qué meses del año la gente busca de verdad lo que vende el cliente, y lo convierte en un
calendario de presupuesto de 12 meses. Sale de los términos de búsqueda reales de la cuenta, no de
suposiciones.

## Antes de empezar necesitás

- La hoja del cliente con las pestañas **`datos-google-terminos`** y **`datos-google-is`**. Las escribe
  sola el Ads Script cada mañana; si no están, la cuenta todavía tiene el script viejo.
- **Al menos 2 años de histórico** para hablar de estacionalidad. Con 12 meses o menos, lo que sale es
  una hipótesis y así hay que decirlo.
- Saber qué vende el cliente, para agrupar los términos en familias con sentido.

## Ojo con esto

- **Las impresiones de un mes dependen del presupuesto que se puso ese mes.** Un mes sin dinero parece
  un mes sin demanda. Siempre se leen junto a la cuota de impresiones perdida.
- **Estacionalidad no es tendencia.** Una cuenta que crece todo el año tiene los últimos meses altos
  por crecimiento, no por temporada.
- **Google Trends no da volúmenes**, da un índice relativo de 0 a 100 dentro de esa consulta concreta.
  Dos consultas distintas no se comparan entre sí sin un término ancla.
- **No se toca `datos-google`**: esa pestaña alimenta el reporte del cliente y tiene fórmulas
  enganchadas a tres listas del Python. La estacionalidad vive en sus dos pestañas propias.
- **Los cambios de presupuesto se proponen, no se aplican.** Y cuando se aplican, 2-3 semanas antes del
  mes bueno, porque Smart Bidding necesita aprender.

## Accesos que toca

La hoja de reportes del cliente en Drive (solo lectura), Google Ads (solo lectura, y solo para mirar).
El entregable va a `~/Desktop/CLIENTES/<Cliente>/`.

## Reglas de la casa (valen para todas las skills)

- **Todo el texto para clientes en español de España** (tú/vosotros). Nunca voseo ni LATAM.
- **No se inventa nada**: cifras, testimonios, fechas, garantías o casos. Lo que falte se marca
  `[FALTA]` y se pide.
- **Las fechas salen del reloj del sistema** (`date +%d/%m/%Y`), nunca de memoria.
- **Los ficheros de un cliente van a `~/Desktop/CLIENTES/<cliente>/`**, nunca sueltos en Descargas.
- **El Drive del cliente es de SOLO LECTURA**, salvo los entregables en su subcarpeta correcta. No se
  mueve, borra ni renombra nada.
- **Nunca se sube un `.md` crudo al Drive del cliente**: se convierte a Google Doc.
- **Nunca se teclean contraseñas, claves de API ni tokens**, aunque te los den. Los pone Dirección.
- **Para avisar a Dirección se usa `avisar.py`** (`--nivel urgente|aviso|info`), no un mensaje suelto que
  nadie lee.
