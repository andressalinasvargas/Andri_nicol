-- ============================================================
-- Sistema Web de Toma de Asistencia SENA (Ficha ADSO 3413974)
-- Esquema de Base de Datos (SQL ANSI)
-- ============================================================

-- ------------------------------------------------------------
-- Tipos ENUM
-- ------------------------------------------------------------
CREATE TYPE tipo_documento_enum AS ENUM ('CC', 'TI', 'PEP', 'CE');
CREATE TYPE tipo_checkpoint_enum AS ENUM ('INICIO', 'RECESO', 'FIN');
CREATE TYPE estado_asistencia_enum AS ENUM ('ASISTIO', 'TARDE', 'AUSENTE');
CREATE TYPE origen_registro_enum AS ENUM ('AUTOMATICO', 'MANUAL');
CREATE TYPE motivo_manual_enum AS ENUM ('SIN_CELULAR', 'DISCAPACIDAD', 'FALLA_RED', 'OTRO');

-- ------------------------------------------------------------
-- Tabla: instructor
-- ------------------------------------------------------------
CREATE TABLE instructor (
    id_instructor       SERIAL PRIMARY KEY,
    numero_documento    VARCHAR(20) NOT NULL UNIQUE,
    tipo_documento      tipo_documento_enum NOT NULL,
    nombre_completo     VARCHAR(150) NOT NULL,
    correo              VARCHAR(150) NOT NULL UNIQUE,
    hash_password       VARCHAR(255) NOT NULL,
    creado_en           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Tabla: ficha (agrupa aprendices; necesaria para Habeas Data)
-- ------------------------------------------------------------
CREATE TABLE ficha (
    id_ficha            SERIAL PRIMARY KEY,
    codigo_ficha        VARCHAR(20) NOT NULL UNIQUE, -- ej. '3413974'
    programa            VARCHAR(150) NOT NULL,        -- ej. 'ADSO'
    id_instructor       INTEGER NOT NULL REFERENCES instructor(id_instructor),
    fecha_certificacion DATE,                          -- se llena al cerrar la ficha
    activa               BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ficha_activa ON ficha(activa);

-- ------------------------------------------------------------
-- Tabla: aprendiz
-- ------------------------------------------------------------
CREATE TABLE aprendiz (
    id_aprendiz          SERIAL PRIMARY KEY,
    numero_documento     VARCHAR(20) NOT NULL,
    tipo_documento       tipo_documento_enum NOT NULL,
    nombre_completo      VARCHAR(150) NOT NULL,
    id_ficha             INTEGER NOT NULL REFERENCES ficha(id_ficha),
    consentimiento_habeas_data BOOLEAN NOT NULL DEFAULT FALSE,
    consentimiento_fecha TIMESTAMP WITH TIME ZONE,
    anonimizado          BOOLEAN NOT NULL DEFAULT FALSE,
    creado_en            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_aprendiz_doc_ficha UNIQUE (numero_documento, id_ficha)
);

CREATE INDEX idx_aprendiz_doc_nombre ON aprendiz(numero_documento, nombre_completo);
CREATE INDEX idx_aprendiz_ficha ON aprendiz(id_ficha);

-- ------------------------------------------------------------
-- Tabla: checkpoint (jornada/momento de toma de asistencia)
-- ------------------------------------------------------------
CREATE TABLE checkpoint (
    id_checkpoint        SERIAL PRIMARY KEY,
    id_ficha              INTEGER NOT NULL REFERENCES ficha(id_ficha),
    tipo_checkpoint       tipo_checkpoint_enum NOT NULL,
    qr_token_estatico     VARCHAR(255) NOT NULL UNIQUE,
    abierto_en            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cerrado_en            TIMESTAMP WITH TIME ZONE,
    activo                BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_checkpoint_ficha_activo ON checkpoint(id_ficha, activo);

-- ------------------------------------------------------------
-- Tabla: codigo_verificacion (OTP rotatorio de 6 dígitos / 20s)
-- ------------------------------------------------------------
CREATE TABLE codigo_verificacion (
    id_codigo             SERIAL PRIMARY KEY,
    id_checkpoint          INTEGER NOT NULL REFERENCES checkpoint(id_checkpoint),
    codigo_otp             CHAR(6) NOT NULL,
    valido_desde_utc       TIMESTAMP WITH TIME ZONE NOT NULL,
    valido_hasta_utc       TIMESTAMP WITH TIME ZONE NOT NULL, -- valido_desde + 20s
    CONSTRAINT chk_ventana_otp CHECK (valido_hasta_utc > valido_desde_utc)
);

CREATE INDEX idx_codigo_checkpoint_vigencia ON codigo_verificacion(id_checkpoint, valido_desde_utc, valido_hasta_utc);

-- ------------------------------------------------------------
-- Tabla: registro_asistencia
-- ------------------------------------------------------------
CREATE TABLE registro_asistencia (
    id_registro            SERIAL PRIMARY KEY,
    id_aprendiz             INTEGER NOT NULL REFERENCES aprendiz(id_aprendiz),
    id_checkpoint            INTEGER NOT NULL REFERENCES checkpoint(id_checkpoint),
    estado                   estado_asistencia_enum NOT NULL,
    origen                   origen_registro_enum NOT NULL DEFAULT 'AUTOMATICO',
    editado                  BOOLEAN NOT NULL DEFAULT FALSE, -- flag visual indeleble "Editado"
    ip_registro              VARCHAR(45) NOT NULL,
    user_agent               VARCHAR(255) NOT NULL,
    marca_tiempo_utc         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_registro_aprendiz_checkpoint UNIQUE (id_aprendiz, id_checkpoint)
);

CREATE INDEX idx_registro_checkpoint ON registro_asistencia(id_checkpoint);
CREATE INDEX idx_registro_ip_checkpoint ON registro_asistencia(ip_registro, id_checkpoint); -- alerta de duplicidad

-- ------------------------------------------------------------
-- Tabla: modificacion_registro (auditoría inmutable de ediciones manuales)
-- ------------------------------------------------------------
CREATE TABLE modificacion_registro (
    id_modificacion        SERIAL PRIMARY KEY,
    id_registro              INTEGER NOT NULL REFERENCES registro_asistencia(id_registro),
    id_instructor             INTEGER NOT NULL REFERENCES instructor(id_instructor),
    estado_anterior            estado_asistencia_enum,
    estado_nuevo               estado_asistencia_enum NOT NULL,
    motivo                     motivo_manual_enum NOT NULL,
    justificacion_texto        VARCHAR(500),
    modificado_en_utc          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_modificacion_registro ON modificacion_registro(id_registro);

-- ------------------------------------------------------------
-- Tabla: intento_pendiente (control de 3 intentos fallidos / bloqueo 30s)
-- ------------------------------------------------------------
CREATE TABLE intento_pendiente (
    id_intento              SERIAL PRIMARY KEY,
    ip_origen                 VARCHAR(45) NOT NULL,
    id_checkpoint               INTEGER REFERENCES checkpoint(id_checkpoint),
    intentos_fallidos           SMALLINT NOT NULL DEFAULT 0,
    bloqueado_hasta_utc          TIMESTAMP WITH TIME ZONE,
    actualizado_en_utc           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_intento_ip_checkpoint UNIQUE (ip_origen, id_checkpoint)
);

CREATE INDEX idx_intento_ip ON intento_pendiente(ip_origen);

-- ------------------------------------------------------------
-- Nota sobre política de depuración automática (Habeas Data - Ley 1581/2012):
-- Ver Base de datos/diccionario-datos.md, sección "Política de Depuración".
-- ------------------------------------------------------------
