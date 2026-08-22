/* ==========================================================
   Sistema de Asistencia SENA — Ficha ADSO 3413974
   app.js — lógica de cliente (vista aprendiz + panel instructor)
   ========================================================== */

const API_BASE = window.API_BASE || "http://localhost:8000";

/* -----------------------------------------------------------
   Utilidades comunes
   ----------------------------------------------------------- */
function generarUserAgentSimulado() {
  // El navegador ya envía su propio User-Agent real en el header HTTP;
  // aquí solo lo leemos para reflejarlo en el payload cuando la API lo pide.
  return navigator.userAgent;
}

function escaparHtml(texto) {
  // Previene XSS almacenado: el nombre del aprendiz hoy viene de un seed fijo
  // en el backend, pero en producción vendrá de un roster importado (SOFIA
  // Plus, CSV) que no debe tratarse como HTML confiable en ningún caso.
  const div = document.createElement("div");
  div.textContent = texto ?? "";
  return div.innerHTML;
}

async function llamarApi(ruta, opciones = {}) {
  const respuesta = await fetch(`${API_BASE}${ruta}`, {
    headers: {
      "Content-Type": "application/json",
      "User-Agent": generarUserAgentSimulado(),
      ...(opciones.headers || {}),
    },
    ...opciones,
  });
  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) {
    const error = new Error(datos.detail || "Error de comunicación con el servidor.");
    error.status = respuesta.status;
    throw error;
  }
  return datos;
}

/* =============================================================
   VISTA APRENDIZ (index.html)
   ============================================================= */
const formIdentidad = document.getElementById("form-identidad");

if (formIdentidad) {
  const pantallaIdentidad = document.getElementById("pantalla-identidad");
  const pantallaOtp = document.getElementById("pantalla-otp");
  const pantallaExito = document.getElementById("pantalla-exito");

  const errorIdentidad = document.getElementById("error-identidad");
  const errorOtp = document.getElementById("error-otp");

  const segundosRestantesEl = document.getElementById("segundos-restantes");
  const barraRellenoEl = document.getElementById("barra-relleno");

  // El checkpoint activo se identifica vía parámetro ?checkpoint=ID en la URL
  // que el instructor comparte junto con el QR proyectado.
  const params = new URLSearchParams(window.location.search);
  const idCheckpoint = Number(params.get("checkpoint") || 1);

  let tokenSesion = null;
  let temporizadorId = null;
  const DURACION_OTP = 20;

  function mostrarPantalla(pantalla) {
    [pantallaIdentidad, pantallaOtp, pantallaExito].forEach((p) => p.classList.remove("activa"));
    pantalla.classList.add("activa");
  }

  function mostrarError(elemento, mensaje) {
    elemento.innerHTML = mensaje
      ? `<div class="mensaje-error"><span>${mensaje}</span></div>`
      : "";
  }

  function iniciarTemporizadorOtp() {
    let segundos = DURACION_OTP;
    segundosRestantesEl.textContent = segundos;
    barraRellenoEl.style.width = "100%";

    clearInterval(temporizadorId);
    temporizadorId = setInterval(() => {
      segundos -= 1;
      if (segundos <= 0) {
        segundos = DURACION_OTP; // el backend rota el OTP en su propio ciclo de 20s
      }
      segundosRestantesEl.textContent = segundos;
      barraRellenoEl.style.width = `${(segundos / DURACION_OTP) * 100}%`;
    }, 1000);
  }

  // -------- Paso 1: validar identidad --------
  formIdentidad.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    mostrarError(errorIdentidad, "");

    const numeroDocumento = document.getElementById("numero_documento").value.trim();
    const tipoDocumento = document.getElementById("tipo_documento").value;
    const nombreCompleto = document.getElementById("nombre_completo").value.trim();
    const aceptaHabeasData = document.getElementById("acepta_habeas_data").checked;

    if (!numeroDocumento || !/^[0-9]+$/.test(numeroDocumento)) {
      mostrarError(errorIdentidad, "Ingresa un número de documento válido (solo dígitos).");
      return;
    }
    if (!nombreCompleto || nombreCompleto.length < 3) {
      mostrarError(errorIdentidad, "Ingresa tu nombre completo.");
      return;
    }

    try {
      const respuesta = await llamarApi("/api/validar-identidad", {
        method: "POST",
        body: JSON.stringify({
          numero_documento: numeroDocumento,
          tipo_documento: tipoDocumento,
          nombre_completo: nombreCompleto,
          id_checkpoint: idCheckpoint,
          acepta_habeas_data: aceptaHabeasData,
        }),
      });

      tokenSesion = respuesta.token_sesion;
      mostrarPantalla(pantallaOtp);
      iniciarTemporizadorOtp();
      document.getElementById("codigo_otp").focus();
    } catch (error) {
      mostrarError(errorIdentidad, error.message);
    }
  });

  // -------- Paso 2: verificar OTP --------
  const formOtp = document.getElementById("form-otp");
  formOtp.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    mostrarError(errorOtp, "");

    const codigoOtp = document.getElementById("codigo_otp").value.trim();
    if (!/^[0-9]{6}$/.test(codigoOtp)) {
      mostrarError(errorOtp, "El código debe tener exactamente 6 dígitos numéricos.");
      return;
    }

    try {
      const respuesta = await llamarApi("/api/registrar-asistencia", {
        method: "POST",
        body: JSON.stringify({ token_sesion: tokenSesion, codigo_otp: codigoOtp }),
      });

      clearInterval(temporizadorId);

      document.getElementById("detalle-nombre").textContent = respuesta.nombre_completo;
      document.getElementById("detalle-checkpoint").textContent = respuesta.tipo_checkpoint;
      const fecha = new Date(respuesta.marca_tiempo_utc);
      document.getElementById("detalle-fecha").textContent = fecha.toLocaleDateString("es-CO");
      document.getElementById("detalle-hora").textContent = fecha.toLocaleTimeString("es-CO");

      mostrarPantalla(pantallaExito);
    } catch (error) {
      mostrarError(errorOtp, error.message);
    }
  });

  document.getElementById("btn-volver-identidad").addEventListener("click", () => {
    clearInterval(temporizadorId);
    mostrarPantalla(pantallaIdentidad);
  });

  document.getElementById("btn-nuevo-registro").addEventListener("click", () => {
    formIdentidad.reset();
    document.getElementById("codigo_otp").value = "";
    mostrarPantalla(pantallaIdentidad);
  });
}

/* =============================================================
   PANEL DEL INSTRUCTOR (instructor.html)
   ============================================================= */
const btnAbrirCheckpoint = document.getElementById("btn-abrir-checkpoint");

if (btnAbrirCheckpoint) {
  const btnCerrarCheckpoint = document.getElementById("btn-cerrar-checkpoint");
  const tipoCheckpointSelect = document.getElementById("tipo_checkpoint_select");
  const etiquetaCheckpointActivo = document.getElementById("etiqueta-checkpoint-activo");
  const textoQr = document.getElementById("texto-qr");
  const otpGigante = document.getElementById("otp-gigante");
  const otpSegundos = document.getElementById("otp-segundos");
  const otpBarra = document.getElementById("otp-barra");
  const resumenConteo = document.getElementById("resumen-conteo");
  const cuerpoTabla = document.getElementById("cuerpo-tabla-asistencia");

  const modalFondo = document.getElementById("modal-fondo");
  const modalNombreAprendiz = document.getElementById("modal-nombre-aprendiz");
  const modalEstado = document.getElementById("modal-estado");
  const modalMotivo = document.getElementById("modal-motivo");
  const modalJustificacion = document.getElementById("modal-justificacion");

  let idCheckpointActivo = null;
  let intervaloOtp = null;
  let intervaloListado = null;
  let aprendizModalActual = null;

  const ID_FICHA = 1;
  const DURACION_OTP = 20;

  function etiquetaEstado(estado) {
    if (estado === "ASISTIO") return { texto: "Asistió", clase: "etiqueta-estado--asistio" };
    if (estado === "TARDE") return { texto: "Tarde", clase: "etiqueta-estado--tarde" };
    if (estado === "AUSENTE") return { texto: "Ausente", clase: "etiqueta-estado--ausente" };
    return { texto: "Sin registrar", clase: "" };
  }

  async function refrescarOtp() {
    if (!idCheckpointActivo) return;
    try {
      const datos = await llamarApi(`/api/checkpoint/${idCheckpointActivo}/otp-vigente`);
      otpGigante.textContent = datos.codigo_otp;
      otpSegundos.textContent = Math.ceil(datos.segundos_restantes);
      otpBarra.style.width = `${(datos.segundos_restantes / DURACION_OTP) * 100}%`;
    } catch (error) {
      // El checkpoint pudo haberse cerrado; se detiene el refresco.
      clearInterval(intervaloOtp);
    }
  }

  async function refrescarListado() {
    if (!idCheckpointActivo) return;
    try {
      // Polling simple sobre el estado agregado (alternativa a SSE en clientes sin soporte).
      const eventSource = null;
      const respuesta = await fetch(`${API_BASE}/api/checkpoint/realtime?id_checkpoint=${idCheckpointActivo}`);
      const lector = respuesta.body.getReader();
      const decodificador = new TextDecoder();
      const { value } = await lector.read();
      const texto = decodificador.decode(value);
      const linea = texto.split("\n").find((l) => l.startsWith("data:"));
      if (!linea) return;
      const datos = JSON.parse(linea.replace("data:", "").trim());

      resumenConteo.textContent = `${datos.total_registrados} de ${datos.total_aprendices} aprendices registrados.`;

      cuerpoTabla.innerHTML = "";
      datos.listado.forEach((item) => {
        const { texto: textoEstado, clase } = etiquetaEstado(item.estado);
        const nombreSeguro = escaparHtml(item.nombre_completo);
        const fila = document.createElement("tr");
        fila.innerHTML = `
          <td>${nombreSeguro}</td>
          <td>
            <span class="etiqueta-estado ${clase}">${textoEstado}</span>
            ${item.editado ? '<span class="marca-editado">Editado</span>' : ""}
          </td>
          <td>
            <div class="acciones-fila">
              <button type="button" class="boton-mini" data-id="${item.id_aprendiz}" data-nombre="${nombreSeguro}" data-accion="manual">
                Registro manual
              </button>
            </div>
          </td>`;
        cuerpoTabla.appendChild(fila);
      });

      cuerpoTabla.querySelectorAll('[data-accion="manual"]').forEach((boton) => {
        boton.addEventListener("click", () => abrirModal(boton.dataset.id, boton.dataset.nombre));
      });

      lector.cancel();
    } catch (error) {
      // Si el checkpoint no existe más, se detiene el polling.
    }
  }

  btnAbrirCheckpoint.addEventListener("click", async () => {
    try {
      const respuesta = await llamarApi("/api/checkpoint/abrir", {
        method: "POST",
        body: JSON.stringify({
          id_ficha: ID_FICHA,
          tipo_checkpoint: tipoCheckpointSelect.value,
        }),
      });

      idCheckpointActivo = respuesta.id_checkpoint;
      etiquetaCheckpointActivo.textContent = `${respuesta.tipo_checkpoint} (#${idCheckpointActivo})`;
      textoQr.textContent = respuesta.qr_token_estatico;

      btnAbrirCheckpoint.disabled = true;
      btnCerrarCheckpoint.disabled = false;

      clearInterval(intervaloOtp);
      clearInterval(intervaloListado);
      refrescarOtp();
      refrescarListado();
      intervaloOtp = setInterval(refrescarOtp, 1000);
      intervaloListado = setInterval(refrescarListado, 3000);
    } catch (error) {
      alert(`No se pudo abrir el checkpoint: ${error.message}`);
    }
  });

  btnCerrarCheckpoint.addEventListener("click", async () => {
    if (!idCheckpointActivo) return;
    try {
      await llamarApi(`/api/checkpoint/cerrar?id_checkpoint=${idCheckpointActivo}`, { method: "POST" });
      clearInterval(intervaloOtp);
      clearInterval(intervaloListado);
      refrescarListado();
      btnAbrirCheckpoint.disabled = false;
      btnCerrarCheckpoint.disabled = true;
      idCheckpointActivo = null;
    } catch (error) {
      alert(`No se pudo cerrar el checkpoint: ${error.message}`);
    }
  });

  function abrirModal(idAprendiz, nombre) {
    aprendizModalActual = idAprendiz;
    modalNombreAprendiz.textContent = nombre;
    modalFondo.classList.add("activo");
  }

  document.getElementById("btn-cancelar-modal").addEventListener("click", () => {
    modalFondo.classList.remove("activo");
  });

  document.getElementById("btn-guardar-modal").addEventListener("click", async () => {
    if (!aprendizModalActual || !idCheckpointActivo) return;
    try {
      await llamarApi("/api/asistencia/modificar", {
        method: "PUT",
        body: JSON.stringify({
          id_aprendiz: Number(aprendizModalActual),
          id_checkpoint: idCheckpointActivo,
          estado_nuevo: modalEstado.value,
          motivo: modalMotivo.value,
          justificacion_texto: modalJustificacion.value || null,
        }),
      });
      modalFondo.classList.remove("activo");
      modalJustificacion.value = "";
      refrescarListado();
    } catch (error) {
      alert(`No se pudo guardar el registro manual: ${error.message}`);
    }
  });
}
