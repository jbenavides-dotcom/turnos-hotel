# Sistema de Turnos · Hotel La Palma y El Tucán

Sistema dinámico para la **parrilla de turnos** del personal del hotel, conectado
a las **reservas (Cloudbeds)** y con cálculo de horas/extras. Reemplaza el manejo
manual en Excel (`TURNOS 2026.xlsx` + `formato horas extras.xlsx`).

## Contenido

- **`DISENO-TURNOS.md`** — diseño completo: reglas, modelo de datos, fases,
  hallazgos de Cloudbeds y de los Excel de Lina.
- **`prototipo-parrilla.html`** — prototipo visual (abrir en el navegador). Vista
  calendario, rotación mañana/tarde lun→lun, descansos editables, ocupación por
  día → semáforo de cobertura (regla >6 cabañas → 2 personas).
- **`validar_cloudbeds.py`** — valida la conexión a la API de Cloudbeds.

## Estado

- ✅ Conexión a Cloudbeds por API **validada** (property `203345`, `getReservations` OK).
- ✅ Prototipo de parrilla funcionando.
- ⏳ Reglas finales de rotación (las envía Lina).
- ⏳ Fase 2: Supabase + módulo en la app web (stack `cafe-trazabilidad-v2`).

## Seguridad — leer antes de commitear

**NINGÚN secreto va en este repo.** El token de Cloudbeds vive solo en el vault
local `key-apis/apis.json` (gitignored). `validar_cloudbeds.py` lo lee de la
variable de entorno `CLOUDBEDS_API_TOKEN` o del vault; nunca hardcodeado.

Antes de cada commit, escanear:

```bash
grep -rnE "(api[_-]?key|token|secret|bearer|cbat_|sk-|AIza)" --exclude-dir=.git .
```

## Validar Cloudbeds desde otra terminal

```bash
# opción A: variable de entorno
export CLOUDBEDS_API_TOKEN=cbat_xxxxx
python validar_cloudbeds.py

# opción B: tener el vault apis.json en su ruta canónica (lo lee solo)
python validar_cloudbeds.py
```

## Plantilla real (de `TURNOS 2026.xlsx`)

~14 colaboradores. Rotación automática mañana/tarde para **Claudia Torres,
Maribel, Shean Paul (Shan), Nicolás**; el resto va por rol (tours, lavandería,
cocina, aseo, servicio) con horario variable.
