# Sistema Dinámico de Parrilla de Turnos — Hotel LP&ET

> Estado: **diseño / prototipo** · Versión 0.1 · 2026-06-06
> Para revisar con Lina el **martes** (lunes 8 es festivo).
> Proyecto hermano del bot de cosecha (n8n + Supabase + app web).

## 1. Objetivo

Reemplazar la programación manual de turnos del personal de cabañas por un
sistema **dinámico conectado a las reservas**, que permita:

- Ver en formato **calendario** los horarios, el personal en servicio y las
  cabañas activas.
- Generar la **parrilla** automáticamente según las reglas de rotación.
- **Editar** la información desde la misma plataforma (no en papel/Excel).
- Avisar cuando la ocupación exige refuerzo de personal.

## 2. Reglas conocidas (de la reunión 2026-06-06)

| Regla | Detalle |
|---|---|
| Personal | Claudia Torres, Maribel, Shan, Nicolás (4 personas) |
| Descanso | Cada persona descansa **al menos 1 día/semana** |
| Rotación | **Semanal**, de lunes a lunes |
| Turno mañana | 7:00 a.m. – 3:00 p.m. |
| Turno tarde/cierre | 2:00 p.m. – cierre |
| Alternancia | Una semana mañana, la siguiente tarde (cada quien rota) |
| Refuerzo | Si hay **> 6 cabañas reservadas** → **2 personas** en turno de servicio |

## 3. Preguntas abiertas para Lina (confirmar martes)

Lina dijo que enviará **las reglas claras de rotación**. Estas son las que el
sistema necesita para ser exacto:

1. **Emparejamiento**: ¿quiénes arrancan en mañana y quiénes en tarde la
   primera semana? (define la rotación de todas las semanas siguientes).
2. **Día de descanso**: ¿lo fija el sistema o cada quien lo elige? ¿Puede caer
   cualquier día o hay días bloqueados (p. ej. fines de semana de alta ocupación)?
3. **"Turno de servicio"**: cuando hay > 6 cabañas, ¿las 2 personas son del
   **mismo** turno (refuerzo del de servicio) o se cruzan mañana+tarde?
4. **Fuente del # de cabañas reservadas**: ¿lo leemos automático de **Cloudbeds**
   (motor de reservas del hotel) o lo carga alguien a mano por día?
5. **Festivos** (como el lunes 8): ¿cambian el arranque de la rotación o se
   ignoran?
6. **Quién edita** la parrilla y quién solo la consulta (Lina, recepción, etc.).

## 4. Lógica de rotación (modelo propuesto)

Semana = lunes→lunes. Índice de semana `w` contado desde un **lunes de
referencia** (sugerido: 2026-06-08).

```
turno(persona, semana) =
    si (w es par)  -> turno_inicial(persona)
    si (w es impar)-> turno_opuesto(persona)
```

Con 4 personas y 2 turnos, cada semana quedan **2 en mañana + 2 en tarde**, y
todos alternan cada semana. Los descansos se **escalonan** para que ningún
turno quede sin cobertura.

**Refuerzo por ocupación** (por día):
```
requerido = (cabañas_reservadas > 6) ? 2 : 1
si (personas_en_servicio_ese_día < requerido) -> ALERTA de falta de personal
```

> Estos supuestos están implementados en el prototipo (`prototipo-parrilla.html`)
> para que Lina los vea y los corrija. NO son definitivos hasta su confirmación.

## 5. Modelo de datos (Supabase — Fase 2)

```
empleados        (id, nombre, turno_inicial, activo)
config_rotacion  (lunes_referencia, hora_manana_ini/fin, hora_tarde_ini, umbral_cabanas)
descansos        (empleado_id, semana, dia_descanso)          -- editable
ocupacion_dia    (fecha, cabanas_reservadas)                   -- de Cloudbeds o manual
parrilla_override(empleado_id, fecha, turno|descanso)          -- ediciones manuales puntuales
```

La parrilla base se **calcula** con la lógica de rotación; `parrilla_override`
guarda solo los cambios manuales (más liviano que materializar cada día).

## 6. Arquitectura por fases

- **Fase 1 — Prototipo (HOY)**: `prototipo-parrilla.html`, un solo archivo, sin
  backend. Muestra la vista calendario, la rotación y las alertas. Es lo que se
  le enseña a Lina el martes. Cabañas por día se editan a mano para demostrar.
- **Fase 2 — Datos reales**: tablas en Supabase + módulo en la app web
  (reutilizar el stack de `cafe-trazabilidad-v2`, Next.js). Edición desde la
  plataforma con login.
- **Fase 3 — Conexión a reservas**: traer el # de cabañas reservadas desde
  **Cloudbeds** (API) vía un workflow de **n8n** (igual que el bot de cosecha),
  o, si no hay API disponible, carga diaria manual/automatizada.

## 7. Vista calendario (prototipo)

- Selector de semana (cualquier fecha → su lunes).
- Fila por empleado, columna por día (Lun–Dom), celda = turno o "Descanso".
- Por día: conteo de personal en mañana/tarde, # de cabañas (editable) y
  semáforo de cobertura (verde/ámbar/rojo).

## 8. Próximos pasos

- [ ] Martes (2026-06-09): revisar prototipo con Lina y cerrar las 6 preguntas abiertas.
- [ ] Recibir de Lina las reglas finales de rotación.
- [x] **Confirmar conexión Cloudbeds por API** — HECHO 2026-06-06 (ver §9).
- [ ] Fase 2: crear tablas Supabase + módulo en la app web.

## 9. Conexión Cloudbeds — VALIDADA (2026-06-06)

**Sí tenemos API.** Token recuperado del workflow n8n "WhatsApp Sofia v3"
(inactivo) y guardado en el vault `key-apis/apis.json` (clave `cloudbeds`,
NUNCA a git).

- **Host:** `https://hotels.cloudbeds.com/api/v1.2`
- **propertyID:** `203345` (La Palma y el Tucán Hotel)
- **Auth:** header `Authorization: Bearer <api_token>` (token `cbat_…`, larga duración)
- **Pruebas OK (HTTP 200):** `getHotelDetails`, `getReservations`.
- **Demo de ocupación** (reservas vigentes por noche, en vivo): 06-jun = 7 cabañas
  → refuerzo; 07-jun = 6; semana de la reunión 0–1.
- **Endpoint clave para turnos:** `getReservations` (`status`, `startDate`,
  `endDate`, `adults`, `children`, `roomTypeName`…). Para el conteo exacto por
  noche conviene revisar el detalle de habitaciones (una reserva puede tener >1 cabaña).
- Validación reproducible: `validar_cloudbeds.py` (lee el token del entorno o del
  vault; sin secretos en el repo).

## 10. La realidad del archivo de Lina (dos Excel)

Lina trabaja HOY con dos Excel (en Descargas). El sistema debe calzar con ellos.

**`TURNOS 2026.xlsx`** — parrilla mensual (una hoja por mes: "ABRIL 26", "MAYO 26"…):
- Columnas = días; cada día ocupa **2 columnas** (hora entrada | hora salida).
- Filas = colaboradores. Celdas = horas, `DESCANSO` o `VACACIONES`.
- **Plantilla real ≈ 14 personas activas**, NO 4: Claudia Montenegro, Claudia
  Torres, Maribel Páez, Kelly Cruz, Diego Díaz, Deisy Rodríguez, Daniela Monroy,
  Nicolás Sarmiento, Shean Paul Gutiérrez, Nicolle, Zaira, Gerwin, Santiago
  (+ filas reservadas: Laura Sánchez, Diana Tunjano, Johan, Nelly, Auxiliar Aseo…).
- **Horarios variados** (7–3, 8–4, 9–5, 9:30–5:30, 10–6, 2–cierre). La rotación
  estricta mañana/tarde lun→lun aplica al subgrupo que mencionó Lina: **Claudia
  Torres, Maribel, Shean (Shan), Nicolás**. El resto va por **rol** (tours,
  lavandería, cocina, aseo, servicio).
- Fila de **notas** al pie de cada día ("Clau M lavandería", "Kelly hace tour",
  "Zaira en servicio"…) → el sistema debe permitir notas por día.

**`formato horas extras.xlsx`** (hoja "Horarios") — cálculo de nómina derivado de
la parrilla, una fila por persona-día:
- Columnas: Trabajador, Fecha, Hora Límite (19:00), Entrada, Salida, Horas
  laboradas, Recargos, **Horas extras**, **Recargo nocturno**, Observaciones,
  Cargo, Diurnas, Nocturnas.
- Hoy tiene `#VALUE!` en filas de DESCANSO y ruido de coma flotante. **Oportunidad:**
  el sistema genera la parrilla Y calcula horas/extras/recargos sin esos errores.

### Implicación de diseño (revisada)
El sistema dinámico = **una sola herramienta** que (1) arma/edita la **parrilla**
(reemplaza `TURNOS 2026.xlsx`), (2) trae la **ocupación** de Cloudbeds (regla >6
cabañas → 2 en servicio), (3) **calcula horas, extras y recargos** por persona-día
(reemplaza `formato horas extras.xlsx`), y (4) soporta los ~14 colaboradores,
descansos, vacaciones, notas por día y la rotación automática del subgrupo de 4.
