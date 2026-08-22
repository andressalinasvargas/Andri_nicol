# Plan de Contingencia
## Sistema de Toma de Asistencia SENA — Ficha ADSO 3413974

Este plan define la respuesta operativa ante situaciones que impiden el registro automático (QR + OTP) de un aprendiz, en concordancia con RF-C4 y RF-C5 del SRS.

## 1. Aprendiz sin celular
- **Respuesta**: el instructor registra manualmente el estado desde el panel (`PUT /api/asistencia/modificar`), motivo `SIN_CELULAR`.
- **Evidencia**: el registro queda marcado "Editado" y auditado con instructor, fecha y justificación.
- **Prevención**: habilitar un punto físico (tablet o equipo del salón) como estación de respaldo para escaneo compartido bajo supervisión del instructor.

## 2. Aprendices en situación de discapacidad
- **Visual**: apoyo verbal del instructor o de un compañero de apoyo para leer el OTP en voz alta; alternativa de registro manual inmediato sin necesidad de completar el flujo QR+OTP.
- **Auditiva**: toda la interfaz debe depender de texto e íconos, no de sonido (ya contemplado en RF no funcionales de accesibilidad).
- **Motriz**: el instructor puede completar el registro manual en su nombre, motivo `DISCAPACIDAD`, dejando la justificación correspondiente.

## 3. Falla técnica del código QR (no escanea o no se proyecta)
- **Respuesta inmediata**: el instructor comunica verbalmente el enlace directo con el parámetro `?checkpoint=ID` para que los aprendices accedan sin depender del escaneo.
- **Si persiste**: se recurre a registro manual masivo justificado con motivo `FALLA_RED` u `OTRO`, documentando la causa técnica.

## 4. Código OTP expirado antes de que el aprendiz lo ingrese
- **Causa esperada**: la rotación de 20 segundos es intencional; el sistema simplemente solicita reintentar con el código vigente.
- **Respuesta**: el frontend muestra el error "Código OTP incorrecto o expirado" y permite reingresar sin penalizar como intento fallido de seguridad si el aprendiz corrige a tiempo (el conteo de intentos fallidos solo aplica a intentos con datos objetivamente incorrectos, no a la expiración natural del ciclo).

## 5. Pérdida de conectividad a internet en el aula
- **Respuesta**: el instructor cambia a modo de registro manual para toda la ficha, marcando cada aprendiz según lista física o verificación visual, motivo `FALLA_RED`.
- **Regularización posterior**: una vez restablecida la conexión, los registros manuales ya quedaron persistidos (no dependen de que el aprendiz tenga red, solo el instructor).

## 6. Intentos duplicados o fraudulentos (misma IP, múltiples aprendices)
- **Detección**: el sistema emite una alerta pasiva (`alerta_duplicidad`) cuando una misma IP registra a 3 o más aprendices distintos en el mismo checkpoint.
- **Respuesta**: la alerta no bloquea el registro automáticamente (para no penalizar salones con IP compartida legítima), pero queda visible para que el instructor la revise y, si corresponde, invalide registros específicos vía edición manual con motivo `OTRO`.
- **Escalamiento**: casos reincidentes se documentan para revisión por coordinación académica.

## 7. Bloqueo por intentos fallidos (3 intentos / 30 segundos)
- **Respuesta**: el aprendiz debe esperar el tiempo indicado por el sistema antes de reintentar.
- **Si el bloqueo es injustificado** (p. ej. error del propio sistema): el instructor puede registrar manualmente sin esperar el desbloqueo, documentando la causa.
