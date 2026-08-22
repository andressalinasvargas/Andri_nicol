# ADR-004: Diseño API-First y Definición de Contratos bajo Estándar OpenAPI

**Estado**: Aceptado
**¿Quién lo lee?** Equipos de frontend y backend, y cualquier integrador externo (p. ej. futura integración con SOFIA Plus).
**¿Cuándo?** Antes de iniciar el desarrollo de una nueva funcionalidad, o al integrar un cliente externo.
**¿Para qué decisión sirve?** Fija que el contrato de la API se acuerda y documenta antes de escribir código, evitando que frontend y backend se bloqueen mutuamente.

## Contexto

El frontend mobile-first del aprendiz y el panel del instructor deben poder desarrollarse en paralelo con el backend FastAPI, sin que un equipo espere a que el otro termine su implementación para empezar a trabajar.

## Decisión

Adoptar el enfoque **API-First**: los contratos de todos los servicios RESTful se definen previamente en formato **OpenAPI (YAML)**, incluyendo:

- Rutas y verbos: `POST /api/validar-identidad`, `POST /api/registrar-asistencia`, `POST /api/checkpoint/abrir`, `POST /api/checkpoint/cerrar`, `GET /api/checkpoint/realtime`, `PUT /api/asistencia/modificar`.
- Esquemas de request/response para cada ruta (payloads de entrada y salida), incluyendo los campos de auditoría (`ip_registro`, `user_agent`, `editado`).
- Códigos de estado HTTP documentados explícitamente por ruta:
  - `200` — operación exitosa (consulta o actualización).
  - `201` — recurso creado (apertura de checkpoint).
  - `400` — payload inválido o tipo de documento no soportado.
  - `401` — identidad no coincide con la ficha activa, u OTP incorrecto/expirado.
  - `409` — conflicto (registro duplicado para el mismo checkpoint).
  - `429` — dispositivo bloqueado por intentos fallidos (3 intentos → 30 segundos).

Con el contrato OpenAPI publicado, el equipo de frontend puede levantar un **mock server** generado automáticamente a partir del YAML y construir contra él, mientras el equipo de backend implementa la lógica real detrás de los mismos contratos.

## Alternativas consideradas
- **Code-first** (generar el contrato a partir del código FastAPI ya implementado): descartado como práctica principal porque obliga al frontend a esperar una implementación concreta antes de poder avanzar, y porque las inconsistencias de contrato se detectan tarde, ya en integración.
- **Comunicación informal de contratos** (documentos de texto libre o mensajería): descartada por no ser verificable automáticamente ni permitir generación de mocks o validación de payloads.

## Consecuencias

**Positivas**:
- Desarrollo simultáneo y desacoplado de frontend y backend.
- Generación automática de mock servers y de documentación interactiva (Swagger UI) desde el mismo contrato.
- Menor cantidad de errores de integración tardíos, al validar payloads contra el esquema desde etapas tempranas.

**Negativas**:
- Requiere tiempo de diseño explícito del contrato antes de escribir la primera línea de código de negocio.
- Cambios de alcance a mitad de desarrollo obligan a renegociar y re-versionar el contrato OpenAPI, no solo el código.
