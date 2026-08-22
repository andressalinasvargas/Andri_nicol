# ADR-003: Selección de Motor de Base de Datos Relacional y Estrategia de Tipos Estrictos

**Estado**: Aceptado
**¿Quién lo lee?** Desarrolladores backend y administradores de base de datos.
**¿Cuándo?** Al definir o modificar el esquema, o al evaluar una migración de motor.
**¿Para qué decisión sirve?** Justifica por qué la persistencia es relacional y con tipos restringidos, en vez de un almacenamiento flexible tipo documento.

## Contexto

Los registros de asistencia son evidencia formativa y administrativa: deben tener integridad referencial absoluta (un registro no puede existir sin un aprendiz y un checkpoint válidos), evitar datos huérfanos, y prevenir la inyección de valores fuera de dominio en campos como tipo de documento o estado de asistencia.

## Decisión

Implementar una **base de datos relacional (SQL ANSI / PostgreSQL)**, con:

- Tipos **ENUM** a nivel de esquema para `tipo_documento` (`CC`, `TI`, `PEP`, `CE`) y `estado_asistencia` (`ASISTIO`, `TARDE`, `AUSENTE`), de forma que el propio motor rechace valores fuera de dominio, sin depender únicamente de validación en la capa de aplicación.
- Llaves foráneas obligatorias entre `registro_asistencia`, `aprendiz` y `checkpoint`, y entre `modificacion_registro` y `registro_asistencia`, garantizando que no exista auditoría sin un registro que auditar.
- Restricciones `UNIQUE` compuestas (p. ej. un aprendiz no puede tener dos registros para el mismo checkpoint) que el motor aplica de forma atómica, evitando condiciones de carrera en registros simultáneos.
- Índices sobre `(numero_documento, nombre_completo)`, `(id_ficha, activo)` y `(ip_registro, id_checkpoint)` para sostener tiempos de carga del listado de aprendices **menores a 2 segundos**.

## Alternativas consideradas

- **Base de datos NoSQL orientada a documentos** (p. ej. MongoDB): descartada porque la validación de tipos y unicidad quedaría delegada por completo a la capa de aplicación, aumentando el riesgo de inconsistencias ante concurrencia (varios aprendices registrándose en el mismo segundo).
- **SQLite como motor definitivo**: válido para pruebas locales, pero descartado para producción por limitaciones de concurrencia de escritura en el escenario de checkpoint con múltiples aprendices simultáneos.

## Consecuencias

**Positivas**:
- Integridad de datos garantizada por el motor, no solo por el código de aplicación.
- Consultas de listado rápidas y predecibles gracias a los índices definidos junto al esquema.
- Auditoría confiable: es estructuralmente imposible tener una modificación sin su registro asociado.

**Negativas**:
- Menor flexibilidad para cambios de esquema rápidos frente a un motor NoSQL; añadir un nuevo estado o tipo de documento requiere una migración formal del ENUM.
- Requiere planeación de migraciones (versión de esquema) desde el primer despliegue.
