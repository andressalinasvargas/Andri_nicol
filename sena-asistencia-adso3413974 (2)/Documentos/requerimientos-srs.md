# Especificación de Requisitos de Software (SRS)
## Sistema Web de Toma de Asistencia SENA — Ficha ADSO 3413974
### (Formato compactado, basado en IEEE 830)

## 1. Introducción

**1.1 Propósito**
Definir los requisitos funcionales y no funcionales del sistema de toma de asistencia por checkpoint (QR + OTP) para la ficha ADSO 3413974.

**1.2 Alcance**
Aplicación web compuesta por un backend FastAPI, un frontend HTML/CSS/JS nativo (vista aprendiz y panel instructor) y una base de datos relacional. Cubre registro de identidad, validación dual, gestión de checkpoints, contingencias manuales y cumplimiento de Habeas Data.

**1.3 Definiciones**
- **Checkpoint**: momento de toma de asistencia (Inicio, Receso, Fin).
- **OTP**: código numérico de 6 dígitos, rotación cada 20 segundos.
- **QR estático**: código fijo por checkpoint que identifica la sesión (no rota).

## 2. Requisitos funcionales por módulo

### Módulo A — Identidad y acceso del aprendiz
- RF-A1: El sistema debe permitir ingresar tipo de documento (CC, TI, PEP, CE), número de documento y nombre completo.
- RF-A2: El backend debe validar el par Documento-Nombre contra la ficha activa antes de habilitar el ingreso del OTP.
- RF-A3: El sistema debe solicitar consentimiento de Habeas Data en el primer acceso del aprendiz.

### Módulo B — Validación dual (QR + OTP)
- RF-B1: El aprendiz debe escanear el QR estático del checkpoint proyectado por el instructor.
- RF-B2: El aprendiz debe ingresar el OTP vigente de 6 dígitos.
- RF-B3: El servidor debe validar la vigencia del OTP con marcas de tiempo UTC y una tolerancia de desfase de 500ms.
- RF-B4: El sistema debe mostrar un contador visual regresivo de los 20 segundos de vigencia del OTP.

### Módulo C — Gestión del instructor y tiempo real
- RF-C1: El instructor debe poder abrir un checkpoint, generando el QR y la secuencia de OTP.
- RF-C2: El instructor debe poder cerrar un checkpoint, marcando como "Ausente" a quienes no se registraron.
- RF-C3: El panel del instructor debe reflejar en tiempo real (SSE o polling) el estado de asistencia de la ficha.
- RF-C4: El instructor debe poder registrar o editar manualmente el estado de un aprendiz (Asistió, Tarde, Ausente), justificando la contingencia.
- RF-C5: Todo registro manual debe quedar marcado visualmente con el flag indeleble "Editado" y registrado en la tabla de auditoría `modificacion_registro`.

### Módulo D — Seguridad y cumplimiento
- RF-D1: Tras 3 intentos fallidos consecutivos desde la misma IP/checkpoint, el sistema debe bloquear el dispositivo por 30 segundos.
- RF-D2: El sistema debe registrar de forma inmutable la IP y el User-Agent de cada registro de asistencia.
- RF-D3: El sistema debe generar una alerta pasiva cuando una misma IP registre a múltiples aprendices en la misma jornada.
- RF-D4: El sistema debe anonimizar y depurar automáticamente los datos personales identificables 6 meses después de la certificación de la ficha (Ley 1581 de 2012).

## 3. Requisitos no funcionales

| Categoría | Requisito |
|---|---|
| Rendimiento | Los listados de asistencia deben cargar en menos de 2 segundos (soportado por índices en `registro_asistencia`, `aprendiz`). |
| Usabilidad | Flujo del aprendiz limitado a 3 pantallas secuenciales, mensajes de error claros y accionables. |
| Seguridad | Bloqueo por intentos fallidos, validación de expiración OTP en servidor (nunca solo en cliente), auditoría inmutable de modificaciones. |
| Accesibilidad | Cumplimiento WCAG 2.1 AA: mobile-first, fuente mínima 16px, alto contraste, estados diferenciados por texto/ícono además de color, foco visible por teclado. |
| Disponibilidad | El panel del instructor debe seguir mostrando el último estado conocido si se pierde momentáneamente la conexión en tiempo real. |
| Cumplimiento legal | Consentimiento explícito de Habeas Data y política de retención/anonimización de 6 meses. |

## 4. Restricciones
- Tipos de documento restringidos a CC, TI, PEP, CE.
- Vigencia OTP fija en 20 segundos, con tolerancia de 500ms.
- Bloqueo de dispositivo fijo en 30 segundos tras 3 fallos.
