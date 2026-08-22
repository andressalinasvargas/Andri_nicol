"""
Sistema Web de Toma de Asistencia SENA (Ficha ADSO 3413974)
Backend FastAPI.

Persistencia: almacenamiento en memoria estructurado como las tablas del
esquema SQL (ver Base de datos/esquema.sql). En un despliegue real, cada
"repositorio" (*_DB) se reemplaza por consultas a PostgreSQL manteniendo
la misma interfaz.
"""

import asyncio
import json
import random
import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

app = FastAPI(title="SENA Asistencia - Ficha ADSO 3413974")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Constantes de negocio
# ------------------------------------------------------------------
OTP_VIGENCIA_SEGUNDOS = 20
OTP_TOLERANCIA_MS = 500
MAX_INTENTOS_FALLIDOS = 3
BLOQUEO_SEGUNDOS = 30

TIPOS_DOCUMENTO_VALIDOS = {"CC", "TI", "PEP", "CE"}


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------
# Enums de dominio
# ------------------------------------------------------------------
class TipoCheckpoint(str, Enum):
    INICIO = "INICIO"
    RECESO = "RECESO"
    FIN = "FIN"


class EstadoAsistencia(str, Enum):
    ASISTIO = "ASISTIO"
    TARDE = "TARDE"
    AUSENTE = "AUSENTE"


class OrigenRegistro(str, Enum):
    AUTOMATICO = "AUTOMATICO"
    MANUAL = "MANUAL"


class MotivoManual(str, Enum):
    SIN_CELULAR = "SIN_CELULAR"
    DISCAPACIDAD = "DISCAPACIDAD"
    FALLA_RED = "FALLA_RED"
    OTRO = "OTRO"


# ------------------------------------------------------------------
# "Tablas" en memoria (equivalentes al esquema SQL)
# ------------------------------------------------------------------
FICHA_DB: Dict[int, dict] = {
    1: {
        "id_ficha": 1,
        "codigo_ficha": "3413974",
        "programa": "Análisis y Desarrollo de Software",
        "activa": True,
        "fecha_certificacion": None,
    }
}

APRENDIZ_DB: Dict[int, dict] = {
    1: {
        "id_aprendiz": 1,
        "numero_documento": "1001234567",
        "tipo_documento": "CC",
        "nombre_completo": "Laura Gómez Ramírez",
        "id_ficha": 1,
        "consentimiento_habeas_data": False,
        "consentimiento_fecha": None,
        "anonimizado": False,
    },
    2: {
        "id_aprendiz": 2,
        "numero_documento": "1002345678",
        "tipo_documento": "TI",
        "nombre_completo": "Juan Pérez Londoño",
        "id_ficha": 1,
        "consentimiento_habeas_data": False,
        "consentimiento_fecha": None,
        "anonimizado": False,
    },
}

CHECKPOINT_DB: Dict[int, dict] = {}
CODIGO_VERIFICACION_DB: Dict[int, dict] = {}
REGISTRO_ASISTENCIA_DB: Dict[int, dict] = {}
MODIFICACION_REGISTRO_DB: List[dict] = []
INTENTO_PENDIENTE_DB: Dict[str, dict] = {}  # key: f"{ip}:{id_checkpoint}"
SESIONES_DB: Dict[str, dict] = {}  # token -> {id_aprendiz, id_checkpoint, exp}

_next_ids = {"checkpoint": 1, "codigo": 1, "registro": 1, "modificacion": 1}


def siguiente_id(entidad: str) -> int:
    _next_ids[entidad] += 1
    return _next_ids[entidad] - 1


# ------------------------------------------------------------------
# Esquemas Pydantic (payloads)
# ------------------------------------------------------------------
class ValidarIdentidadRequest(BaseModel):
    numero_documento: str
    tipo_documento: str
    nombre_completo: str
    id_checkpoint: int
    acepta_habeas_data: bool = False


class RegistrarAsistenciaRequest(BaseModel):
    token_sesion: str
    codigo_otp: str = Field(min_length=6, max_length=6)


class AbrirCheckpointRequest(BaseModel):
    id_ficha: int
    tipo_checkpoint: TipoCheckpoint


class ModificarAsistenciaRequest(BaseModel):
    id_registro: Optional[int] = None
    id_aprendiz: int
    id_checkpoint: int
    estado_nuevo: EstadoAsistencia
    motivo: MotivoManual
    justificacion_texto: Optional[str] = None
    id_instructor: int = 1


# ------------------------------------------------------------------
# Utilidades de seguridad: control de intentos fallidos
# ------------------------------------------------------------------
def clave_intento(ip: str, id_checkpoint: int) -> str:
    return f"{ip}:{id_checkpoint}"


def verificar_bloqueo(ip: str, id_checkpoint: int) -> None:
    registro = INTENTO_PENDIENTE_DB.get(clave_intento(ip, id_checkpoint))
    if not registro:
        return
    bloqueado_hasta = registro.get("bloqueado_hasta_utc")
    if bloqueado_hasta and ahora_utc() < bloqueado_hasta:
        segundos_restantes = int((bloqueado_hasta - ahora_utc()).total_seconds()) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Dispositivo bloqueado por intentos fallidos. Intenta en {segundos_restantes}s.",
        )


def registrar_intento_fallido(ip: str, id_checkpoint: int) -> None:
    key = clave_intento(ip, id_checkpoint)
    registro = INTENTO_PENDIENTE_DB.setdefault(
        key,
        {"ip_origen": ip, "id_checkpoint": id_checkpoint, "intentos_fallidos": 0, "bloqueado_hasta_utc": None},
    )
    registro["intentos_fallidos"] += 1
    registro["actualizado_en_utc"] = ahora_utc()
    if registro["intentos_fallidos"] >= MAX_INTENTOS_FALLIDOS:
        registro["bloqueado_hasta_utc"] = ahora_utc() + timedelta(seconds=BLOQUEO_SEGUNDOS)
        registro["intentos_fallidos"] = 0


def limpiar_intentos(ip: str, id_checkpoint: int) -> None:
    INTENTO_PENDIENTE_DB.pop(clave_intento(ip, id_checkpoint), None)


def obtener_ip_cliente(request: Request) -> str:
    return request.client.host if request.client else "0.0.0.0"


# ------------------------------------------------------------------
# Alerta pasiva de duplicidad (misma IP registrando varios aprendices)
# ------------------------------------------------------------------
def detectar_duplicidad(ip: str, id_checkpoint: int) -> Optional[str]:
    aprendices_misma_ip = {
        r["id_aprendiz"]
        for r in REGISTRO_ASISTENCIA_DB.values()
        if r["ip_registro"] == ip and r["id_checkpoint"] == id_checkpoint
    }
    if len(aprendices_misma_ip) >= 2:
        return (
            f"ALERTA: la IP {ip} ha registrado a {len(aprendices_misma_ip) + 1} "
            f"aprendices distintos en el checkpoint {id_checkpoint}."
        )
    return None


# ==================================================================
# RUTAS DEL APRENDIZ
# ==================================================================
@app.post("/api/validar-identidad")
def validar_identidad(payload: ValidarIdentidadRequest, request: Request):
    ip = obtener_ip_cliente(request)
    verificar_bloqueo(ip, payload.id_checkpoint)

    if payload.tipo_documento not in TIPOS_DOCUMENTO_VALIDOS:
        raise HTTPException(status_code=400, detail="Tipo de documento no soportado.")

    checkpoint = CHECKPOINT_DB.get(payload.id_checkpoint)
    if not checkpoint or not checkpoint["activo"]:
        raise HTTPException(status_code=404, detail="Checkpoint no encontrado o inactivo.")

    aprendiz = next(
        (
            a
            for a in APRENDIZ_DB.values()
            if a["numero_documento"] == payload.numero_documento
            and a["nombre_completo"].strip().lower() == payload.nombre_completo.strip().lower()
            and a["id_ficha"] == checkpoint["id_ficha"]
        ),
        None,
    )

    if not aprendiz:
        registrar_intento_fallido(ip, payload.id_checkpoint)
        raise HTTPException(
            status_code=401,
            detail="El par Documento-Nombre no coincide con la ficha activa.",
        )

    if payload.acepta_habeas_data and not aprendiz["consentimiento_habeas_data"]:
        aprendiz["consentimiento_habeas_data"] = True
        aprendiz["consentimiento_fecha"] = ahora_utc()

    limpiar_intentos(ip, payload.id_checkpoint)

    token = uuid.uuid4().hex
    SESIONES_DB[token] = {
        "id_aprendiz": aprendiz["id_aprendiz"],
        "id_checkpoint": payload.id_checkpoint,
        "creado_en": ahora_utc(),
        "exp": ahora_utc() + timedelta(minutes=5),
    }

    return {
        "token_sesion": token,
        "id_aprendiz": aprendiz["id_aprendiz"],
        "nombre_completo": aprendiz["nombre_completo"],
        "requiere_consentimiento": not aprendiz["consentimiento_habeas_data"],
    }


@app.post("/api/registrar-asistencia")
def registrar_asistencia(
    payload: RegistrarAsistenciaRequest,
    request: Request,
    user_agent: Optional[str] = Header(default=None),
):
    ip = obtener_ip_cliente(request)
    sesion = SESIONES_DB.get(payload.token_sesion)
    if not sesion or ahora_utc() > sesion["exp"]:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada. Vuelve a validar tu identidad.")

    id_checkpoint = sesion["id_checkpoint"]
    verificar_bloqueo(ip, id_checkpoint)

    checkpoint = CHECKPOINT_DB.get(id_checkpoint)
    if not checkpoint or not checkpoint["activo"]:
        raise HTTPException(status_code=404, detail="Checkpoint no encontrado o inactivo.")

    codigo_vigente = next(
        (
            c
            for c in CODIGO_VERIFICACION_DB.values()
            if c["id_checkpoint"] == id_checkpoint
            and c["codigo_otp"] == payload.codigo_otp
            and c["valido_desde_utc"] - timedelta(milliseconds=OTP_TOLERANCIA_MS)
            <= ahora_utc()
            <= c["valido_hasta_utc"] + timedelta(milliseconds=OTP_TOLERANCIA_MS)
        ),
        None,
    )

    if not codigo_vigente:
        registrar_intento_fallido(ip, id_checkpoint)
        raise HTTPException(status_code=401, detail="Código OTP incorrecto o expirado.")

    limpiar_intentos(ip, id_checkpoint)

    ya_registrado = next(
        (
            r
            for r in REGISTRO_ASISTENCIA_DB.values()
            if r["id_aprendiz"] == sesion["id_aprendiz"] and r["id_checkpoint"] == id_checkpoint
        ),
        None,
    )
    if ya_registrado:
        raise HTTPException(status_code=409, detail="Ya existe un registro de asistencia para este checkpoint.")

    id_registro = siguiente_id("registro")
    registro = {
        "id_registro": id_registro,
        "id_aprendiz": sesion["id_aprendiz"],
        "id_checkpoint": id_checkpoint,
        "estado": EstadoAsistencia.ASISTIO.value,
        "origen": OrigenRegistro.AUTOMATICO.value,
        "editado": False,
        "ip_registro": ip,
        "user_agent": user_agent or "desconocido",
        "marca_tiempo_utc": ahora_utc(),
    }
    REGISTRO_ASISTENCIA_DB[id_registro] = registro

    alerta = detectar_duplicidad(ip, id_checkpoint)
    del SESIONES_DB[payload.token_sesion]

    aprendiz = APRENDIZ_DB[sesion["id_aprendiz"]]
    return {
        "mensaje": "Asistencia registrada correctamente.",
        "estado": registro["estado"],
        "tipo_checkpoint": checkpoint["tipo_checkpoint"],
        "nombre_completo": aprendiz["nombre_completo"],
        "marca_tiempo_utc": registro["marca_tiempo_utc"].isoformat(),
        "alerta_duplicidad": alerta,
    }


# ==================================================================
# RUTAS DEL INSTRUCTOR
# ==================================================================
def generar_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


@app.post("/api/checkpoint/abrir")
def abrir_checkpoint(payload: AbrirCheckpointRequest):
    ficha = FICHA_DB.get(payload.id_ficha)
    if not ficha or not ficha["activa"]:
        raise HTTPException(status_code=404, detail="Ficha no encontrada o inactiva.")

    id_checkpoint = siguiente_id("checkpoint")
    qr_token = secrets.token_urlsafe(24)
    ahora = ahora_utc()

    CHECKPOINT_DB[id_checkpoint] = {
        "id_checkpoint": id_checkpoint,
        "id_ficha": payload.id_ficha,
        "tipo_checkpoint": payload.tipo_checkpoint.value,
        "qr_token_estatico": qr_token,
        "abierto_en": ahora,
        "cerrado_en": None,
        "activo": True,
    }

    id_codigo = siguiente_id("codigo")
    codigo = generar_otp()
    CODIGO_VERIFICACION_DB[id_codigo] = {
        "id_codigo": id_codigo,
        "id_checkpoint": id_checkpoint,
        "codigo_otp": codigo,
        "valido_desde_utc": ahora,
        "valido_hasta_utc": ahora + timedelta(seconds=OTP_VIGENCIA_SEGUNDOS),
    }

    return {
        "id_checkpoint": id_checkpoint,
        "qr_token_estatico": qr_token,
        "tipo_checkpoint": payload.tipo_checkpoint.value,
        "codigo_otp_actual": codigo,
        "vigencia_segundos": OTP_VIGENCIA_SEGUNDOS,
    }


@app.post("/api/checkpoint/cerrar")
def cerrar_checkpoint(id_checkpoint: int):
    checkpoint = CHECKPOINT_DB.get(id_checkpoint)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint no encontrado.")
    checkpoint["activo"] = False
    checkpoint["cerrado_en"] = ahora_utc()

    for aprendiz in APRENDIZ_DB.values():
        if aprendiz["id_ficha"] != checkpoint["id_ficha"]:
            continue
        tiene_registro = any(
            r["id_aprendiz"] == aprendiz["id_aprendiz"] and r["id_checkpoint"] == id_checkpoint
            for r in REGISTRO_ASISTENCIA_DB.values()
        )
        if not tiene_registro:
            id_registro = siguiente_id("registro")
            REGISTRO_ASISTENCIA_DB[id_registro] = {
                "id_registro": id_registro,
                "id_aprendiz": aprendiz["id_aprendiz"],
                "id_checkpoint": id_checkpoint,
                "estado": EstadoAsistencia.AUSENTE.value,
                "origen": OrigenRegistro.AUTOMATICO.value,
                "editado": False,
                "ip_registro": "0.0.0.0",
                "user_agent": "sistema",
                "marca_tiempo_utc": ahora_utc(),
            }

    return {"mensaje": "Checkpoint cerrado.", "id_checkpoint": id_checkpoint}


@app.get("/api/checkpoint/{id_checkpoint}/otp-vigente")
def otp_vigente(id_checkpoint: int):
    """Rota el OTP si el código vigente ya expiró; útil para el panel del instructor."""
    checkpoint = CHECKPOINT_DB.get(id_checkpoint)
    if not checkpoint or not checkpoint["activo"]:
        raise HTTPException(status_code=404, detail="Checkpoint no encontrado o inactivo.")

    ahora = ahora_utc()
    vigente = next(
        (
            c
            for c in CODIGO_VERIFICACION_DB.values()
            if c["id_checkpoint"] == id_checkpoint and c["valido_hasta_utc"] > ahora
        ),
        None,
    )
    if not vigente:
        id_codigo = siguiente_id("codigo")
        vigente = {
            "id_codigo": id_codigo,
            "id_checkpoint": id_checkpoint,
            "codigo_otp": generar_otp(),
            "valido_desde_utc": ahora,
            "valido_hasta_utc": ahora + timedelta(seconds=OTP_VIGENCIA_SEGUNDOS),
        }
        CODIGO_VERIFICACION_DB[id_codigo] = vigente

    segundos_restantes = (vigente["valido_hasta_utc"] - ahora).total_seconds()
    return {
        "codigo_otp": vigente["codigo_otp"],
        "segundos_restantes": max(0, round(segundos_restantes, 1)),
    }


@app.get("/api/checkpoint/realtime")
async def checkpoint_realtime(id_checkpoint: int):
    """Server-Sent Events con el estado en tiempo real de la ficha para un checkpoint."""

    async def generador_eventos():
        while True:
            checkpoint = CHECKPOINT_DB.get(id_checkpoint)
            if not checkpoint:
                yield f"event: error\ndata: checkpoint no encontrado\n\n"
                break

            registros = [r for r in REGISTRO_ASISTENCIA_DB.values() if r["id_checkpoint"] == id_checkpoint]
            aprendices_ficha = [a for a in APRENDIZ_DB.values() if a["id_ficha"] == checkpoint["id_ficha"]]

            listado = []
            for aprendiz in aprendices_ficha:
                registro = next((r for r in registros if r["id_aprendiz"] == aprendiz["id_aprendiz"]), None)
                listado.append(
                    {
                        "id_aprendiz": aprendiz["id_aprendiz"],
                        "nombre_completo": aprendiz["nombre_completo"],
                        "estado": registro["estado"] if registro else None,
                        "editado": registro["editado"] if registro else False,
                        "origen": registro["origen"] if registro else None,
                    }
                )

            payload = {
                "id_checkpoint": id_checkpoint,
                "activo": checkpoint["activo"],
                "total_aprendices": len(aprendices_ficha),
                "total_registrados": len(registros),
                "listado": listado,
            }
            yield f"data: {json.dumps(payload)}\n\n"

            if not checkpoint["activo"]:
                break
            await asyncio.sleep(2)

    return StreamingResponse(generador_eventos(), media_type="text/event-stream")


@app.put("/api/asistencia/modificar")
def modificar_asistencia(payload: ModificarAsistenciaRequest):
    registro = None
    if payload.id_registro is not None:
        registro = REGISTRO_ASISTENCIA_DB.get(payload.id_registro)
    else:
        registro = next(
            (
                r
                for r in REGISTRO_ASISTENCIA_DB.values()
                if r["id_aprendiz"] == payload.id_aprendiz and r["id_checkpoint"] == payload.id_checkpoint
            ),
            None,
        )

    estado_anterior = registro["estado"] if registro else None

    if registro:
        registro["estado"] = payload.estado_nuevo.value
        registro["origen"] = OrigenRegistro.MANUAL.value
        registro["editado"] = True
    else:
        id_registro = siguiente_id("registro")
        registro = {
            "id_registro": id_registro,
            "id_aprendiz": payload.id_aprendiz,
            "id_checkpoint": payload.id_checkpoint,
            "estado": payload.estado_nuevo.value,
            "origen": OrigenRegistro.MANUAL.value,
            "editado": True,
            "ip_registro": "manual-instructor",
            "user_agent": "panel-instructor",
            "marca_tiempo_utc": ahora_utc(),
        }
        REGISTRO_ASISTENCIA_DB[id_registro] = registro

    id_modificacion = siguiente_id("modificacion")
    auditoria = {
        "id_modificacion": id_modificacion,
        "id_registro": registro["id_registro"],
        "id_instructor": payload.id_instructor,
        "estado_anterior": estado_anterior,
        "estado_nuevo": payload.estado_nuevo.value,
        "motivo": payload.motivo.value,
        "justificacion_texto": payload.justificacion_texto,
        "modificado_en_utc": ahora_utc().isoformat(),
    }
    MODIFICACION_REGISTRO_DB.append(auditoria)

    return {"mensaje": "Registro actualizado con auditoría.", "registro": registro, "auditoria": auditoria}


@app.get("/api/salud")
def salud():
    return {"estado": "ok", "hora_servidor_utc": ahora_utc().isoformat()}
