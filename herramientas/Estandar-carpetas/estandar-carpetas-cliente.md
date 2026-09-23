# Estándar de carpetas de cliente (Drive) — Flowboost

Estructura única para TODOS los clientes. Se comprueba **antes de enviarle al cliente la Guía de grabación**:
si no están creadas las carpetas, el cliente abre el Drive, no encuentra dónde subir y se lía.

## Árbol estándar

```
i_<Cliente>/c_<Cliente>/
├── 0. Onboarding
├── 1. Branding
├── 2. Ads
│   ├── Vídeos crudos        ← AQUÍ sube el cliente. Se lo dejamos creado.
│   │   ├── Script 1
│   │   ├── Script 2
│   │   ├── Script 3
│   │   ├── Script 4
│   │   ├── Script 5
│   │   └── VSL
│   ├── Estáticos
│   │   └── GPT
│   │       └── Tanda 1, Tanda 2…   ← estáticos generados por estaticos-meta (1:1 + 9:16 + specs)
│   └── EGC
│       └── Editados
│           └── Anuncio 1, Anuncio 2… ← vídeo editado + copy.md (copy-anuncios-meta)
├── 3. Landing
├── 4. Formulario
├── 5. Cierre
├── 6. Reportes                     ← «Reporte diario — <Cliente>» (hoja que n8n actualiza a las 8:00)
├── 7. Leads
└── 8. RRSS
```

## Reglas

0. **La carpeta del cliente la crea OPERACIONES** (i_<Cliente>/c_<Cliente>/ con las numeradas). **El agente, al activarse (`/funnel` o cualquier skill), la REVISA** con `auditar-carpetas-cliente.py`: si no existe → para y avisa; si faltan subcarpetas del estándar → las crea con `--crear`.
1. **`Vídeos crudos` la dejamos hecha nosotros (el agente con `--crear`), con una carpeta por guion.** El cliente no crea nada:
   solo suelta los vídeos dentro de la carpeta del guion que le toca. (Si son más o menos de 5 guiones,
   se ajusta el número de carpetas antes de enviar la guía.)
2. **Los crudos del cliente NUNCA se mezclan** con `Estáticos` ni `EGC`, que son piezas ya montadas por nosotros.
3. **Nombres de carpeta**: en español de España y con tilde donde corresponda (`Estáticos`, `Vídeos crudos`).
4. **Nombres de archivo del cliente**: sin tildes, sin eñes y sin espacios (`01_Gancho.mp4`), para que el
   orden alfabético coincida con el orden del guion. Esto va en la guía de grabación.
5. **`6. Reportes` es donde vive la hoja de cálculo del cliente**, la que el flujo `datos-diarios-meta`
   de n8n reescribe cada mañana a las 8:00 de España. Se crea una sola vez con `crear_hoja_cliente.py`.
   *(Dirección la pidió como "5. Reportes"; el 5 ya es `5. Cierre`, así que va en el 6, que es el que el
   estándar y el funnel ya usan para reportes.)*
6. **DECISIÓN DE DIRECCIÓN: este estándar es SOLO para CLIENTES NUEVOS.** Los clientes actuales **no se tocan** con el agente por ahora: ni renombrar, ni reorganizar, ni mover nada. El auditor los reconoce igual (compara por nombre ignorando número y tildes), así que se puede seguir trabajando con ellos tal como están.

## Variantes en clientes antiguos (NO se tocan — solo para que el agente las reconozca)

| Concepto | Estándar | Variantes encontradas |
|---|---|---|
| Cierre | `5. Cierre` | `5. Closer`, `5. Closing` |
| Reportes | `6. Reportes` | `6. Reporting` |
| Estáticos | `Estáticos` | `Estaticos` |
| EGC | `EGC` | `EGC-UGC`, `Vídeos EGC - UGC` |

## Cómo comprobarlo

```bash
python3 auditar-carpetas-cliente.py --todos          # audita todos los clientes (solo lectura)
python3 auditar-carpetas-cliente.py Cliente 04            # audita uno
python3 auditar-carpetas-cliente.py Cliente 04 --crear    # crea lo que falte (nunca renombra ni borra)
```
