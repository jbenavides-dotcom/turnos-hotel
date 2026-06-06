# Sistema de Turnos · Hotel La Palma y El Tucán

Sistema dinámico para la **parrilla de turnos** del personal del hotel, conectado
a las **reservas (Cloudbeds)** y con cálculo de horas/extras. Reemplaza el manejo
manual en Excel (`TURNOS 2026.xlsx` + `formato horas extras.xlsx`).

## Contenido

- **`servidor_turnos.py`** + **`app.html`** — la **app funcional conectada**
  (backend local + frontend). Lee la ocupación real de Cloudbeds y guarda las
  ediciones de horarios. **Esto es lo que se usa.**
- **`start.bat`** — lanza la app con doble clic (Windows).
- **`DISENO-TURNOS.md`** — diseño completo: reglas, modelo de datos, fases,
  hallazgos de Cloudbeds y de los Excel de Lina.
- **`prototipo-parrilla.html`** — prototipo estático offline (sin backend), por
  si se quiere mostrar sin levantar el servidor.
- **`validar_cloudbeds.py`** — valida la conexión a la API de Cloudbeds.

## Cómo correr la app

```bash
python servidor_turnos.py        # o doble clic a start.bat (Windows)
# abre http://localhost:8787
```

Necesita Python 3 (solo librería estándar, sin pip install) y el token de
Cloudbeds disponible (vault `apis.json` en esta PC, o `CLOUDBEDS_API_TOKEN` en
otra terminal). La app:
- trae las **cabañas reservadas por noche** de Cloudbeds (regla >6 → refuerzo),
- muestra la **plantilla real** (~13 personas; rotación auto para Claudia Torres,
  Maribel, Shean y Nicolás),
- permite **editar cada turno** con clic (mañana/tarde/descanso/vacaciones/
  horario por rol) y **notas por día**; se guarda solo en `data/parrilla.json`.

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
