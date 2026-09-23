# flowboost-skills-google-ads

Google Ads: conexión, keywords y estacionalidad

---

## Instalar (2 minutos)

Abre **Claude Code** y pégale esto tal cual:

```
Instálame las skills de Flowboost de este repo y guíame en la primera configuración:
https://github.com/<usuario-github>/flowboost-skills-google-ads
```

Claude clona el repo, instala las skills y te va pidiendo lo que falte en tu ordenador.
No hace falta que sepas nada de terminal: te da los comandos ya escritos.

> ### ⚠️ Instala también el paquete base
> Estas skills leen de `fundamentos` (Ogilvy, Schwartz, el compliance de Meta).
> **Sin él funcionan a medias y no avisan.** Pégale también esto a Claude:
> ```
> Instala también https://github.com/<usuario-github>/flowboost-skills-fundamentos
> ```


### Si lo prefieres a mano

```bash
git clone https://github.com/<usuario-github>/flowboost-skills-google-ads.git
cd flowboost-skills-google-ads
python3 instalar.py
```

Y después, en Claude: `guíame en la primera configuración`

---

## Qué hay aquí

| Skill | Qué hace |
|---|---|
| `google-ads-mcp` | Audita cuentas de Google Ads leyendo datos reales por MCP y cruzándolos con GA4 y Search Console. Saca las cuatro métricas que la interfaz no da - CPA… |
| `keywords-google-ads` | Las keywords de Google Ads de un cliente, con criterio - qué pujar, qué negativizar y hacia dónde se mueve la demanda. Con cuenta activa, cruza tres f… |

Cada skill lleva un **`LEEME.md`** con lo que hay que tener en cuenta antes de usarla: qué
necesita, qué no puede hacer y dónde deja las cosas.

---

## Lo que vas a necesitar

| | Para qué |
|---|---|
| **rclone + el Drive de Flowboost** | de ahí salen el brief, el branding y las fotos; ahí se dejan los entregables |
| **Python 3** | ya viene en el Mac |


La primera configuración te la monta Claude paso a paso. Lo único que tiene que darte Dirección son
los accesos: el Google del Drive y, si llevas campañas, la cuenta de Meta.

**Nunca le des una contraseña o una clave por chat.** Si algo la necesita, la pones tú en tu
ordenador y Claude te dice dónde.

---

## Reglas de la casa que aplican aquí

- Todo el texto para clientes en **español de España** (tú/vosotros), nunca voseo.
- **No se inventa** nada: cifras, testimonios, fechas ni garantías. Lo que falte se marca `[FALTA]`.
- Los ficheros de un cliente van a `~/Desktop/CLIENTES/<cliente>/`.
- El **Drive del cliente es de solo lectura**, salvo los entregables en su subcarpeta.
- **Activar una campaña de Meta es siempre de Dirección.** Las skills las dejan en pausa.

---

*Generado desde el sistema de Flowboost. No se edita aquí: se edita en el origen y se regenera.*
