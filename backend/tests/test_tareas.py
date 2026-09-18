"""
Tests del motor del nivel Tranquilidad (app/tareas.py): re-escaneo
mensual de las suscripciones activas + email de resumen.

Todo mockeado (base de datos, scanner, envío de email): esto no prueba
que el cron llame bien a la API real, prueba la lógica de "qué le toca
a quién y qué pasa si algo falla" sin tocar red ni disco.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.notificaciones.enviar import ErrorEmail  # noqa: E402
from app.notificaciones.mensajes import mensaje_resumen_mensual  # noqa: E402
from app.tareas import ejecutar_re_escaneos_pendientes  # noqa: E402


def _resultado_falso(nota=80, estado="verde"):
    return {
        "checks": [],
        "resumen": {"puntuacion": nota, "estado_global": estado, "conteo": {}, "familias": []},
        "perfil_sitio": {"tipo_sitio": "landing_servicios", "senales": {}, "tamano": {}},
    }


def _suscripcion(id_=1, email="cliente@ejemplo.es", dominio="ejemplo.es"):
    return {"id": id_, "email": email, "dominio": dominio, "id_escaneo_origen": 1, "ultima_ejecucion": None}


# --- El motor, con todo mockeado ------------------------------------

def test_sin_suscripciones_pendientes_no_hace_nada():
    with patch("app.tareas.suscripciones_pendientes_de_re_escaneo", return_value=[]):
        resultados = asyncio.run(ejecutar_re_escaneos_pendientes())
    assert resultados == []


def test_una_suscripcion_pendiente_se_reescanea_y_avisa():
    suscripcion = _suscripcion()
    with (
        patch("app.tareas.suscripciones_pendientes_de_re_escaneo", return_value=[suscripcion]),
        patch("app.tareas.escaneo_anterior", return_value=None),
        patch("app.tareas.ejecutar_escaneo", new=AsyncMock(return_value=_resultado_falso())),
        patch("app.tareas.guardar_escaneo", return_value=(42, "token")),
        patch("app.tareas.marcar_ejecutada_suscripcion") as mock_marcar,
        patch("app.tareas.enviar_email") as mock_enviar,
    ):
        resultados = asyncio.run(ejecutar_re_escaneos_pendientes())

    assert len(resultados) == 1
    fila = resultados[0]
    assert fila["id_escaneo"] == 42
    assert fila["email_enviado"] is True
    assert fila["error"] is None
    mock_marcar.assert_called_once_with(1, 42)
    mock_enviar.assert_called_once()
    assert mock_enviar.call_args[0][0] == "cliente@ejemplo.es"


def test_si_el_email_falla_el_escaneo_ya_queda_guardado():
    """
    Un email que rebota no debe perder el escaneo ni forzar reintentar
    mañana: la suscripción se marca ejecutada igual, para no volver a
    escanear el mismo dominio dos veces en la misma ventana de 30 días.
    """
    suscripcion = _suscripcion()
    with (
        patch("app.tareas.suscripciones_pendientes_de_re_escaneo", return_value=[suscripcion]),
        patch("app.tareas.escaneo_anterior", return_value=None),
        patch("app.tareas.ejecutar_escaneo", new=AsyncMock(return_value=_resultado_falso())),
        patch("app.tareas.guardar_escaneo", return_value=(42, "token")),
        patch("app.tareas.marcar_ejecutada_suscripcion") as mock_marcar,
        patch("app.tareas.enviar_email", side_effect=ErrorEmail("Resend caído")),
    ):
        resultados = asyncio.run(ejecutar_re_escaneos_pendientes())

    fila = resultados[0]
    assert fila["id_escaneo"] == 42
    assert fila["email_enviado"] is False
    assert fila["error"] is None
    mock_marcar.assert_called_once_with(1, 42)


def test_un_dominio_caido_no_para_la_cola_de_los_demas():
    """Si escanear una suscripción lanza, las siguientes se procesan igual."""
    rota = _suscripcion(id_=1, dominio="caida.es")
    sana = _suscripcion(id_=2, dominio="sana.es")

    async def escaneo_o_fallo(dominio, **kwargs):
        if dominio == "caida.es":
            raise TimeoutError("no responde")
        return _resultado_falso()

    with (
        patch("app.tareas.suscripciones_pendientes_de_re_escaneo", return_value=[rota, sana]),
        patch("app.tareas.escaneo_anterior", return_value=None),
        patch("app.tareas.ejecutar_escaneo", new=AsyncMock(side_effect=escaneo_o_fallo)),
        patch("app.tareas.guardar_escaneo", return_value=(99, "token")),
        patch("app.tareas.marcar_ejecutada_suscripcion"),
        patch("app.tareas.enviar_email"),
    ):
        resultados = asyncio.run(ejecutar_re_escaneos_pendientes())

    assert len(resultados) == 2
    assert resultados[0]["error"] is not None
    assert resultados[0]["dominio"] == "caida.es"
    assert resultados[1]["error"] is None
    assert resultados[1]["dominio"] == "sana.es"


def test_pasa_la_comparacion_al_mensaje_si_hay_escaneo_anterior():
    suscripcion = _suscripcion()
    anterior = {"checks": [{"check": "ssl", "estado": "verde"}], "resumen": {"puntuacion": 90}, "fecha": "2026-08-01"}
    actual = _resultado_falso(nota=70)
    actual["checks"] = [{"check": "ssl", "estado": "rojo"}]

    with (
        patch("app.tareas.suscripciones_pendientes_de_re_escaneo", return_value=[suscripcion]),
        patch("app.tareas.escaneo_anterior", return_value=anterior),
        patch("app.tareas.ejecutar_escaneo", new=AsyncMock(return_value=actual)),
        patch("app.tareas.guardar_escaneo", return_value=(7, "token")),
        patch("app.tareas.marcar_ejecutada_suscripcion"),
        patch("app.tareas.enviar_email") as mock_enviar,
    ):
        asyncio.run(ejecutar_re_escaneos_pendientes())

    asunto = mock_enviar.call_args[0][1]
    assert "70/100" in asunto


# --- El contenido del email ------------------------------------------

def test_resumen_sin_comparacion_dice_que_es_la_primera_vez():
    asunto, cuerpo, html = mensaje_resumen_mensual("ejemplo.es", 80, None)
    assert "primera revisión" in cuerpo
    assert "primera revisión" in html


def test_resumen_sin_cambios_lo_dice_claramente():
    comparacion = {"mejoras": [], "empeoramientos": []}
    _, cuerpo, html = mensaje_resumen_mensual("ejemplo.es", 80, comparacion)
    assert "sigue exactamente igual" in cuerpo
    assert "sigue exactamente igual" in html


def test_resumen_con_empeoramiento_usa_tono_de_alerta():
    """El asunto y el saludo deben destacar cuando hay malas noticias."""
    comparacion = {"mejoras": [], "empeoramientos": [{"check": "ssl", "antes": "verde", "ahora": "rojo"}]}
    asunto, cuerpo, html = mensaje_resumen_mensual("ejemplo.es", 60, comparacion)
    assert "ha empeorado" in asunto
    assert "Atención" in cuerpo


def test_resumen_sin_empeoramiento_usa_tono_tranquilo():
    asunto, cuerpo, _ = mensaje_resumen_mensual("ejemplo.es", 90, None)
    assert "ha empeorado" not in asunto
    assert "Hola" in cuerpo


def test_resumen_con_empeoramiento_lo_lista():
    comparacion = {"mejoras": [], "empeoramientos": [{"check": "ssl", "antes": "verde", "ahora": "rojo"}]}
    _, cuerpo, html = mensaje_resumen_mensual("ejemplo.es", 60, comparacion)
    assert "ha empeorado" in cuerpo
    assert "certificado y cifrado" in cuerpo
    assert "certificado y cifrado" in html


def test_resumen_con_mejora_lo_lista():
    comparacion = {"mejoras": [{"check": "dns", "antes": "rojo", "ahora": "verde"}], "empeoramientos": []}
    _, cuerpo, html = mensaje_resumen_mensual("ejemplo.es", 90, comparacion)
    assert "ha mejorado" in cuerpo
    assert "correo (SPF/DKIM/DMARC)" in cuerpo
