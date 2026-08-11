"""
Punto de arranque de la API de Pipo.

Esto es lo primero que se ejecuta. De momento no hace ningún análisis
todavía — solo confirma que el servidor está vivo. Los checks reales
(SSL, cabeceras, DNS...) vivirán en app/checks/ y se irán conectando
aquí como endpoints a medida que los construyamos.
"""

import asyncio
import re
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.checks.archivos_expuestos import comprobar_archivos_expuestos
from app.checks.dns_check import comprobar_dns
from app.checks.headers_check import comprobar_headers
from app.checks.mixed_content_check import comprobar_mixed_content
from app.checks.pagina import obtener_pagina
from app.checks.privacidad_check import comprobar_privacidad
from app.checks.rendimiento_check import comprobar_rendimiento
from app.checks.seo_check import comprobar_seo
from app.checks.ssl_check import comprobar_ssl
from app.checks.tecnologia_check import comprobar_tecnologia
from app.config import GMAIL_EMAIL, TELEFONO_BIZUM
from app.database import (
    guardar_escaneo,
    guardar_informe,
    guardar_lead,
    guardar_pedido,
    guardar_rendimiento,
    guardar_soluciones,
    inicializar_db,
    obtener_escaneo,
)
from app.ia.cliente import ErrorIA
from app.ia.interpretar import interpretar_hallazgos
from app.ia.soluciones import generar_soluciones
from app.notificaciones.enviar import ErrorEmail, enviar_email
from app.notificaciones.mensajes import mensaje_pedido_alberto, mensaje_pedido_cliente
from app.pdf.generar_pdf import generar_pdf_informe
from app.puntuacion import calcular_precio_arreglo
from app.scanner import ejecutar_escaneo

# Precio del nivel de pago "soluciones + PDF" (ver CLAUDE.md, P2).
PRECIO_INFORME_COMPLETO = 19

# El "limitador": decide cuántas peticiones permite por IP y en qué
# ventana de tiempo. get_remote_address identifica a quién limitar por
# su dirección IP (lo mismo que usaría cualquier firewall básico).
limiter = Limiter(key_func=get_remote_address)

# Comprobación ligera de que el email tiene forma de email — no es un
# validador RFC 5322 completo (eso exigiría una librería aparte para
# poca ganancia real). Solo pretende filtrar errores de escritura
# evidentes antes de guardar el lead.
REGEX_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """
    Código que se ejecuta una vez al arrancar el servidor (antes del
    'yield') y una vez al apagarlo (después). De momento solo lo
    usamos para asegurar que la tabla de la base de datos existe antes
    de que llegue la primera petición.
    """
    inicializar_db()
    yield


app = FastAPI(
    title="Pipo API",
    description="Analizador pasivo de webs para pymes",
    version="0.1.0",
    lifespan=ciclo_de_vida,
)

# Registramos el limitador en la app: el middleware intercepta cada
# petición para contar peticiones por IP, y el exception_handler
# decide qué responder cuando alguien se pasa del límite (error 429).
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS: por defecto, un navegador bloquea que una página en un origen
# (p.ej. tu landing servida en localhost:5500) llame a una API en otro
# origen (Railway) — es una protección estándar del navegador, no de
# nuestro servidor. Aquí solo dejamos pasar tu entorno de desarrollo
# local. Antes, con allow_origins=["*"], el backend ya desplegado en
# Railway habría aceptado peticiones desde CUALQUIER página web que
# alguien visitara — con la cuota diaria de Gemini tan ajustada (ver
# CLAUDE.md, P1), eso es un riesgo real, no solo teórico.
# Landing ya desplegada en Vercel (10 ago 2026) — dominio estable del
# proyecto, no las URLs de preview con hash que cambian en cada deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "https://piposcan.vercel.app",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
def raiz():
    """Endpoint de bienvenida, solo para comprobar que Pipo responde."""
    return {"mensaje": "Pipo está despierto y listo para revisar webs 🦉"}


@app.get("/health")
def salud():
    """
    Endpoint de salud. Es una convención estándar: cualquier sistema
    que despliegue o monitorice esta API (Railway, Render, un uptime
    checker...) puede pedir /health para saber si sigue viva.
    """
    return {"estado": "ok"}


@app.get("/check/ssl")
def check_ssl(dominio: str):
    """
    Endpoint de prueba para el check de SSL, aislado del resto.
    Ejemplo de uso: /check/ssl?dominio=example.com

    Es temporal: cuando montemos el endpoint /api/scan que orquesta
    todos los checks a la vez (Fase 2 del planning), este quedará
    solo como utilidad de depuración, o desaparecerá.
    """
    return comprobar_ssl(dominio)


@app.get("/check/headers")
async def check_headers(dominio: str):
    """
    Endpoint de prueba para el check de cabeceras de seguridad.
    Ejemplo de uso: /check/headers?dominio=example.com
    """
    return await comprobar_headers(dominio)


@app.get("/check/dns")
async def check_dns(dominio: str):
    """
    Endpoint de prueba para el check de DNS (SPF/DKIM/DMARC).
    Ejemplo de uso: /check/dns?dominio=example.com
    """
    return await comprobar_dns(dominio)


@app.get("/check/seo")
async def check_seo(dominio: str):
    """Endpoint de prueba del check de SEO técnico."""
    pagina = await obtener_pagina(dominio)
    return await comprobar_seo(pagina)


@app.get("/check/privacidad")
async def check_privacidad(dominio: str):
    """Endpoint de prueba del check de privacidad/RGPD."""
    pagina = await obtener_pagina(dominio)
    return comprobar_privacidad(pagina)


@app.get("/check/tecnologia")
async def check_tecnologia(dominio: str):
    """Endpoint de prueba del check de tecnología/CMS desactualizada."""
    pagina = await obtener_pagina(dominio)
    return await comprobar_tecnologia(pagina)


@app.get("/check/mixed-content")
async def check_mixed_content(dominio: str):
    """Endpoint de prueba del check de mixed content."""
    pagina = await obtener_pagina(dominio)
    return comprobar_mixed_content(pagina)


@app.get("/check/archivos-expuestos")
async def check_archivos_expuestos(dominio: str):
    """
    Endpoint de prueba del check de archivos expuestos (ámbar).
    A diferencia del resto, este SIEMPRE requiere haberlo llamado
    explícitamente aquí, o pasar consiento=true en /api/scan: nunca
    se ejecuta como parte de un escaneo por defecto.
    """
    return await comprobar_archivos_expuestos(dominio)


@app.get("/check/rendimiento")
async def check_rendimiento(dominio: str):
    """
    Endpoint de prueba del check de rendimiento (Google PageSpeed).
    Puede tardar 20-30 segundos: Google está auditando la web de
    verdad, no es un fallo si la respuesta no llega al instante.
    """
    return await comprobar_rendimiento(dominio)


@app.get("/api/scan")
@limiter.limit("5/minute")
async def escanear(
    request: Request,
    dominio: str,
    consiento: bool = False,
    incluir_rendimiento: bool = False,
):
    """
    El endpoint principal del producto: lanza todos los checks
    disponibles sobre un dominio, en paralelo, guarda el resultado en
    la base de datos y lo devuelve. Ejemplo de uso:
    /api/scan?dominio=example.com

    `consiento` representa el checkbox de consentimiento de
    titularidad del planning (punto 8): solo si viene en True se
    incluye el check de archivos expuestos (ámbar). Por defecto queda
    fuera, así el escaneo gratis nunca lo toca por accidente. Cuando
    exista el formulario real en el frontend, este parámetro vendrá
    marcado por ese checkbox, no a mano como ahora.

    Limitado a 5 peticiones por minuto y por IP (ver 'limiter' arriba):
    es la barrera contra que alguien use Pipo como arma de reconocimiento
    masivo contra terceros (punto 8 del planning, no negociable).
    El parámetro `request` lo exige slowapi para poder identificar de
    qué IP viene cada petición; no lo usamos nosotros directamente.

    `incluir_rendimiento` añade el check de PageSpeed, que puede
    añadir 20-30 segundos al escaneo (ver rendimiento_check.py). Por
    defecto queda fuera para que el escaneo rápido siga siendo rápido.

    Los /check/* individuales de arriba siguen ahí como utilidades de
    depuración por check; este es el que usará el frontend real.
    """
    resultado = await ejecutar_escaneo(
        dominio,
        incluir_archivos_expuestos=consiento,
        incluir_rendimiento=incluir_rendimiento,
    )
    id_escaneo = guardar_escaneo(
        dominio=dominio,
        estado_global=resultado["resumen"]["estado_global"],
        resultado=resultado,
    )
    return {"id": id_escaneo, **resultado}


@app.get("/api/scan/{id_escaneo}")
def obtener_scan(id_escaneo: int):
    """
    Recupera un escaneo ya guardado, por su id. Es lo que permitirá
    más adelante que un cliente vuelva a ver su informe con un enlace
    fijo (p.ej. pipo.es/informe/42), sin tener que relanzar el escaneo.
    """
    escaneo = obtener_escaneo(id_escaneo)
    if escaneo is None:
        raise HTTPException(status_code=404, detail="Ese escaneo no existe.")
    return escaneo


@app.post("/api/leads")
@limiter.limit("5/minute")
async def crear_lead(request: Request, email: str, dominio: str, id_escaneo: int):
    """
    Guarda un lead: alguien que ha dejado su email en el escaneo
    gratis para desbloquear el resto del informe (ver landing/index.html,
    la sección que queda difuminada hasta que se envía este formulario).

    `id_escaneo` tiene que ser el de un escaneo real — así no se puede
    usar este endpoint para acumular emails sueltos sin que estén
    atados a un escaneo de verdad. Es POST porque escribe datos nuevos,
    igual que /api/scan.

    Limitado a 5 peticiones por minuto y por IP, mismo motivo que el
    resto: evitar que alguien reviente el formulario con un script.
    """
    if obtener_escaneo(id_escaneo) is None:
        raise HTTPException(status_code=404, detail="Ese escaneo no existe.")

    email_limpio = email.strip().lower()
    if not REGEX_EMAIL.match(email_limpio):
        raise HTTPException(status_code=400, detail="Ese email no parece válido.")

    guardar_lead(email=email_limpio, dominio=dominio, id_escaneo=id_escaneo)
    return {"ok": True}


@app.post("/api/pedidos")
@limiter.limit("5/minute")
async def crear_pedido(request: Request, email: str, dominio: str, id_escaneo: int, telefono: str | None = None):
    """
    Pedido del nivel de pago "soluciones + PDF" (19€). Hoy el cobro es
    manual por Bizum (ver CLAUDE.md, P2) — este endpoint no cobra nada,
    solo guarda el pedido con una referencia para que Alberto pueda
    identificarlo cuando le llegue el Bizum y, más adelante, marcarlo
    como pagado (ese mecanismo todavía no existe, queda pendiente).

    A propósito, la web pública no enseña el número de Bizum ni la
    referencia directamente — le llegan al cliente por email, en
    privado, junto con un resumen de su caso (nota y checks a mejorar).
    Alberto recibe un segundo email avisando del pedido nuevo.

    `email_enviado` en la respuesta le dice al frontend si el email al
    cliente salió bien. Si falló (Gmail no configurado, corte de red...),
    el frontend usa eso como señal para enseñar el Bizum y la referencia
    directamente en la página — mejor un poco menos elegante que dejar
    a alguien que ya ha pedido esto sin ninguna forma de pagar.
    """
    escaneo = obtener_escaneo(id_escaneo)
    if escaneo is None:
        raise HTTPException(status_code=404, detail="Ese escaneo no existe.")

    email_limpio = email.strip().lower()
    if not REGEX_EMAIL.match(email_limpio):
        raise HTTPException(status_code=400, detail="Ese email no parece válido.")

    referencia = f"PIPO{id_escaneo}-{secrets.token_hex(2).upper()}"
    precio_arreglo_estimado = calcular_precio_arreglo(escaneo["resultado"]["checks"])
    guardar_pedido(
        referencia=referencia,
        email=email_limpio,
        dominio=dominio,
        id_escaneo=id_escaneo,
        precio=PRECIO_INFORME_COMPLETO,
        telefono=telefono,
    )

    email_enviado = False
    try:
        asunto_cliente, cuerpo_cliente = mensaje_pedido_cliente(
            dominio=dominio,
            checks=escaneo["resultado"]["checks"],
            precio=PRECIO_INFORME_COMPLETO,
            telefono_bizum=TELEFONO_BIZUM or "(número no configurado)",
            referencia=referencia,
            precio_arreglo_estimado=precio_arreglo_estimado,
        )
        await asyncio.to_thread(enviar_email, email_limpio, asunto_cliente, cuerpo_cliente)
        email_enviado = True
    except ErrorEmail:
        pass  # el frontend cae al plan B (enseñar el Bizum en la propia página)

    try:
        asunto_alberto, cuerpo_alberto = mensaje_pedido_alberto(
            dominio=dominio,
            email_cliente=email_limpio,
            telefono_cliente=telefono,
            referencia=referencia,
            precio=PRECIO_INFORME_COMPLETO,
            precio_arreglo_estimado=precio_arreglo_estimado,
        )
        await asyncio.to_thread(enviar_email, GMAIL_EMAIL, asunto_alberto, cuerpo_alberto)
    except ErrorEmail:
        pass  # aviso interno, best-effort: no debe romper el pedido del cliente

    return {
        "referencia": referencia,
        "precio": PRECIO_INFORME_COMPLETO,
        "telefono_bizum": TELEFONO_BIZUM,
        "precio_arreglo_estimado": precio_arreglo_estimado,
        "email_enviado": email_enviado,
    }


@app.get("/api/scan/{id_escaneo}/rendimiento")
@limiter.limit("5/minute")
async def scan_rendimiento(request: Request, id_escaneo: int):
    """
    El botón "Comprobar velocidad" del informe: audita con PageSpeed el
    dominio de un escaneo ya guardado. Antes llamaba directo a
    /check/rendimiento?dominio=... (una utilidad de depuración sin
    caché); ahora vive atado al id del escaneo para poder cachear el
    resultado (columna rendimiento_json) y no pedirle a Google la misma
    auditoría cada vez que alguien recarga la página del informe o
    pulsa el botón dos veces.

    Limitado a 5 peticiones por minuto y por IP, igual que los otros
    endpoints "caros" — no cuesta cuota de Gemini, pero sí es una
    petición real a la API de PageSpeed de Google.
    """
    escaneo = obtener_escaneo(id_escaneo)
    if escaneo is None:
        raise HTTPException(status_code=404, detail="Ese escaneo no existe.")

    if escaneo["rendimiento"] is not None:
        return escaneo["rendimiento"]

    resultado = await comprobar_rendimiento(escaneo["dominio"])

    # Solo cacheamos si hubo una auditoría real (datos no vacío). Si no
    # hay clave de PageSpeed configurada, o si Google ha fallado un
    # instante, comprobar_rendimiento devuelve un resultado sin
    # excepción pero con "datos" vacío — cachear eso sería dejar este
    # escaneo con velocidad "no disponible" para siempre, incluso si el
    # problema se arregla cinco minutos después.
    if resultado.get("datos"):
        guardar_rendimiento(id_escaneo, resultado)

    return resultado


@app.get("/api/informe/{id_escaneo}")
@limiter.limit("5/minute")
async def informe(request: Request, id_escaneo: int):
    """
    El informe interpretado: coge un escaneo ya guardado y le pide a la
    IA que traduzca cada hallazgo a lenguaje llano. La puntuación global
    la calcula el código (puntuacion.py), nunca la IA — ver el docstring
    de app/ia/interpretar.py para el porqué.

    Limitado a 5 peticiones por minuto y por IP, igual que /api/scan:
    cada llamada dispara una petición real a Gemini (dinero/cuota), así
    que el mismo límite que protege el escaneo protege también esto.
    El parámetro `request` lo exige slowapi para identificar la IP.

    Cachea el resultado en la base de datos (columna informe_json): si
    ya se pidió antes para este escaneo, se devuelve lo guardado sin
    volver a llamar a Gemini. Un escaneo, una vez creado, no cambia —
    así que no hay riesgo de servir algo desactualizado. Esto importa
    de verdad: el plan gratuito de Gemini tiene una cuota diaria muy
    ajustada (ver nota en app/ia/cliente.py), y sin caché, recargar la
    página del informe dos veces la agotaría el doble de rápido.
    """
    escaneo = obtener_escaneo(id_escaneo)
    if escaneo is None:
        raise HTTPException(status_code=404, detail="Ese escaneo no existe.")

    if escaneo["informe"] is not None:
        return escaneo["informe"]

    try:
        # interpretar_hallazgos hace una llamada de red bloqueante (el
        # SDK de Gemini no es async); la mandamos a un hilo aparte para
        # no congelar el servidor mientras espera respuesta.
        resultado = await asyncio.to_thread(interpretar_hallazgos, escaneo["resultado"])
    except ErrorIA as error:
        # 502: el fallo no es culpa de quien pregunta, es que el
        # proveedor de IA no ha podido responder.
        raise HTTPException(status_code=502, detail=str(error)) from error

    guardar_informe(id_escaneo, resultado)
    return resultado


@app.post("/api/informe/{id_escaneo}/soluciones")
@limiter.limit("5/minute")
async def informe_soluciones(request: Request, id_escaneo: int):
    """
    El "segundo botón": soluciones concretas para los checks que no
    están en verde, más la nota estimada tras aplicarlas. Es POST y no
    GET porque, a diferencia de /api/informe, dispara una llamada de
    pago a la IA cada vez — no queremos que un navegador o un bot la
    repita sin querer (los GET se pueden recargar, cachear, prefetchear).

    Limitado a 5 peticiones por minuto y por IP, mismo motivo que
    /api/informe: cada llamada cuesta dinero/cuota de IA de verdad.

    Cachea el resultado (columna soluciones_json) igual que /api/informe:
    si alguien pulsa el botón "soluciones" dos veces para el mismo
    escaneo, la segunda vez se sirve desde la base de datos, sin gastar
    cuota de Gemini otra vez.
    """
    escaneo = obtener_escaneo(id_escaneo)
    if escaneo is None:
        raise HTTPException(status_code=404, detail="Ese escaneo no existe.")

    if escaneo["soluciones"] is not None:
        return escaneo["soluciones"]

    try:
        resultado = await asyncio.to_thread(generar_soluciones, escaneo["resultado"])
    except ErrorIA as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    guardar_soluciones(id_escaneo, resultado)
    return resultado


@app.get("/api/informe/{id_escaneo}/pdf")
@limiter.limit("5/minute")
async def informe_pdf(request: Request, id_escaneo: int):
    """
    El informe en PDF descargable, con la marca de Pipo — el
    entregable del informe de pago (ver CLAUDE.md, P2). Reaprovecha
    el informe interpretado (lo genera si todavía no está en caché,
    igual que /api/informe) y las soluciones si ya se pidieron antes;
    no hace ninguna llamada a la IA que no fuera a hacer falta de todos
    modos, solo compone el PDF con lo que hay guardado.
    """
    escaneo = obtener_escaneo(id_escaneo)
    if escaneo is None:
        raise HTTPException(status_code=404, detail="Ese escaneo no existe.")

    if escaneo["informe"] is None:
        try:
            resultado = await asyncio.to_thread(interpretar_hallazgos, escaneo["resultado"])
        except ErrorIA as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        guardar_informe(id_escaneo, resultado)
        escaneo["informe"] = resultado

    # WeasyPrint es una librería pesada y el renderizado no es
    # instantáneo — se manda a un hilo aparte, igual que las llamadas
    # a la IA, para no bloquear el resto de peticiones al servidor.
    pdf_bytes = await asyncio.to_thread(generar_pdf_informe, escaneo)

    nombre_archivo = re.sub(r"[^a-zA-Z0-9.-]", "_", escaneo["dominio"])
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="informe-pipo-{nombre_archivo}.pdf"'},
    )
