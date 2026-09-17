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

import httpx
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.checks.accesibilidad_check import comprobar_accesibilidad
from app.checks.archivos_expuestos import comprobar_archivos_expuestos
from app.checks.area_privada_check import comprobar_area_privada
from app.checks.dns_check import comprobar_dns
from app.checks.dominio_check import comprobar_dominio
from app.checks.ecommerce_check import comprobar_ecommerce
from app.checks.experiencia_check import comprobar_experiencia
from app.checks.headers_check import comprobar_headers
from app.checks.mixed_content_check import comprobar_mixed_content
from app.checks.pagina import obtener_pagina
from app.checks.perfil_sitio import detectar_perfil
from app.checks.privacidad_check import comprobar_privacidad
from app.checks.rendimiento_check import comprobar_rendimiento
from app.checks.seo_check import comprobar_seo
from app.checks.ssl_check import comprobar_ssl
from app.checks.tecnologia_check import comprobar_tecnologia
from app.checks.whois_check import comprobar_whois
from app.config import CLAVE_ADMIN, GMAIL_EMAIL, MOSTRAR_DOCS
from app.database import (
    ESTADOS_SOLICITUD,
    escaneo_anterior,
    estadisticas_globales,
    guardar_escaneo,
    guardar_informe,
    guardar_lead,
    guardar_notas_solicitud,
    guardar_rendimiento,
    guardar_solicitud,
    guardar_soluciones,
    inicializar_db,
    listar_actividad_reciente,
    listar_leads,
    listar_solicitudes,
    marcar_cobro_solicitud,
    marcar_estado_solicitud,
    obtener_escaneo,
)
from app.ia.cliente import ErrorIA
from app.ia.interpretar import interpretar_hallazgos
from app.ia.soluciones import generar_soluciones
from app.notificaciones.enviar import ErrorEmail, enviar_email
from app.notificaciones.mensajes import mensaje_solicitud_alberto, mensaje_solicitud_cliente
from app.pdf.generar_pdf import generar_pdf_informe
from app.puntuacion import calcular_precio_arreglo, comparar_escaneos
from app.relevancia import relevancia_de
from app.scanner import ejecutar_escaneo
from app.seguridad import (
    DominioNoValido,
    comprobar_dominio_publico,
    ip_cliente,
    normalizar_dominio,
)

# El "limitador": decide cuántas peticiones permite por IP y en qué
# ventana de tiempo. La clave la calcula ip_cliente (ver app/seguridad.py),
# que lee X-Forwarded-For: con el get_remote_address que traía slowapi,
# detrás del proxy de Railway todas las peticiones caían en cubos
# distintos y el límite no se aplicaba NUNCA en producción.
limiter = Limiter(key_func=ip_cliente)

# Comprobación ligera de que el email tiene forma de email — no es un
# validador RFC 5322 completo (eso exigiría una librería aparte para
# poca ganancia real). Solo pretende filtrar errores de escritura
# evidentes antes de guardar el lead.
REGEX_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _verificar_token(escaneo: dict, token: str | None) -> None:
    """
    Comprueba que quien pide un escaneo tiene su enlace, no solo su
    número. Los ids son correlativos (1, 2, 3...), así que sin esto
    cualquiera puede recorrerlos y leer todos los escaneos hechos con
    Pipo, con dominios y resultados incluidos — comprobado en producción
    el 13 ago 2026.

    No es un sistema de cuentas: el enlace del informe sigue siendo
    compartible tal cual, simplemente deja de ser adivinable. Mismo
    compare_digest que la clave de admin, por el mismo motivo.
    """
    esperado = escaneo.get("token")
    if not esperado or not token or not secrets.compare_digest(token, esperado):
        raise HTTPException(status_code=403, detail="Este enlace no es válido o está incompleto.")


def _normalizar_o_400(dominio: str) -> str:
    """Deja el dominio limpio, o devuelve un 400 con un mensaje legible."""
    try:
        return normalizar_dominio(dominio)
    except DominioNoValido as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def _verificar_clave_admin(clave: str | None) -> None:
    """
    Protege el panel de pedidos (landing/pedidos.html?clave=...). No es
    un sistema de usuarios de verdad — es un enlace secreto que solo
    tiene Alberto, suficiente para un panel de uso personal. Se usa
    secrets.compare_digest en vez de "==" para que comparar la clave no
    filtre por temporización cuánto se parece un intento a la correcta.
    Si CLAVE_ADMIN no está configurada, se deniega siempre (nunca un
    panel abierto por descuido de configuración).
    """
    if not CLAVE_ADMIN or not clave or not secrets.compare_digest(clave, CLAVE_ADMIN):
        raise HTTPException(status_code=403, detail="Clave incorrecta.")


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
    # /docs y /redoc solo si PIPO_DOCS=1 (ver config.py): en producción
    # publicaban el mapa entero de la API, endpoints de admin incluidos.
    docs_url="/docs" if MOSTRAR_DOCS else None,
    redoc_url="/redoc" if MOSTRAR_DOCS else None,
    openapi_url="/openapi.json" if MOSTRAR_DOCS else None,
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
        # Dominio propio, desde el 14 ago 2026. Van los dos: el host que
        # Vercel sirve de verdad es www y el apex redirige ahí, pero el
        # navegador comprueba CORS contra el origen desde el que se cargó
        # la página, así que los dos tienen que estar.
        "https://pipoweb.com",
        "https://www.pipoweb.com",
        # El dominio viejo se queda a propósito mientras haya enlaces de
        # informe compartidos apuntando ahí. Si se quita antes de tiempo,
        # esas páginas dejan de poder hablar con la API y parecen rotas
        # sin dar ningún error visible.
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


async def _solo_admin(clave: str = "") -> None:
    """
    Dependencia que exige la clave de administración. Se aplica a todo
    el router de depuración de abajo: FastAPI la ejecuta antes que
    cualquiera de esas funciones, así que no hay forma de añadir un
    endpoint nuevo ahí y olvidarse de protegerlo.
    """
    _verificar_clave_admin(clave)


# Los /check/* son utilidades de depuración: ejecutan UN check suelto
# sobre un dominio. Hasta el 13 ago 2026 estaban abiertos a internet,
# sin rate limit y sin validar el destino — comprobado con curl real
# contra producción: 8 llamadas seguidas, las 8 servidas, y aceptaban
# hasta direcciones internas del hosting. Es decir, cualquiera podía
# usar el servidor de Pipo como escáner de webs ajenas, con la IP de
# Pipo apareciendo en los registros del sitio escaneado. Todo el
# consentimiento de titularidad de la landing rodeaba la puerta
# principal mientras esta puerta lateral estaba abierta.
#
# Ahora piden ?clave= (la misma del panel de pedidos) y el dominio pasa
# por la misma validación que el escaneo de verdad.
depuracion = APIRouter(prefix="/check", tags=["depuración"], dependencies=[Depends(_solo_admin)])


async def _dominio_de_depuracion(dominio: str) -> str:
    """Valida el dominio igual que /api/scan, también en depuración."""
    limpio = _normalizar_o_400(dominio)
    try:
        await comprobar_dominio_publico(limpio)
    except DominioNoValido as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return limpio


@depuracion.get("/ssl")
async def check_ssl(dominio: str):
    """Check de SSL aislado. Ejemplo: /check/ssl?dominio=example.com&clave=..."""
    return await asyncio.to_thread(comprobar_ssl, await _dominio_de_depuracion(dominio))


@depuracion.get("/headers")
async def check_headers(dominio: str):
    """Check de cabeceras de seguridad, aislado."""
    return await comprobar_headers(await _dominio_de_depuracion(dominio))


@depuracion.get("/dns")
async def check_dns(dominio: str):
    """Check de DNS (SPF/DKIM/DMARC), aislado."""
    return await comprobar_dns(await _dominio_de_depuracion(dominio))


@depuracion.get("/seo")
async def check_seo(dominio: str):
    """Check de SEO técnico, aislado."""
    pagina = await obtener_pagina(await _dominio_de_depuracion(dominio))
    return await comprobar_seo(pagina)


@depuracion.get("/privacidad")
async def check_privacidad(dominio: str):
    """Check de privacidad/RGPD, aislado."""
    pagina = await obtener_pagina(await _dominio_de_depuracion(dominio))
    return comprobar_privacidad(pagina)


@depuracion.get("/tecnologia")
async def check_tecnologia(dominio: str):
    """Check de tecnología/CMS desactualizada, aislado."""
    pagina = await obtener_pagina(await _dominio_de_depuracion(dominio))
    return await comprobar_tecnologia(pagina)


@depuracion.get("/mixed-content")
async def check_mixed_content(dominio: str):
    """Check de mixed content, aislado."""
    pagina = await obtener_pagina(await _dominio_de_depuracion(dominio))
    return comprobar_mixed_content(pagina)


@depuracion.get("/dominio")
async def check_dominio(dominio: str):
    """Check de dominio (CAA/DNSSEC), aislado."""
    return await comprobar_dominio(await _dominio_de_depuracion(dominio))


@depuracion.get("/whois")
async def check_whois(dominio: str):
    """Check de WHOIS (caducidad del dominio), aislado."""
    return await asyncio.to_thread(comprobar_whois, await _dominio_de_depuracion(dominio))


@depuracion.get("/accesibilidad")
async def check_accesibilidad(dominio: str):
    """Check de accesibilidad básica, aislado."""
    pagina = await obtener_pagina(await _dominio_de_depuracion(dominio))
    return comprobar_accesibilidad(pagina)


@depuracion.get("/experiencia")
async def check_experiencia(dominio: str):
    """Check de experiencia de cliente (móvil, contacto, formularios), aislado."""
    limpio = await _dominio_de_depuracion(dominio)
    pagina = await obtener_pagina(limpio)
    return await comprobar_experiencia(pagina, limpio)


@depuracion.get("/perfil")
async def check_perfil(dominio: str):
    """Detección de perfil de sitio (tipo, CMS, señales), aislado. No es un check con semáforo."""
    pagina = await obtener_pagina(await _dominio_de_depuracion(dominio))
    return await detectar_perfil(pagina)


@depuracion.get("/ecommerce")
async def check_ecommerce(dominio: str):
    """Check condicional de tienda online, aislado. Normalmente solo se lanza si tiene_checkout=True."""
    pagina = await obtener_pagina(await _dominio_de_depuracion(dominio))
    return await asyncio.to_thread(comprobar_ecommerce, pagina)


@depuracion.get("/area-privada")
async def check_area_privada(dominio: str):
    """Check condicional de exposición del acceso privado, aislado. Normalmente solo se lanza si tiene_login=True."""
    pagina = await obtener_pagina(await _dominio_de_depuracion(dominio))
    return await asyncio.to_thread(comprobar_area_privada, pagina)


# TEMPORAL — diagnóstico del 403 de toldosonline.es contra Railway (17 sep
# 2026). Mismo patrón que /api/diagnostico-email de agosto: exponer el dato
# real en vez de adivinar, y borrar este endpoint en el commit siguiente.
# Compara qué código de estado da un dominio con las cabeceras actuales de
# Pipo (solo User-Agent) frente a cabeceras completas de navegador, para
# saber si el bloqueo es por huella HTTP/cabeceras o por la IP de Railway
# (en cuyo caso ningún cambio de cabeceras lo arregla).
@depuracion.get("/diagnostico-bloqueo")
async def diagnostico_bloqueo(dominio: str):
    limpio = await _dominio_de_depuracion(dominio)
    resultados = {}
    for etiqueta, headers in (
        ("solo_user_agent", {"User-Agent": "Mozilla/5.0 (compatible; PipoBot/1.0; +https://pipoweb.com)"}),
        (
            "cabeceras_navegador",
            {
                "User-Agent": "Mozilla/5.0 (compatible; PipoBot/1.0; +https://pipoweb.com)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
            },
        ),
    ):
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=8.0, headers=headers) as cliente:
                respuesta = await cliente.get(f"https://{limpio}")
            resultados[etiqueta] = {"status": respuesta.status_code, "bytes": len(respuesta.content)}
        except httpx.RequestError as error:
            resultados[etiqueta] = {"error": str(error)}
    return resultados


@depuracion.get("/archivos-expuestos")
async def check_archivos_expuestos(dominio: str):
    """
    Check de archivos expuestos (ámbar). A diferencia del resto, este
    SIEMPRE requiere haberlo llamado explícitamente aquí, o pasar
    consiento=true en /api/scan: nunca se ejecuta por defecto.
    """
    return await comprobar_archivos_expuestos(await _dominio_de_depuracion(dominio))


@depuracion.get("/rendimiento")
async def check_rendimiento(dominio: str):
    """
    Check de rendimiento (Google PageSpeed). Puede tardar 20-30
    segundos: Google está auditando la web de verdad.
    """
    return await comprobar_rendimiento(await _dominio_de_depuracion(dominio))


app.include_router(depuracion)


@app.get("/api/scan")
@limiter.limit("5/minute")
async def escanear(
    request: Request,
    dominio: str,
    declara_titularidad: bool = False,
    consiento: bool = False,
    incluir_rendimiento: bool = False,
):
    """
    El endpoint principal del producto: lanza todos los checks
    disponibles sobre un dominio, en paralelo, guarda el resultado en
    la base de datos y lo devuelve. Ejemplo de uso:
    /api/scan?dominio=example.com&declara_titularidad=true

    `declara_titularidad` es el checkbox de la landing ("declaro ser el
    titular de este dominio o tener autorización"). Antes se quedaba en
    el navegador y no llegaba aquí, mientras la FAQ prometía que "queda
    registrado". Ahora es obligatorio y se guarda junto al escaneo con
    la fecha y la IP de quien lo declaró, que es lo que convierte esa
    frase en algo demostrable. No pide ninguna prueba técnica de la
    propiedad del dominio (eso sería verificar un registro DNS o un
    archivo subido al servidor) — es una declaración, igual que antes,
    solo que ahora queda anotada.

    `consiento` es otra cosa distinta: activa el único check ámbar
    (archivos expuestos). Por defecto queda fuera, así el escaneo
    gratis nunca lo toca por accidente.

    Limitado a 5 peticiones por minuto y por IP (ver 'limiter' arriba):
    es la barrera contra que alguien use Pipo como arma de reconocimiento
    masivo contra terceros (punto 8 del planning, no negociable).
    El parámetro `request` lo exige slowapi para poder identificar de
    qué IP viene cada petición; aquí además la usamos para el registro
    de la declaración.

    `incluir_rendimiento` añade el check de PageSpeed, que puede
    añadir 20-30 segundos al escaneo (ver rendimiento_check.py). Por
    defecto queda fuera para que el escaneo rápido siga siendo rápido.
    """
    if not declara_titularidad:
        raise HTTPException(
            status_code=400,
            detail="Hay que declarar que la web es tuya o que tienes autorización para analizarla.",
        )

    limpio = _normalizar_o_400(dominio)
    try:
        await comprobar_dominio_publico(limpio)
    except DominioNoValido as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    resultado = await ejecutar_escaneo(
        limpio,
        incluir_archivos_expuestos=consiento,
        incluir_rendimiento=incluir_rendimiento,
    )

    # "¿Ha mejorado desde la última vez?" — se calcula contra el escaneo
    # anterior del mismo dominio, si lo hay. Es la base del futuro nivel
    # de vigilancia, pero sin necesitar todavía ninguna tarea programada:
    # aparece solo cuando alguien vuelve a analizar la misma web.
    anterior = escaneo_anterior(limpio)
    resultado["comparacion"] = comparar_escaneos(anterior, resultado) if anterior else None

    id_escaneo, token = guardar_escaneo(
        dominio=limpio,
        estado_global=resultado["resumen"]["estado_global"],
        resultado=resultado,
        ip_solicitante=ip_cliente(request),
    )
    return {"id": id_escaneo, "token": token, **resultado}


@app.get("/api/scan/{id_escaneo}")
@limiter.limit("30/minute")
async def obtener_scan(request: Request, id_escaneo: int, t: str = ""):
    """
    Recupera un escaneo ya guardado, por su id y su token (el `t` del
    enlace del informe). Sin el token no se devuelve nada: los ids son
    correlativos y sin él bastaba con contar del 1 en adelante para
    leer todos los escaneos hechos con Pipo.
    """
    escaneo = obtener_escaneo(id_escaneo)
    if escaneo is None:
        raise HTTPException(status_code=404, detail="Ese escaneo no existe.")
    _verificar_token(escaneo, t)
    return escaneo


@app.get("/api/estadisticas")
@limiter.limit("30/minute")
async def estadisticas(request: Request):
    """
    Números agregados de todo lo que Pipo ha revisado: cuántas webs
    distintas, su nota media y qué porcentaje tenía algún fallo grave.

    Sirve para dos cosas, las dos honestas: enseñar en la landing un
    dato propio y verificable en vez de una cifra inventada, y poder
    decirle a alguien "tu web está por debajo de la media de las que
    revisamos", que es lo que convierte un número suelto en una
    posición. Cuenta cada dominio una sola vez (su escaneo más
    reciente), para que analizar diez veces la misma web no deforme la
    media.
    """
    return estadisticas_globales()


@app.post("/api/leads")
@limiter.limit("5/minute")
async def crear_lead(
    request: Request, email: str, dominio: str, id_escaneo: int, t: str = "", marketing: bool = False
):
    """
    Guarda un lead: alguien que ha dejado su email en el informe para
    que Pipo pueda escribirle. Desde el 13 ago 2026 este es el único
    punto de captura de email del informe gratis (el informe en sí ya
    no se tapa, ver CLAUDE.md) — su función es explícitamente reunir
    contactos para poder recordarle a un negocio que vuelva, no
    desbloquear nada.

    `marketing` es el checkbox "quiero recibir consejos y ofertas..."
    del formulario — se guarda tal cual, es la base legal (RGPD art.
    6.1.a) para poder mandar campañas más adelante. Sin él a True, ese
    email solo debería usarse para lo que se pidió en el momento.

    `id_escaneo` tiene que ser el de un escaneo real, y `t` su token —
    así no se puede usar este endpoint para acumular emails sueltos sin
    que estén atados a un escaneo de verdad. Es POST porque escribe
    datos nuevos, igual que /api/scan.

    Limitado a 5 peticiones por minuto y por IP, mismo motivo que el
    resto: evitar que alguien reviente el formulario con un script.
    """
    escaneo = obtener_escaneo(id_escaneo)
    if escaneo is None:
        raise HTTPException(status_code=404, detail="Ese escaneo no existe.")
    _verificar_token(escaneo, t)

    email_limpio = email.strip().lower()
    if not REGEX_EMAIL.match(email_limpio):
        raise HTTPException(status_code=400, detail="Ese email no parece válido.")

    # El dominio se coge del escaneo, no del parámetro: ya está validado y
    # normalizado, y así abrir informe.html sin "&dominio=" no deja un lead
    # sin dominio en el panel. El parámetro se sigue aceptando para no
    # romper los enlaces que ya circulan, pero no se usa.
    guardar_lead(
        email=email_limpio,
        dominio=escaneo["dominio"],
        id_escaneo=id_escaneo,
        consiente_marketing=marketing,
    )
    return {"ok": True}


@app.post("/api/solicitudes")
@limiter.limit("5/minute")
async def crear_solicitud(
    request: Request,
    email: str,
    dominio: str,
    id_escaneo: int,
    t: str = "",
    telefono: str | None = None,
    mensaje: str | None = None,
):
    """
    Solicitud de "arregladlo vosotros": el producto de verdad (ver
    CLAUDE.md, P2). Sustituye al antiguo pedido de 19€ por el informe
    con soluciones.

    Por qué cambió: el informe y el PDF cuestan céntimos de IA y no
    requieren tiempo de nadie, así que cobrarlos convertía a Pipo en un
    negocio de muchos clientes a poco dinero — justo el que no se puede
    servir cobrando por Bizum a mano. Lo que sí cuesta tiempo, y es lo
    que el dueño del negocio quiere en realidad, es que el problema
    desaparezca. Eso es lo que se vende ahora.

    Aquí no se cobra nada ni se pide el pago por adelantado: es un
    servicio, así que primero se habla y se cierra presupuesto. El
    cliente recibe un email confirmando que la solicitud ha llegado y
    con su diagnóstico; Alberto recibe otro con el caso para
    responderle.
    """
    escaneo = obtener_escaneo(id_escaneo)
    if escaneo is None:
        raise HTTPException(status_code=404, detail="Ese escaneo no existe.")
    _verificar_token(escaneo, t)

    email_limpio = email.strip().lower()
    if not REGEX_EMAIL.match(email_limpio):
        raise HTTPException(status_code=400, detail="Ese email no parece válido.")

    referencia = f"PIPO{id_escaneo}-{secrets.token_hex(2).upper()}"
    precio_estimado = calcular_precio_arreglo(escaneo["resultado"]["checks"])
    guardar_solicitud(
        referencia=referencia,
        email=email_limpio,
        dominio=escaneo["dominio"],
        id_escaneo=id_escaneo,
        precio_estimado=precio_estimado,
        telefono=telefono,
        mensaje=mensaje,
    )

    email_enviado = False
    try:
        asunto_cliente, cuerpo_cliente, html_cliente = mensaje_solicitud_cliente(
            dominio=escaneo["dominio"],
            checks=escaneo["resultado"]["checks"],
            referencia=referencia,
            precio_estimado=precio_estimado,
        )
        await asyncio.to_thread(enviar_email, email_limpio, asunto_cliente, cuerpo_cliente, html_cliente)
        email_enviado = True
    except ErrorEmail:
        # El frontend ya enseña en pantalla la confirmación y el email de
        # contacto, así que aunque falle el envío nadie se queda sin saber
        # qué pasa después. La solicitud ya está guardada.
        pass

    try:
        asunto_alberto, cuerpo_alberto, html_alberto = mensaje_solicitud_alberto(
            dominio=escaneo["dominio"],
            email_cliente=email_limpio,
            telefono_cliente=telefono,
            mensaje_cliente=mensaje,
            referencia=referencia,
            precio_estimado=precio_estimado,
            id_escaneo=id_escaneo,
        )
        await asyncio.to_thread(enviar_email, GMAIL_EMAIL, asunto_alberto, cuerpo_alberto, html_alberto)
    except ErrorEmail:
        pass  # aviso interno, best-effort: no debe romper la solicitud del cliente

    return {
        "referencia": referencia,
        "precio_estimado": precio_estimado,
        "email_enviado": email_enviado,
    }


@app.get("/api/solicitudes")
@limiter.limit("20/minute")
async def ver_solicitudes(request: Request, clave: str):
    """
    Lista todas las solicitudes de arreglo, para el panel privado de
    Alberto (landing/panel.html). Límite más alto que el resto (20/min
    en vez de 5/min) porque es él recargando su propio panel, no tráfico
    público — y cada llamada aquí no cuesta cuota de IA ni de PageSpeed.
    """
    _verificar_clave_admin(clave)
    return listar_solicitudes()


@app.post("/api/solicitudes/{id_solicitud}/estado")
@limiter.limit("20/minute")
async def cambiar_estado_solicitud(request: Request, id_solicitud: int, clave: str, estado: str):
    """
    Mueve una solicitud por el pipeline del panel:
    nuevo → contactado → presupuesto_enviado → pagado → arreglado →
    cerrado. No hay automatismo detrás; es una nota para Alberto mismo,
    para no perder el hilo de a quién ha contestado y en qué punto está.
    """
    _verificar_clave_admin(clave)
    if estado not in ESTADOS_SOLICITUD:
        raise HTTPException(status_code=400, detail=f"Estado no válido. Usa uno de: {', '.join(ESTADOS_SOLICITUD)}.")
    if not marcar_estado_solicitud(id_solicitud, estado):
        raise HTTPException(status_code=404, detail="Esa solicitud no existe.")
    return {"ok": True, "estado": estado}


@app.post("/api/solicitudes/{id_solicitud}/notas")
@limiter.limit("20/minute")
async def actualizar_notas_solicitud(request: Request, id_solicitud: int, clave: str, notas: str = ""):
    """
    Guarda las notas libres de una solicitud (qué le dijo Alberto, qué
    pidió el cliente) — el cuaderno del caso dentro del panel.
    """
    _verificar_clave_admin(clave)
    if not guardar_notas_solicitud(id_solicitud, notas):
        raise HTTPException(status_code=404, detail="Esa solicitud no existe.")
    return {"ok": True}


@app.post("/api/solicitudes/{id_solicitud}/cobro")
@limiter.limit("20/minute")
async def registrar_cobro_solicitud(request: Request, id_solicitud: int, clave: str, importe: int):
    """
    Registra cuánto se ha cobrado por una solicitud, con la fecha de
    hoy. Es manual a propósito — Pipo no cobra nada automáticamente,
    esto es solo el apunte de que el dinero ya ha llegado.
    """
    _verificar_clave_admin(clave)
    if not marcar_cobro_solicitud(id_solicitud, importe):
        raise HTTPException(status_code=404, detail="Esa solicitud no existe.")
    return {"ok": True, "importe_cobrado": importe}


@app.get("/api/leads")
@limiter.limit("20/minute")
async def ver_leads(request: Request, clave: str):
    """
    Todos los emails captados por el formulario de avisos de
    informe.html — gente que ha dejado su email sin (todavía) pedir un
    arreglo. Es la mitad "recordatorio" del panel: a quién se le puede
    escribir más adelante con consejos u ofertas (solo a quien marcó
    consiente_marketing).
    """
    _verificar_clave_admin(clave)
    return listar_leads()


@app.get("/api/actividad")
@limiter.limit("20/minute")
async def ver_actividad(request: Request, clave: str):
    """
    Los escaneos más recientes, con el email captado para cada uno si
    lo hay — "quién ha entrado a la web", tal cual lo pidió Alberto para
    el panel. No todo el que escanea deja un lead, y aun así interesa
    ver que alguien analizó su dominio y qué nota sacó.
    """
    _verificar_clave_admin(clave)
    return listar_actividad_reciente()


@app.get("/api/scan/{id_escaneo}/rendimiento")
@limiter.limit("5/minute")
async def scan_rendimiento(request: Request, id_escaneo: int, t: str = ""):
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
    _verificar_token(escaneo, t)

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
async def informe(request: Request, id_escaneo: int, t: str = ""):
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
    # Sin token no se genera: este endpoint llama a la IA de verdad si
    # el informe no estaba en caché, así que un id adivinable era además
    # una forma de que un desconocido gastara nuestro saldo de Anthropic.
    _verificar_token(escaneo, t)

    if escaneo["informe"] is None:
        try:
            # interpretar_hallazgos hace una llamada de red bloqueante (el
            # SDK de la IA no es async); la mandamos a un hilo aparte para
            # no congelar el servidor mientras espera respuesta.
            resultado = await asyncio.to_thread(interpretar_hallazgos, escaneo["resultado"])
        except ErrorIA as error:
            # 502: el fallo no es culpa de quien pregunta, es que el
            # proveedor de IA no ha podido responder.
            raise HTTPException(status_code=502, detail=str(error)) from error
        guardar_informe(id_escaneo, resultado)
        escaneo["informe"] = resultado

    perfil_sitio = escaneo["resultado"].get("perfil_sitio")

    # Relevancia por tipo de sitio (ver app/relevancia.py): "esto te
    # importa más/menos por ser el tipo de web que eres". Fórmula fija,
    # igual que la prioridad — nunca la decide la IA. Se calcula al
    # vuelo con el perfil de este escaneo, así que un informe cacheado
    # de antes de que existiera esta tabla también la lleva sin volver
    # a llamar a la IA.
    hallazgos_con_relevancia = [
        {**hallazgo, "relevancia": relevancia_de(hallazgo["check"], perfil_sitio)}
        for hallazgo in escaneo["informe"].get("hallazgos", [])
    ]

    # El desglose por familias y la comparación con el escaneo anterior
    # se añaden al vuelo, no se guardan dentro del informe: son datos del
    # escaneo, no de la interpretación de la IA. Así los informes que ya
    # estaban cacheados también los llevan, sin volver a llamar a la IA.
    return {
        **escaneo["informe"],
        "hallazgos": hallazgos_con_relevancia,
        "resumen": escaneo["resultado"].get("resumen"),
        "comparacion": escaneo["resultado"].get("comparacion"),
        # Qué tipo de sitio es, con qué CMS está hecho (ver
        # perfil_sitio.py). Metadata de detección, no interpretación de
        # la IA, así que viaja igual que resumen/comparacion: se añade
        # al vuelo desde el escaneo guardado, no desde la caché de IA.
        "perfil_sitio": perfil_sitio,
        "fecha": escaneo["fecha"],
        # Precio orientativo del arreglo, para poder enseñarlo antes de
        # que nadie rellene ningún formulario. Fórmula fija, nunca IA.
        "precio_arreglo_estimado": calcular_precio_arreglo(escaneo["resultado"]["checks"]),
    }


@app.post("/api/informe/{id_escaneo}/soluciones")
@limiter.limit("20/minute")
async def informe_soluciones(request: Request, id_escaneo: int, clave: str = ""):
    """
    Las soluciones paso a paso: qué hay que tocar exactamente para
    arreglar cada punto que no está en verde.

    HERRAMIENTA INTERNA, no producto. Solo responde con la clave de
    administración, y no hay ningún botón en la web que lleve aquí.

    El porqué es de negocio, no técnico: el diagnóstico se regala (crea
    la conversación), pero el "cómo se arregla" es exactamente lo que se
    vende. Si se entrega junto al informe, el cliente se lo reenvía a su
    informático de siempre y la venta se pierde ahí — que era el riesgo
    que teníamos con el nivel de 19€. Ahora esto es lo que abre Alberto
    en el panel para hacer el trabajo que le han encargado.

    Es POST y no GET porque dispara una llamada de pago a la IA cada
    vez, y los GET se recargan, cachean y prefetchean solos. Se cachea
    en soluciones_json: abrirlo dos veces no cuesta el doble.
    """
    _verificar_clave_admin(clave)

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
async def informe_pdf(request: Request, id_escaneo: int, t: str = "", marca: str | None = None):
    """
    El informe en PDF con la marca de Pipo. Desde el 13 ago 2026 es
    GRATIS (solo pide el token del enlace): cuesta céntimos generarlo y
    es la mejor tarjeta de visita que tiene el proyecto — algo que el
    dueño del negocio se guarda, reenvía a su socio o le enseña a su
    informático, con el nombre de Pipo en cada página.

    Lo que NO lleva es la sección de soluciones paso a paso: eso es lo
    que se vende (ver /soluciones). El PDF dice qué falla y por qué
    importa; no dice cómo se arregla.

    `marca` permite poner "informe elaborado para —tu agencia—" en la
    portada, para cuando un diseñador o una agencia quiera entregárselo
    a sus propios clientes.
    """
    escaneo = obtener_escaneo(id_escaneo)
    if escaneo is None:
        raise HTTPException(status_code=404, detail="Ese escaneo no existe.")
    _verificar_token(escaneo, t)

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
    pdf_bytes = await asyncio.to_thread(generar_pdf_informe, escaneo, marca)

    nombre_archivo = re.sub(r"[^a-zA-Z0-9.-]", "_", escaneo["dominio"])
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="informe-pipo-{nombre_archivo}.pdf"'},
    )
