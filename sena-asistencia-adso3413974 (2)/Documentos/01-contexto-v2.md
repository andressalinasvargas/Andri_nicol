# 01 — Contexto del Sistema (v2)
## Sistema Web de Toma de Asistencia SENA — Ficha ADSO 3413974 — Sede SENA Neiva, Huila

**¿Quién lo lee?** Instructores, coordinación académica y equipo de desarrollo que dará mantenimiento al sistema.
**¿Cuándo?** Antes de intervenir el sistema o de justificar su existencia ante coordinación.
**¿Para qué decisión sirve?** Sustenta por qué se reemplaza el registro manual/SOFIA Plus por un mecanismo digital de checkpoint, y fija los límites de lo que el sistema cubre.

## 1. Problema y justificación cuantitativa

El registro de asistencia en SOFIA Plus, realizado de forma manual al inicio, receso y fin de jornada, toma entre **8 y 15 minutos por checkpoint** en una ficha de 30 aprendices (llamado a lista, verificación de identidad, digitación posterior). Con 3 checkpoints diarios, esto representa hasta **45 minutos de inactividad formativa por jornada**, tiempo que se resta directamente de las horas de formación efectiva.

El sistema de asistencia por QR + OTP busca reducir ese tiempo a segundos por aprendiz mediante autoservicio validado, liberando el tiempo del instructor para su función pedagógica.

## 2. Marco SECI (Nonaka-Takeuchi) aplicado a esta documentación

Este repositorio de documentación es en sí mismo un ejercicio de gestión del conocimiento:

- **Externalización**: el conocimiento tácito de los instructores —las ineficiencias reales del aula, los cuellos de botella del registro manual, los casos de contingencia vividos día a día (aprendices sin celular, fallas de red, discapacidades)— se convierte en conocimiento explícito al quedar escrito en el SRS, el plan de contingencia y los ADR.
- **Combinación**: ese conocimiento explícito, antes disperso entre instructores individuales, se organiza y estructura en un repositorio único (`Documentos/`, `Backend/`, `Frontend/`, `Base de datos/`), combinándolo con estándares formales (IEEE 830, ADR, OpenAPI) para producir un activo institucional reutilizable por cualquier ficha del centro de formación, no solo la ADSO 3413974.

Las fases de Socialización (transferencia informal entre instructores) e Internalización (adopción del nuevo flujo como hábito) ocurren fuera de este repositorio, en la operación diaria del aula.

## 3. Alcance

### Incluye (IN)
- Registro de asistencia por checkpoint (Inicio, Receso, Fin) mediante QR estático + OTP rotatorio.
- Panel de instructor con visualización en tiempo real y registro manual justificado.
- Auditoría inmutable de modificaciones manuales.
- Cumplimiento de Habeas Data (consentimiento, retención, anonimización a 6 meses).
- **Funcionamiento en red local (LAN) sin dependencia de internet externo**: el backend y el frontend deben poder operar íntegramente dentro de la red del aula/sede, de modo que una caída del enlace a internet de la sede no interrumpa la toma de asistencia. Este es un requisito funcional crítico, no una mejora opcional.

### Excluye (OUT)
- Integración directa y automática con SOFIA Plus (se contempla como fase posterior).
- Biometría o reconocimiento facial como mecanismo de validación.
- Geolocalización satelital del dispositivo del aprendiz.
- Aplicación móvil nativa (el acceso es vía navegador web).

## 4. Alcance geográfico e institucional

Sede SENA Neiva, Huila. Piloto sobre la ficha ADSO 3413974, con vocación de extenderse a otras fichas del mismo centro de formación una vez validado el funcionamiento en LAN y la política de Habeas Data.
