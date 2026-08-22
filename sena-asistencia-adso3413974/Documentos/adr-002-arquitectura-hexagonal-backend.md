# ADR-002: Implementación de Arquitectura Hexagonal en el Backend con FastAPI

**Estado**: Aceptado
**¿Quién lo lee?** Desarrolladores backend que implementan o extienden casos de uso.
**¿Cuándo?** Al añadir una nueva regla de negocio, cambiar de motor de base de datos, o escribir tests.
**¿Para qué decisión sirve?** Define dónde debe vivir cada pieza de código para que el negocio no dependa de FastAPI ni de la base de datos.

## Contexto

La lógica de negocio (validación de OTP, control de intentos fallidos, reglas de contingencia, auditoría) debe permanecer estable aunque cambien los detalles de infraestructura: el framework web, el motor de base de datos, o el mecanismo de transporte en tiempo real (SSE, WebSockets, polling).

## Decisión

Adoptar **Arquitectura Hexagonal (Puertos y Adaptadores)**, con tres capas:

- **Dominio**: entidades de negocio puras — `Aprendiz`, `Checkpoint`, `CodigoOTP`, `RegistroAsistencia`, `ModificacionRegistro` — sin dependencias externas, con sus invariantes (p. ej. un `CodigoOTP` sabe calcular su propia vigencia).
- **Aplicación**: casos de uso (`ValidarIdentidadAprendiz`, `RegistrarAsistencia`, `AbrirCheckpoint`, `ModificarAsistenciaManual`) y **puertos** (interfaces) que declaran lo que la aplicación necesita de la infraestructura: `RepositorioAprendiz`, `RepositorioRegistroAsistencia`, `RelojUTC`, `NotificadorTiempoReal`.
- **Infraestructura**: adaptadores concretos — rutas FastAPI (adaptador de entrada), implementación SQL de los repositorios (adaptador de salida), adaptador SSE para tiempo real.

Se aplican explícitamente:
- **SRP (Responsabilidad Única)**: cada caso de uso resuelve una sola operación de negocio; los adaptadores solo traducen entre el mundo externo y los puertos.
- **DIP (Inversión de Dependencias)**: la capa de Aplicación depende de interfaces (puertos), nunca de implementaciones concretas; FastAPI y el motor SQL dependen del dominio, no al revés.

## Alternativas consideradas
- Arquitectura en capas tradicional (Controller-Service-Repository) sin puertos explícitos: descartada por acoplar implícitamente los casos de uso a la implementación de persistencia elegida.
- Monolito sin separación de capas (todo en `main.py`): válido para el prototipo inicial, pero descartado como destino final por dificultar el testing aislado de reglas de negocio como la ventana OTP o el conteo de intentos fallidos.

## Consecuencias

**Positivas**:
- Los casos de uso se prueban con mocks de los puertos, sin levantar FastAPI ni una base de datos real.
- El motor de base de datos (memoria → PostgreSQL) se reemplaza implementando un nuevo adaptador, sin tocar reglas de negocio.
- El mecanismo de tiempo real (SSE → WebSockets) es intercambiable detrás del puerto `NotificadorTiempoReal`.

**Negativas**:
- Incremento en la cantidad de clases e interfaces desde el inicio del proyecto, con mayor curva de entrada para desarrolladores nuevos.
- Sobrecarga de diseño para operaciones triviales que no lo justificarían en un sistema más pequeño.
