# Diccionario de Datos — Sistema de Asistencia SENA (Ficha ADSO 3413974)

## instructor
| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| id_instructor | SERIAL PK | No | Identificador único |
| numero_documento | VARCHAR(20) | No | Documento del instructor |
| tipo_documento | ENUM | No | CC, TI, PEP, CE |
| nombre_completo | VARCHAR(150) | No | Nombre del instructor |
| correo | VARCHAR(150) | No | Correo institucional, único |
| hash_password | VARCHAR(255) | No | Hash de la contraseña |
| creado_en | TIMESTAMPTZ | No | Fecha de creación del usuario |

## ficha
| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| id_ficha | SERIAL PK | No | Identificador único |
| codigo_ficha | VARCHAR(20) | No | Código SENA (ej. 3413974) |
| programa | VARCHAR(150) | No | Nombre del programa (ej. ADSO) |
| id_instructor | INTEGER FK | No | Instructor responsable |
| fecha_certificacion | DATE | Sí | Fecha en que la ficha se certifica |
| activa | BOOLEAN | No | Indica si la ficha sigue en formación |

## aprendiz
| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| id_aprendiz | SERIAL PK | No | Identificador único |
| numero_documento | VARCHAR(20) | No | Documento del aprendiz |
| tipo_documento | ENUM | No | CC, TI, PEP, CE |
| nombre_completo | VARCHAR(150) | No | Nombre del aprendiz |
| id_ficha | INTEGER FK | No | Ficha a la que pertenece |
| consentimiento_habeas_data | BOOLEAN | No | Consentimiento en primer acceso |
| consentimiento_fecha | TIMESTAMPTZ | Sí | Fecha del consentimiento |
| anonimizado | BOOLEAN | No | Marca si ya fue anonimizado |

## checkpoint
| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| id_checkpoint | SERIAL PK | No | Identificador único |
| id_ficha | INTEGER FK | No | Ficha asociada |
| tipo_checkpoint | ENUM | No | INICIO, RECESO, FIN |
| qr_token_estatico | VARCHAR(255) | No | Token fijo codificado en el QR |
| abierto_en | TIMESTAMPTZ | No | Apertura del checkpoint |
| cerrado_en | TIMESTAMPTZ | Sí | Cierre del checkpoint |
| activo | BOOLEAN | No | Si acepta registros actualmente |

## codigo_verificacion
| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| id_codigo | SERIAL PK | No | Identificador único |
| id_checkpoint | INTEGER FK | No | Checkpoint al que pertenece |
| codigo_otp | CHAR(6) | No | Código numérico rotatorio |
| valido_desde_utc | TIMESTAMPTZ | No | Inicio de vigencia (UTC) |
| valido_hasta_utc | TIMESTAMPTZ | No | Fin de vigencia — desde + 20s, tolerancia 500ms |

## registro_asistencia
| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| id_registro | SERIAL PK | No | Identificador único |
| id_aprendiz | INTEGER FK | No | Aprendiz registrado |
| id_checkpoint | INTEGER FK | No | Checkpoint del registro |
| estado | ENUM | No | ASISTIO, TARDE, AUSENTE |
| origen | ENUM | No | AUTOMATICO, MANUAL |
| editado | BOOLEAN | No | Flag visual indeleble "Editado" |
| ip_registro | VARCHAR(45) | No | IP de origen (auditoría) |
| user_agent | VARCHAR(255) | No | User-Agent del dispositivo |
| marca_tiempo_utc | TIMESTAMPTZ | No | Momento del registro |

## modificacion_registro
| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| id_modificacion | SERIAL PK | No | Identificador único |
| id_registro | INTEGER FK | No | Registro modificado |
| id_instructor | INTEGER FK | No | Instructor que modificó |
| estado_anterior | ENUM | Sí | Estado antes del cambio |
| estado_nuevo | ENUM | No | Estado después del cambio |
| motivo | ENUM | No | SIN_CELULAR, DISCAPACIDAD, FALLA_RED, OTRO |
| justificacion_texto | VARCHAR(500) | Sí | Justificación textual |
| modificado_en_utc | TIMESTAMPTZ | No | Momento de la modificación |

## intento_pendiente
| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| id_intento | SERIAL PK | No | Identificador único |
| ip_origen | VARCHAR(45) | No | IP que realiza los intentos |
| id_checkpoint | INTEGER FK | Sí | Checkpoint relacionado |
| intentos_fallidos | SMALLINT | No | Contador de fallos consecutivos |
| bloqueado_hasta_utc | TIMESTAMPTZ | Sí | Fin del bloqueo de 30s |
| actualizado_en_utc | TIMESTAMPTZ | No | Última actualización |

---

## Política de Depuración Automática (Habeas Data — Ley 1581 de 2012)

1. **Consentimiento**: se exige en el primer acceso del aprendiz (`aprendiz.consentimiento_habeas_data`), con fecha registrada (`consentimiento_fecha`).
2. **Retención**: los datos personales identificables se conservan mientras la ficha esté activa y hasta 6 meses después de `ficha.fecha_certificacion`.
3. **Anonimización automática**: transcurridos los 6 meses, un job programado debe:
   - Reemplazar `numero_documento` y `nombre_completo` en `aprendiz` por valores anonimizados (hash irreversible o `"ANONIMIZADO"`).
   - Marcar `aprendiz.anonimizado = TRUE`.
   - Conservar únicamente datos agregados/estadísticos de asistencia (sin identificación) para fines de reporte institucional.
4. **Auditoría**: los registros de `modificacion_registro` se conservan como evidencia de gobernanza, pero también quedan sujetos a anonimización del instructor/aprendiz referenciado tras el mismo período, salvo obligación legal de conservación distinta.
