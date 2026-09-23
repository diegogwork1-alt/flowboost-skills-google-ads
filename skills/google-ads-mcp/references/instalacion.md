# Instalación — de cero a los tres MCP conectados

Verificado contra los repos y la documentación de Google el **21-09-2026**. Se lee una vez.

| Servicio | Servidor | Origen | Arranque |
|---|---|---|---|
| Google Ads | **Oficial de Google** | `googleads/google-ads-mcp` — **no está en PyPI**: se instala desde el repo | `pipx run --spec git+…` |
| GA4 | **Oficial de Google** | `googleanalytics/google-analytics-mcp` (PyPI `analytics-mcp`) | `pipx run analytics-mcp` |
| Search Console | **Comunidad** | `ahonn/mcp-server-gsc` (npm `mcp-server-gsc`) | `npx -y` |

`mcp-server-gsc` (0.3.0) expone ocho herramientas: `list_sites`, `search_analytics`,
`enhanced_search_analytics`, `detect_quick_wins`, `index_inspect`, `list_sitemaps`, `get_sitemap`,
`submit_sitemap`. **Su README documenta parámetros que el código no acepta** (`detectQuickWins`,
`quickWinsConfig`): los buenos son `enableQuickWins` / `quickWinsThresholds`, o la herramienta
`detect_quick_wins`. Manda el código.

---

## 0 · Estado del Mac de Dirección (comprobado 21-09-2026)

```
python3 --version   → 3.9.6   ❌ hace falta 3.10+ (el 3.9 es el del sistema, no se toca)
pipx                → no está ❌
gcloud              → no está ❌
node                → v24.18.0 ✅
claude              → ~/.local/bin/claude ✅
brew                → no está
```

### Opción A — con Homebrew (recomendada)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
Seguir las dos líneas que imprime el instalador para añadir brew al PATH, y luego:
```bash
brew install python@3.12 pipx
brew install --cask google-cloud-sdk
pipx ensurepath
```
Cerrar y reabrir la terminal.

### Opción B — sin Homebrew
- Python: instalador oficial de python.org (3.12).
- pipx: `python3.12 -m pip install --user pipx && python3.12 -m pipx ensurepath`
- gcloud: `curl https://sdk.cloud.google.com | bash` y reiniciar la terminal.

Verificación (y **apuntar la ruta de pipx**, que hará falta en el paso 5):
```bash
python3.12 --version && which pipx && pipx --version && gcloud --version | head -1
```

---

## 1 · Proyecto de Google Cloud con las tres APIs

1. En `console.cloud.google.com` → **Crear proyecto** (ej. `mcp-flowboost`).
   Si la cuenta tiene organización de Google Workspace, **créalo dentro de la organización**: es lo
   único que habilita el tipo «Interno» del paso 2.
2. Loguear gcloud y averiguar el **PROJECT_ID**, que **no es el nombre** que escribiste: Google le
   añade un sufijo (`mcp-flowboost` → `mcp-flowboost-483921`).
```bash
gcloud auth login                       # abre el navegador, ~1 min
gcloud projects list                    # el PROJECT_ID es la primera columna
gcloud config set project TU_PROJECT_ID
gcloud services enable googleads.googleapis.com searchconsole.googleapis.com \
  analyticsadmin.googleapis.com analyticsdata.googleapis.com
```
Un solo proyecto para los tres servicios. Repetirlo tres veces es el error más común de los tutoriales.

---

## 2 · Pantalla de consentimiento y cliente OAuth de escritorio

*APIs y servicios → Pantalla de consentimiento de OAuth*:
- **Interno** solo aparece si el proyecto está en una organización de Google Cloud (Workspace o Cloud
  Identity). Con un Gmail suelto **esa opción no existe**.
- Sin organización: **Externo** y añadirte a ti mismo en *Usuarios de prueba*. Así funciona sin pasar
  la verificación de Google, **pero** en estado *Prueba* Google emite un refresh token que
  **caduca a los 7 días** con scopes como `adwords`: los MCP dejarán de responder cada semana.
  Dos salidas: repetir el login del paso 4 cada semana, o publicar la app (*En producción*), que con
  scopes sensibles exige verificación. Elegir a sabiendas, no por descuido.

*Credenciales → Crear credenciales → ID de cliente de OAuth* → tipo **Aplicación de escritorio** →
**descargar el JSON**:
```bash
mkdir -p ~/.config/google-mcp
mv ~/Downloads/client_secret_*.json ~/.config/google-mcp/oauth_client.json
chmod 600 ~/.config/google-mcp/oauth_client.json
```
(El vídeo lo deja en el Escritorio. Mala idea: se borra sin querer y sale en cualquier captura.)

### 2b · Cuenta de servicio para Search Console
Se crea ahora, en la misma pantalla de *Credenciales*, porque el MCP de GSC **no usa el login del
paso 4**:
1. *Crear credenciales → Cuenta de servicio* → crear **clave JSON**.
2. ```bash
   mv ~/Downloads/<clave>.json ~/.config/google-mcp/gsc_service_account.json
   chmod 600 ~/.config/google-mcp/gsc_service_account.json
   ```
3. En Search Console, *Configuración → Usuarios y permisos*, añadir el email
   `<cuenta-de-servicio>@<proyecto>.iam.gserviceaccount.com` como usuario de la propiedad. Sin este paso, `PERMISSION_DENIED`.

---

## 3 · Nivel de acceso de la API — ya NO hay developer token

**Google retiró los developer tokens el 09-09-2026.** Si mandas uno en la cabecera, los servidores lo
ignoran. El nivel de acceso lo determina ahora el **proyecto de Google Cloud** que emite las
credenciales OAuth, y se gestiona en la página **Google Ads API Overview** de la Cloud Console
(el *Centro de API* del MCC ya no procesa solicitudes).

| Nivel | Qué alcanza | Cómo se consigue |
|---|---|---|
| **Test** | solo cuentas de prueba | automático al habilitar la API |
| **Explorer** | **cuentas de producción**, 2.880 operaciones/día | se solicita en esa página; Google suele concederlo al enviar la solicitud |
| **Basic** | 15.000 operaciones/día | verificación de marca; revisión automática en minutos |
| **Standard** | sin límite | auditoría manual, ~10 días hábiles |

**Para auditar la cuenta de un cliente basta Explorer.** No hay ningún reloj de 2-3 días: nada bloquea
el montaje. Si el proyecto se queda en Test y consultas producción, el error es
`CLOUD_PROJECT_NOT_APPROVED_FOR_PRODUCTION`.

---

## 4 · Un solo login para Google Ads y GA4 (ADC)

```bash
gcloud auth application-default login \
  --client-id-file="$HOME/.config/google-mcp/oauth_client.json" \
  --scopes="https://www.googleapis.com/auth/adwords,https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/webmasters.readonly,https://www.googleapis.com/auth/cloud-platform"
```
Abre el navegador: entrar con la cuenta que tiene acceso al MCC y a GA4. Deja las credenciales en
`~/.config/gcloud/application_default_credentials.json`, que es lo que se pasa como
`GOOGLE_APPLICATION_CREDENTIALS`. (Search Console **no** usa esto: usa la cuenta de servicio de §2b.)

---

## 5 · Añadir los MCP a Claude Code

`pipx` se escribe con su ruta absoluta porque **Claude no hereda el PATH del shell**; sustituir por lo
que devolvió `which pipx` en el paso 0.

```bash
PIPX=$(which pipx)
ADC="$HOME/.config/gcloud/application_default_credentials.json"

# GA4 (oficial)
claude mcp add analytics-mcp --scope user \
  -e "GOOGLE_APPLICATION_CREDENTIALS=$ADC" \
  -e "GOOGLE_PROJECT_ID=TU_PROJECT_ID" \
  -- "$PIPX" run analytics-mcp

# Google Ads (oficial) — LOGIN_CUSTOMER_ID es el MCC; obligatorio si la cuenta cuelga de un MCC
claude mcp add ads --scope user \
  -e "GOOGLE_APPLICATION_CREDENTIALS=$ADC" \
  -e "GOOGLE_PROJECT_ID=TU_PROJECT_ID" \
  -e "GOOGLE_ADS_LOGIN_CUSTOMER_ID=ID_DEL_MCC" \
  -- "$PIPX" run --spec "git+https://github.com/googleads/google-ads-mcp.git@<TAG_O_COMMIT>" google-ads-mcp

# Search Console (comunidad) — su credencial es la cuenta de servicio, NO el ADC
claude mcp add gsc --scope user \
  -e "GOOGLE_APPLICATION_CREDENTIALS=$HOME/.config/google-mcp/gsc_service_account.json" \
  -- npx -y mcp-server-gsc
```

- El servidor de Ads se llama **`ads`**, no `google-ads-mcp`, para no confundirlo con esta skill.
- `GOOGLE_ADS_LOGIN_CUSTOMER_ID` acepta guiones: el servidor los quita. Es el ID de 10 dígitos que sale
  arriba a la derecha en la interfaz del MCC.
- **Fijar un tag o commit** en `--spec` en vez de dejar `@main`: si no, cada arranque ejecuta el HEAD
  del repo con el ADC en el entorno.
- `GOOGLE_ADS_DEVELOPER_TOKEN` ya no hace falta (§3). Si algún día hiciera falta un secreto, lo teclea
  Dirección: los tokens no se escriben desde aquí, y menos en un comando que queda en `~/.zsh_history`.

**Rehacer uno que salió mal** (repetir el `add` falla por nombre duplicado):
```bash
claude mcp remove <nombre> --scope user
```

Para **Claude Desktop** (la app, no la CLI) el equivalente es
`~/Library/Application Support/Claude/claude_desktop_config.json` con los mismos `command`/`args`/`env`.

---

## 6 · Verificar, uno por uno

```bash
claude mcp list          # los tres en ✓ Connected
```
Y dentro de Claude, **antes de pasar al siguiente**:
- Ads → `customers_list_accessible_customers` devuelve `customers/NNNNNNNNNN`.
  El `customer_id` que pide la skill es **solo la parte numérica**, sin `customers/` y sin guiones.
- GA4 → `get_account_summaries` lista propiedades.
- GSC → `list_sites`, y luego `search_analytics` con un rango de 7 días.

## Herramientas que quedan disponibles
- **Ads**: `customers_list_accessible_customers`, `search_search` (la que lanza GAQL),
  `metadata_get_resource_metadata`. El prefijo es el nombre de la categoría y se cambia en
  `tools_config.yaml`. Solo lectura.
- **GA4**: `get_account_summaries`, `get_property_details`, `list_google_ads_links`, `run_report`,
  `run_funnel_report`, `get_custom_dimensions_and_metrics`, `run_realtime_report`. Solo lectura.
- **GSC**: las ocho de arriba. Solo lectura salvo `submit_sitemap`, que **no se usa desde esta skill**.

## Fallos típicos
| Síntoma | Causa |
|---|---|
| `CLOUD_PROJECT_NOT_APPROVED_FOR_PRODUCTION` | el proyecto sigue en nivel **Test**: pedir Explorer (§3) |
| `USER_PERMISSION_DENIED` en Ads | falta `GOOGLE_ADS_LOGIN_CUSTOMER_ID`, o la cuenta del ADC no tiene acceso a ese `customer_id` |
| Los tres MCP dejan de responder cada semana | app OAuth **Externo en estado *Prueba***: refresh token de 7 días (§2) |
| `PERMISSION_DENIED` en GSC | no se dio de alta el email de la cuenta de servicio en la propiedad (§2b) |
| GA4 devuelve vacío | el `GOOGLE_PROJECT_ID` no es el que tiene habilitada la Data API |
| `pipx: command not found` al arrancar el MCP | se puso `pipx` a secas: va la ruta absoluta (§5) |
| `UNRECOGNIZED_FIELD` en una consulta | la API cambió de versión: comprobar el campo con `metadata_get_resource_metadata` |
