# LEEME — `keywords-google-ads`

> Paquete **google-ads**. Esto es lo que hay que tener en cuenta **antes** de usar la skill.
> Las instrucciones de trabajo están en `SKILL.md`; esto son las condiciones y los límites.

## Qué hace

Las keywords de Google Ads de un cliente, con criterio: qué pujar, qué negativizar y hacia dónde se
mueve la demanda. Con cuenta activa cruza los términos reales de la cuenta, cinco años de Google
Trends y lo que el servicio ofrece de verdad. Sin cuenta, arma el plan desde el brief. Entrega un
solo documento en `6. Reportes` del Drive del cliente.

## Antes de empezar necesitas

- **La landing que recibe el tráfico de Google** y una lista de **lo que el cliente NO ofrece**
  (un centro físico, un ingreso, otras ciudades…). Sin eso la skill recomienda lo que no se vende.
- **Con cuenta**: la URL del archivo «Estacionalidad - \<Cliente\>», que escribe el Ads Script.
  Si la cuenta no lo tiene, `INSTALACION.md` (15 minutos).
- **Al menos 24 meses completos** para hablar de estacionalidad. Con menos, la skill entrega una
  hipótesis y lo dice.
- rclone configurado con el remoto `gdrive:` y el archivo compartido con ese Google.

## Ojo con esto

- **La landing actual manda sobre el brief.** El brief puede describir líneas que ya no van en
  Google. Si no coinciden, se le pregunta a Dirección antes de seguir.
- **Lo que el servicio no ofrece va fuera aunque crezca.** Un servicio online no puja «centro de…».
- **La marca va siempre aparte**, y el nombre del fundador también es marca.
- **Antes de fiarse de un CPA, las alertas de medición.** Más conversiones que clics = cuenta de
  más, y el CPA sale falso.
- **La tendencia de Trends se mide término a término**, nunca desde un lote con ancla. Las cifras
  de un lote son ruido para los términos pequeños.
- **Ninguna acción se aplica desde aquí.** Se propone; ejecutar es de Dirección.

## Accesos que toca

El archivo «Estacionalidad - \<Cliente\>» del Drive (solo lectura, por rclone), Google Trends
(consulta pública), la landing del cliente. Escribe el entregable en `6. Reportes` del Drive del
cliente y el contexto en `~/Desktop/CLIENTES/<Cliente>/google-ads/`.

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
- **Para avisar a Dirección se usa `avisar.py`** (`~/Desktop/FLOWBOOST-BACKUP-MAC/Documentos-Flowboost/Estandar-carpetas/avisar.py --nivel urgente|aviso|info`), no un mensaje suelto que nadie lee.

---

*Escrito el 23-09-2026 y auditado por consejo el mismo día. Cuando se regenere el sistema de LEEME
con `gen_leeme.py`, hay que incluirlo.*
