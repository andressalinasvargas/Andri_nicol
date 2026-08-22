# ADR-001 (v2): Mecanismo de Validación Dual QR + OTP

**Estado**: Aceptado (revisión v2)
**¿Quién lo lee?** Equipo de desarrollo backend/frontend y auditores de seguridad.
**¿Cuándo?** Al implementar o modificar el mecanismo de validación, o al responder una auditoría de seguridad/datos.
**¿Para qué decisión sirve?** Sustenta por qué la presencia del aprendiz se valida con QR estático + OTP en vez de otros mecanismos, y fija las reglas exactas de expiración, auditoría y protección de datos.

## Contexto

El sistema debe certificar presencia física real del aprendiz en el checkpoint (Inicio, Receso, Fin), resistiendo reenvío de capturas de pantalla o suplantación remota, y cumpliendo la Ley 1581 de 2012 sobre datos personales.

## Decisión

### 1. Algoritmo TOTP (RFC 6238)

El OTP de 6 dígitos se genera con el algoritmo estándar **TOTP (Time-based One-Time Password, RFC 6238)**:
- Ventana de validez: **20 segundos** por código.
- Base temporal: exclusivamente **UTC**, tomada del reloj del servidor (nunca del cliente).
- Tolerancia de desfase servidor-cliente: **500ms**, aplicada como margen adicional al validar `valido_desde_utc` / `valido_hasta_utc`.
- El secreto compartido (`seed`) del TOTP se genera por checkpoint, no es reutilizable entre jornadas.

### 2. Auditoría pasiva de dispositivo

Cada registro de asistencia almacena de forma **inmutable**:
- IP de origen (`ip_registro`).
- User-Agent del navegador (`user_agent`).
- Marca de tiempo UTC del registro (`marca_tiempo_utc`).

Un disparador de negocio evalúa, por checkpoint, cuántos aprendices distintos se han registrado desde la misma IP. Al alcanzar el umbral (≥3 aprendices), se emite una **alerta pasiva** visible en el panel del instructor. La alerta **no bloquea** el registro, dado que una IP compartida (Wi-Fi de aula) es el caso normal esperado, no la excepción.

### 3. Ciclo de vida del dato del aprendiz (Habeas Data)

1. **Consentimiento activo**: se solicita y registra en el primer acceso del aprendiz (`consentimiento_habeas_data`, `consentimiento_fecha`); sin este consentimiento no se completa el registro.
2. **Cifrado de campos sensibles**: `numero_documento` y `nombre_completo` se almacenan cifrados en reposo (cifrado simétrico a nivel de columna); el backend descifra solo en memoria durante la validación de identidad.
3. **Purga batch a los 6 meses**: un job programado, ejecutado sobre `fecha_certificacion` de la ficha, anonimiza (`anonimizado = TRUE`) los campos identificables transcurridos 6 meses de la certificación, conservando únicamente estadísticas agregadas.

### 4. Accesibilidad WCAG 2.1 AA (interfaz del aprendiz)

La interfaz del aprendiz es **mobile-first**, sin elementos decorativos que no aporten función, con:
- Fuente mínima de **16px**.
- Contraste alto entre texto y fondo.
- Estados (éxito, error, tarde) diferenciados por **texto e ícono**, nunca solo por color.
- Foco de teclado visible en todos los controles interactivos.

## Alternativas consideradas
- Geolocalización del dispositivo: descartada por dependencia de permisos y precisión deficiente en interiores.
- QR de un solo uso sin componente temporal: descartado por no impedir el reenvío dentro de la ventana de uso.
- Bloqueo automático (no pasivo) ante IP duplicada: descartado por alta tasa de falsos positivos en aulas con red compartida.

## Consecuencias
- **Positivas**: resistencia a suplantación remota, trazabilidad completa para auditoría, cumplimiento legal verificable.
- **Negativas**: dependencia estricta de sincronización horaria del servidor (NTP); un desfase de reloj no corregido invalida OTPs legítimos.
