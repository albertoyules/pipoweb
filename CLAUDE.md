# Pipo — contexto del proyecto para retomar el trabajo

Este archivo es la memoria del proyecto: qué es, qué hay construido, qué falta y en qué orden. Léelo entero antes de tocar código. El documento de visión de producto completo (modelo de negocio, marca, roadmap por fases) está en **[PIPO_PLANNING.md](PIPO_PLANNING.md)** — este `CLAUDE.md` es el estado técnico real, más al día que el planning en cuanto a "qué existe ya".

## Quién es el usuario de este proyecto

Alberto, en Málaga. No es programador profesional — está aprendiendo mientras construye. **Prefiere ir despacio, en trozos pequeños, entendiendo el qué y el porqué de cada pieza antes de seguir**, no que le sueltes código sin contexto. Es un proyecto personal/side-project, compaginado con otras cosas (cold-visits a negocios, otro proyecto de reseñas QR). Le importa mucho no cruzar líneas legales sin darse cuenta — explícale siempre si un check es pasivo (verde, seguro) o zona gris (ámbar, con condiciones), nunca actives nada rojo.

## Qué es Pipo, en una frase

Un analizador **100% pasivo** de webs para pymes: le das un dominio, revisa seguridad/RGPD/SEO/velocidad sin tocar el servidor del cliente (solo mira lo que cualquier visitante o Google ya ve), y genera un informe en lenguaje llano con IA, con semáforo verde/ámbar/rojo. Personaje: Pipo, un búho con lupa.

**Regla legal que gobierna todo el diseño técnico:** solo se piden datos que el servidor publica a cualquiera sin credenciales (art. 197 bis CP — sin vulnerar medidas de seguridad, no hay delito). El único check que no es 100% pasivo (`archivos_expuestos.py`) está marcado ámbar y apagado por defecto, solo se activa con consentimiento explícito.

---

## Cómo arrancar el proyecto (para retomar sesión)

**El backend ya está desplegado de verdad, en producción**: `https://pipo-analiza-production.up.railway.app` (Railway, desde el 10 ago 2026). La landing (`API_BASE` en `index.html` e `informe.html`) apunta ahí por defecto — **no hace falta arrancar el backend en local para probar la landing**, ya habla con el de Railway.

```bash
# Landing (sirve contra el backend de Railway sin nada más que arrancar)
cd "PIPO ANALIZA/landing"
python3 -m http.server 5500
```

Solo hace falta levantar el backend en local si vas a tocar código del backend y quieres probarlo antes de subirlo:

```bash
cd "PIPO ANALIZA/backend"
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Si haces esto, cambia temporalmente `API_BASE` en `index.html`/`informe.html` de vuelta a `http://127.0.0.1:8000` (está comentado en el propio código dónde) — y recuerda devolverlo a la URL de Railway antes de hacer commit.

**Desplegar cambios del backend:** Railway está conectado al repo de GitHub (`albertoyules/pipo-analiza`, privado) y redespliega solo con cada `git push` a `main`. No hace falta tocar nada en Railway para desplegar — solo `git push`.

La API de producción tiene `/docs` igual que la local — nunca se le enseña esto a un cliente.

**Cuidado con procesos zombis:** si el puerto 8000 responde raro (p.ej. 404 en `/health`), es casi seguro un proceso de una sesión anterior que quedó colgado. `lsof -i :8000`, mata el PID, y arranca uvicorn limpio.

---

## Estructura del repo

```
PIPO ANALIZA/
├── PIPO_PLANNING.md          ← visión de producto completa (marca, negocio, roadmap por fases)
├── CLAUDE.md                  ← este archivo
├── landing/
│   ├── index.html              → landing pública, con el escaneo gratis en vivo conectado al backend
│   ├── informe.html             → informe completo: hallazgos interpretados por IA + botones de velocidad y soluciones
│   ├── aviso-legal.html          → identificación del titular (Alberto Yules), NIF/domicilio pendientes hasta que se formalice como autónomo
│   ├── privacidad.html            → qué datos trata Pipo, con quién se comparten (Gemini, PageSpeed), derechos RGPD
│   ├── cookies.html                → hoy Pipo no instala cookies propias, solo declara Google Fonts
│   └── 404.html                     → página de error con Pipo desorientado (animación); ojo: solo se sirve sola en hostings que la detecten (Netlify/Vercel), NO con `python3 -m http.server` en local — pendiente activarla al desplegar (ver P1)
└── backend/
    ├── .env                     → claves de API (NUNCA se sube a git, ver .gitignore)
    ├── requirements.txt
    ├── railpack.json              → librerías de sistema (Pango/Cairo) que necesita WeasyPrint en Railway
    ├── pipo.db                   → SQLite con historial de escaneos (tampoco se sube a git)
    └── app/
        ├── main.py                → todos los endpoints FastAPI
        ├── seguridad.py            → IP real del visitante (rate limit) + validación del dominio de entrada
        ├── config.py               → lee .env (claves de Anthropic, Gemini y PageSpeed)
        ├── database.py              → guardar/leer escaneos en SQLite
        ├── scanner.py                → orquestador: lanza todos los checks en paralelo
        ├── puntuacion.py              → nota 0-100, calculada por FÓRMULA FIJA, nunca por la IA
        ├── checks/
        │   ├── pagina.py                → descarga compartida de la home (evita pedir la misma página 3 veces)
        │   ├── ssl_check.py              → verde (certificado + redirección http→https real)
        │   ├── headers_check.py           → verde (4 cabeceras "core" + aviso de cookies/Referrer-Policy/Permissions-Policy/fuga de versión)
        │   ├── dns_check.py                → verde (SPF/DKIM/DMARC)
        │   ├── dominio_check.py             → verde (CAA + DNSSEC)
        │   ├── whois_check.py                → verde (caducidad del dominio; "no disponible" nunca cuenta como fallo)
        │   ├── seo_check.py                   → verde
        │   ├── privacidad_check.py             → verde (aviso legal/cookies/trackers)
        │   ├── mixed_content_check.py           → verde (recursos http:// + Subresource Integrity en scripts externos)
        │   ├── tecnologia_check.py               → verde (CMS desactualizado)
        │   ├── accesibilidad_check.py             → verde (lang, formularios sin etiqueta)
        │   ├── experiencia_check.py                → verde (móvil, teléfono pulsable, favicon, formularios sin cifrar, peso, www)
        │   ├── rendimiento_check.py                → verde, opt-in (PageSpeed, móvil+ordenador, 4 categorías cada uno)
        │   └── archivos_expuestos.py                → ÁMBAR, opt-in solo con consentimiento
        ├── ia/
        │   ├── cliente.py               → envoltorio del proveedor de IA (hoy Claude/Anthropic — ver nota abajo)
        │   ├── interpretar.py            → botón 1: hallazgos en lenguaje llano
        │   └── soluciones.py              → botón 2: soluciones + nota estimada tras aplicarlas
        ├── pdf/
        │   └── generar_pdf.py             → informe de marca en PDF (WeasyPrint), reaprovecha informe+soluciones ya cacheados
        └── notificaciones/
            ├── enviar.py                   → envío genérico de email (Gmail SMTP), no sabe nada de solicitudes
            └── mensajes.py                  → contenido de los emails de solicitud (cliente + aviso a Alberto)
    ├── herramientas/
    │   └── lote.py                → INTERNO: revisa un CSV de dominios y los ordena por quién está peor
    ├── tests/                     → pytest (69 tests): puntuación, semáforo, checks con HTML fijo, validación de dominios
    └── requirements-dev.txt        → pytest/playwright, NO se instalan en Railway
```

**Los tests** se lanzan con `cd backend && .venv/bin/python -m pytest`. **Ojo: el atajo `.venv/bin/pytest` está roto** — su shebang apunta a `PRUEBAS PROG/PIPOSCAN/backend/.venv/...`, la ruta de cuando el proyecto se llamaba así, y falla con "No such file or directory". Lanzarlo como módulo (`python -m pytest`) lo esquiva sin tener que rehacer el venv. No tocan la red: a los checks se les pasa el HTML ya "descargado". Prueban sobre todo los casos donde Pipo podría **acusar de más**, que es lo que costaría credibilidad delante de un cliente. Ya han pagado su coste: encontraron que la detección de favicon no funcionaba nunca (`soup.find("link", rel=lambda...)` no hace lo que parece con atributos de varios valores en BeautifulSoup).

No hay `__init__.py` en ningún paquete — funciona porque Python 3.3+ soporta "namespace packages" implícitos. No hace falta añadirlos.

---

## Endpoints de la API

> **Dos llaves distintas, no las confundas:**
> - `?t=` — el **token del escaneo**, que viaja en el enlace del informe. Lo tiene el cliente. Sin él, `403`.
> - `?clave=` — la **clave de administración** (`CLAVE_ADMIN`). Solo la tiene Alberto. Protege el panel, los `/check/*` y las soluciones.

| Endpoint | Qué hace | Notas |
|---|---|---|
| `GET /health` | Salud del servidor | — |
| `GET /check/{...}?dominio=&clave=` | Cada check por separado | **Requiere `clave` de admin** desde el 13 ago 2026 (antes estaban abiertos a internet, ver P0-bis). Valida el dominio igual que `/api/scan` |
| `GET /api/scan?dominio=&declara_titularidad=true&consiento=&incluir_rendimiento=` | Orquesta todos los checks en paralelo, guarda en DB | **Rate limited: 5/min por IP real.** `declara_titularidad` es **obligatorio** (`400` si falta) y queda registrado con IP y fecha. `consiento=true` activa `archivos_expuestos`; `incluir_rendimiento=true` añade PageSpeed (+10-15s). Devuelve `token`, que hay que llevar a todo lo demás |
| `GET /api/scan/{id}?t=` | Recupera un escaneo guardado | `403` sin token |
| `GET /api/estadisticas` | Nº de webs revisadas, nota media y % con fallo grave | Rate limited 30/min. Cuenta cada dominio una vez (su escaneo más reciente). Alimenta el dato de la landing y el "tu web frente a la media" del informe |
| `GET /api/scan/{id}/rendimiento?t=` | Audita velocidad (PageSpeed) del dominio de ese escaneo | Rate limited 5/min. **Cacheado** en `rendimiento_json` |
| `GET /api/informe/{id}?t=` | Hallazgos interpretados por IA + nota (determinista) + desglose por familias + comparación con el escaneo anterior + precio orientativo del arreglo | Rate limited 5/min. **Cacheado** en `informe_json`. Familias/comparación/precio se añaden al vuelo, no se cachean dentro del informe |
| `POST /api/informe/{id}/soluciones?clave=` | Soluciones paso a paso | **HERRAMIENTA INTERNA**: requiere clave de admin, no hay ningún botón público que lleve aquí. Es lo que se vende, ver P2 |
| `GET /api/informe/{id}/pdf?t=&marca=` | Informe en PDF con marca Pipo (`app/pdf/generar_pdf.py`) | **Gratis** (solo token). **NO lleva soluciones** a propósito. `marca=` pone "Preparado para X" en portada (para agencias) |
| `POST /api/leads?email=&dominio=&id_escaneo=&t=` | Lista de avisos ("cuando esté la revisión mensual, avísame") | Rate limited 5/min. Guarda en tabla `leads`, sin FOREIGN KEY hacia `escaneos` a propósito |
| `POST /api/solicitudes?email=&dominio=&id_escaneo=&t=&telefono=&mensaje=` | Solicitud de "arregladlo vosotros" — el producto de pago | Rate limited 5/min. Guarda en tabla `solicitudes`, manda el diagnóstico al cliente y avisa a Alberto. **No cobra ni pide pago por adelantado**: es un servicio, primero se presupuesta |
| `GET /api/solicitudes?clave=` | Lista todas las solicitudes — panel privado (`landing/panel.html`) | Rate limited 20/min. `403` si la clave no coincide |
| `POST /api/solicitudes/{id}/notas?clave=&notas=` | Guarda las notas libres de una solicitud | Rate limited 20/min. Sustituye el texto, no acumula |
| `POST /api/solicitudes/{id}/cobro?clave=&importe=` | Registra cuánto se ha cobrado, con la fecha de hoy | Rate limited 20/min. Manual — Pipo no cobra nada automáticamente |
| `GET /api/leads?clave=` | Todos los emails captados por el formulario de avisos | Rate limited 20/min. Incluye `consiente_marketing` por fila |
| `GET /api/actividad?clave=` | Los últimos 60 escaneos, con el email captado si lo hay | Rate limited 20/min. "Quién ha entrado a la web" |
| `POST /api/solicitudes/{id}/estado?clave=&estado=` | Mueve una solicitud: `nueva` → `presupuestada` → `hecha` | Rate limited 20/min. `400` con un estado inventado, `404` si no existe |

---

## Decisiones de diseño ya tomadas (no las repitas ni las cuestiones sin motivo)

1. **La nota (0-100) nunca la calcula la IA** — la calcula `puntuacion.py` con una fórmula fija. Es determinista y reproducible a propósito, para que la IA no pueda "inventar" una puntuación. La IA solo pone el texto explicativo. **Desde el 13 ago 2026 la fórmula es una media PONDERADA**: cada check tiene un peso (`PESOS`), de 3 (SSL, privacidad, archivos expuestos) a 1 (WHOIS, DNSSEC, accesibilidad). Antes todos pesaban igual y un `<title>` largo de más contaba como un certificado caducado.
2. ~~El peor check manda en el semáforo global~~ **CAMBIADO el 13 ago 2026** (`puntuacion.py::resumir_checks`). El problema medido: de los escaneos reales guardados, **todos** salían en rojo, incluida la web de Pipo — si todo es rojo, el semáforo no informa y el producto se lee como venta del miedo. Ahora los checks se agrupan en **tres familias** (`seguridad`, `cumplimiento`, `clientes`) y el color global se decide así:
   - **Rojo** solo si hay un rojo en un check de peso ≥2 de una familia crítica (seguridad o cumplimiento legal). Eso sí merece llamarse crítico.
   - **Ámbar** para cualquier otro rojo (un detalle menor, o algo de la familia "clientes") y para cualquier ámbar.
   - **Verde** si no hay nada.
   El principio original sigue vivo donde tiene sentido — dentro de seguridad manda el eslabón débil — pero un detalle de SEO ya no puede pintar el informe entero de rojo.
3. **`archivos_expuestos` es el único check ámbar**, apagado por defecto en `/api/scan`, solo se activa con `consiento=true`. Nunca debe entrar en el escaneo gratis.
4. **HIBP (Have I Been Pwned) está aparcado** — su API exige verificar la propiedad del dominio antes de consultarlo, lo cual no encaja con escanear dominios de terceros en self-service. Solo tendría sentido en el futuro nivel "Pipo + acompañamiento" (servicio manual, el cliente coopera).
5. ✅ **La capa de IA está desacoplada del proveedor** (`app/ia/cliente.py`) — el 11 ago 2026 se resolvió el problema de pago y se cambió de Google Gemini a **Claude (Anthropic)**, precisamente para dejar atrás la cuota gratuita de Gemini (ver P1 más abajo). El cambio solo tocó ese archivo — `interpretar.py` y `soluciones.py` no saben qué proveedor hay detrás, tal y como estaba pensado. `GOOGLE_GEMINI_API_KEY` se deja en `config.py` y en las variables de Railway sin usar, por si algún día hiciera falta volver atrás; `google-genai` se queda en `requirements.txt` por la misma razón.
6. **Modelo de Claude en uso:** `claude-haiku-4-5-20251001` (ver `app/ia/cliente.py`) — elegido por precio sobre `claude-sonnet-5` dado el volumen bajo de peticiones por escaneo (máximo 2, informe + soluciones, gracias a la caché del punto P1). Si la calidad de redacción no convence, el candidato a probar es `claude-sonnet-5`, más caro pero con mejor pluma en español.
7. ✅ **Las soluciones son herramienta interna, no producto** (cambiado el 13 ago 2026; antes eran el nivel de pago de 19€ junto al PDF). El razonamiento: el diagnóstico y el PDF cuestan céntimos de IA y no consumen tiempo de nadie, así que cobrarlos convertía Pipo en un negocio de muchos clientes a poco dinero — justo el que no se puede servir cobrando a mano por Bizum. Y había un riesgo concreto: entregar los pasos técnicos hace que el cliente se los reenvíe a su informático de siempre y la venta se pierda ahí. Ahora el diagnóstico y el PDF se regalan (crean la conversación) y lo que se vende es **aplicar los cambios**. `/soluciones` solo responde con la clave de admin y es lo que Alberto abre en el panel para hacer el trabajo.
8. ✅ **CORS restringido** (10 ago 2026) — ya no es `allow_origins=["*"]`. Con el backend en Railway (internet real) y la cuota de Gemini tan ajustada, dejarlo abierto permitía que cualquier página web disparase peticiones a la API desde el navegador de cualquier visitante. Hoy permite `http://127.0.0.1:5500` y `http://localhost:5500` (desarrollo local) y `https://piposcan.vercel.app` (la landing real, añadida el 10 ago 2026). Si algún día la landing cambia de dominio, hay que añadirlo aquí **y hacer `git push`** — si no, el navegador bloquea todas las llamadas a la API y la landing parece rota sin dar error claro.

---

9. **El rate limiting se identifica por `X-Forwarded-For`, no por la IP de la conexión** (`app/seguridad.py::ip_cliente`). Detrás del proxy de Railway, el `get_remote_address` que trae slowapi ve la IP del proxy, no la del visitante, y el límite **no se aplicaba nunca en producción** — comprobado con curl el 13 ago 2026: 7 escaneos seguidos, los 7 aceptados, mientras el mismo código en local cortaba al sexto. Si alguna vez se toca el rate limiting, **hay que verificarlo contra Railway**, no solo en local: es un fallo que no se ve desde el código.
10. **Todo lo de un escaneo va con token** (`?t=`). Los ids son correlativos; sin token, cualquiera podía recorrer `/api/scan/1,2,3...` y leer todos los escaneos con sus resultados. El token no es un sistema de cuentas: el enlace se sigue compartiendo tal cual, solo deja de ser adivinable.
11. **Pipo no ejecuta JavaScript, y ahora lo dice cuando importa** (`pagina.py::parece_dibujada_con_javascript`). En webs hechas con React/Vue el HTML llega vacío, y SEO/privacidad/accesibilidad daban por ausente lo que solo era invisible desde fuera. Ahora esos tres checks detectan el caso y responden "no hemos podido comprobarlo" en ámbar, en vez de acusar. Lo mismo con los banners de cookies: casi todos los reales (Cookiebot, Complianz, CookieYes, Iubenda, OneTrust...) se inyectan con JavaScript, así que se reconocen por el **script del gestor** — buscar la palabra "aceptar cookies" en el HTML fallaba en la mayoría de webs que sí cumplen, y es la acusación más grave que hace Pipo.

12. **El `www` no puede cambiar la nota, y la puerta de entrada a los checks no es la misma para todos** (16 ago 2026, `seguridad.py::dominio_raiz` y `variante_www`). Hasta esta fecha, escanear `ejemplo.com` y `www.ejemplo.com` daba resultados distintos **y los dos estaban mal**, cada uno por un lado. Medido en un caso real: 37 puntos de diferencia en el mismo negocio (`mchomeinmobiliaria.com`, 33 contra 70). Dos causas independientes:
    - **SPF, DMARC, CAA, DNSSEC y WHOIS solo existen en el dominio registrado.** Preguntarlos en el subdominio `www` devuelve silencio siempre, y Pipo tomaba ese silencio por una acusación (`dns` en ROJO a un dominio con DMARC en `p=quarantine`). Ahora `scanner.py` les pasa `dominio_raiz(dominio)`. **Regla al añadir un check nuevo: si mira registros del DNS o el registro del dominio, va con la raíz; si mira el certificado, las cabeceras o la página, va con el host tal cual lo pidió el usuario**, porque esas tres cosas sí son de cada host.
    - **Si la raíz no sirve la página pero `www` sí (o al revés), la descarga fallaba** y los seis checks de contenido se iban a rojo en cascada. Ahora `obtener_pagina()` reintenta con la otra variante y deja en `host_servido` cuál respondió. Y si no responde ninguna, esos checks salen en **`sin_datos`**, no en rojo: no poder leer una web es una limitación nuestra, no un fallo del negocio. `puntuacion.py` ya excluía `sin_datos` de la nota, así que no hubo que tocarlo.

    Es el mismo principio de la decisión #11 llevado hasta el final: **cuando Pipo no puede comprobar algo, lo dice; no lo cuenta como que está mal.** Es la clase de fallo que no se ve leyendo el código, solo verificando a mano contra webs reales.

13. **Pipo se identifica como `PipoBot`, y una página de error no es la web del cliente** (16 ago 2026, `pagina.py::USER_AGENT_PIPO`). El mismo día del `www` aparecieron cinco fallos más de la misma familia, todos encontrados verificando a mano los hallazgos del estudio de Churriana/Alhaurín contra las webs reales. El de fondo era el peor de todos:
    - **`obtener_pagina()` solo capturaba errores de red, no códigos de error HTTP.** Un `403` llegaba con `ok=True` y los checks analizaban la página de error —125 bytes— como si fuera la home: de ahí salían acusaciones de no tener ni H1, ni aviso legal, ni etiqueta de móvil, dichas con la misma seguridad que un hallazgo real. **Le pasaba a 6 de las 39 webs del estudio (15%)**, entre ellas un despacho de abogados y una clínica veterinaria que estaban en la lista de objetivos comerciales por hallazgos que no existían.
    - La causa de los 403 era el User-Agent de fábrica de `httpx` (`python-httpx/…`), que bastantes servidores bloquean. **Ahora Pipo se identifica por su nombre en todas las peticiones** (`Mozilla/5.0 (compatible; PipoBot/1.0; +https://pipoweb.com)`), en `pagina.py`, `headers_check`, `ssl_check`, `seo_check`, `tecnologia_check`, `experiencia_check` y `archivos_expuestos`. **Disfrazarse de Chrome funcionaría igual de bien y sería lo contrario de lo que Pipo dice ser**: un visitante identificado que solo mira lo público. Si algún día un servidor bloquea a `PipoBot` por su nombre, la respuesta correcta es aceptar el `sin_datos`, no camuflarse.
    - `ssl_check` pedía la redirección `http→https` sin UA, así que un 403 se leía como "la web sirve contenido sin cifrar". `experiencia_check` exigía la palabra `width` en el viewport, cuando `initial-scale=1` también adapta al móvil. `seo_check` decía "faltan etiquetas Open Graph" cuando faltaba solo `og:image`. `rendimiento_check` ponía en rojo una avería de la API de Google, y `archivos_expuestos` ponía en rojo un fallo de conexión — o sea, acusaba de tener archivos expuestos justo cuando no había podido comprobar ninguno.

    Efecto medido sobre las 38 webs: **nota media 63 → 69**, y las que tienen algún fallo grave bajan del 95% al 87%. **La lección, que es lo que hay que recordar: los tres bugs del `www` y estos cinco salieron todos de comprobar a mano con `curl`, `openssl` y `dig` lo que decía la nota — ninguno se veía leyendo el código.** Antes de poner un hallazgo delante de un cliente, verifícalo.

14. **El dominio oficial es `www.pipoweb.com`, con www, y los tres sitios que lo declaran tienen que decir lo mismo** (19 ago 2026). Search Console reportaba 3 de 5 páginas sin indexar y 0 impresiones desde el 13 ago, con dos motivos: "Página con redirección" (2) y "Rastreada: actualmente sin indexar" (1). La causa no era de contenido: **Vercel sirve `www.pipoweb.com` y redirige el apex ahí con un 308**, pero el `sitemap.xml`, el `canonical` de `index.html` y el `Sitemap:` de `robots.txt` declaraban el apex sin www. O sea, cada URL que Pipo le daba a Google era una redirección, y el canonical le decía a Google que la página buena era justo la que redirige. Google no indexa eso: se limita a anotar "redirección" y esperar.

    Arreglado alineando **todo** a www: sitemap (con `lastmod`), canonical y `og:url` de `index.html`, `og:image`, `twitter:image` y el `url`/`logo` del JSON-LD, `robots.txt`, y un `canonical` nuevo en `aviso-legal.html`, `privacidad.html` y `cookies.html`, que no tenían ninguno. **Si algún día se cambia el dominio principal en Vercel, hay que tocar esos tres sitios a la vez** — cambiar uno solo reproduce exactamente este fallo.

    Tres cosas más de la misma revisión:
    - **`informe.html` y `404.html` llevan ahora `noindex, follow`**, y `informe.html` está también en `robots.txt`. El informe de un cliente sin `?id=` es una página vacía y con `?id=` es contenido privado de un negocio concreto — no debe aparecer en Google jamás. Ese "Rastreada: actualmente sin indexar" era casi con seguridad esta página, y Google acertaba.
    - **`piposcan.vercel.app` seguía sirviendo `200` con el sitio entero duplicado**, con su propio canonical apuntando al apex. Contenido duplicado compitiendo con el dominio bueno. Ahora `vercel.json` tiene un `redirects` con `has: [{type: "host", value: "piposcan.vercel.app"}]` que lo manda a `www.pipoweb.com` con 308, conservando el query string — así los enlaces de informe compartidos con el dominio viejo (`?id=&t=`) siguen funcionando. El host exacto no coincide con los deployments de preview, que siguen accesibles.
    - **El `<h1>` de la landing nacía vacío**: el efecto máquina de escribir lo rellenaba con JS y el `aria-label` no cuenta como contenido indexable. Para un dominio nuevo sin autoridad, regalar el titular es caro. Ahora el texto viene en el HTML y un `<script>` minúsculo **pegado justo debajo del `</h1>`** lo guarda en `window.__titularPipo` y vacía los huecos antes del primer repintado — va ahí, y no en el script del final, para que el titular no se vea entero y de golpe antes de empezar a teclearse. Verificado con Chrome de verdad: a los 0,5s se está escribiendo, al final se lee completo, cero errores de JS. Si el JS no llega a ejecutarse, el titular se queda visible tal cual.

    **Lo que no era el problema, para no perseguirlo otra vez:** las 0 impresiones. El sitio se dio de alta el 13 de agosto y Search Console tarda días en dar datos; con 2 páginas indexadas y sin enlaces entrantes, cero impresiones a los seis días es lo normal, no un síntoma.

---

## Qué falta por hacer, con prioridad

### ✅ P0-bis — Auditoría del 13 ago 2026: cerraduras abiertas en producción, HECHO

Una auditoría del proyecto entero (leyendo el repo y lanzando peticiones reales contra Railway) encontró tres agujeros que el código no dejaba ver, más un puñado de promesas que la web hacía y el código no cumplía. Todo arreglado el mismo día:

- ✅ **El rate limit no se aplicaba en producción** — ver decisión #9 arriba. Arreglado con `key_func=ip_cliente`. **Verificado en Railway después de desplegar**: siete escaneos seguidos, `429` a partir del segundo (el cubo ya venía gastado de las pruebas anteriores). Hallazgo extra del despliegue: **Railway reescribe `X-Forwarded-For`** con la IP real, así que no se puede esquivar el límite mandando la cabecera falsificada — se probó con siete IPs inventadas distintas y el límite saltó igual. Si algún día se cambia de hosting, hay que volver a comprobar esto.
- ✅ **Los `/check/*` estaban abiertos a internet**, sin límite y aceptando hasta direcciones internas (`169.254.169.254`): cualquiera podía usar el servidor de Pipo como escáner de webs ajenas, con la IP de Pipo en los registros del sitio escaneado. Ahora van detrás de `?clave=` en un `APIRouter` con dependencia, para que no se pueda añadir un endpoint nuevo ahí y olvidarse de protegerlo.
- ✅ **`/docs` estaba público** — ahora solo con `PIPO_DOCS=1` en el `.env` local. Apagado por defecto, así producción queda segura sin tener que configurar nada en Railway.
- ✅ **Los escaneos eran enumerables** — tokens (decisión #10). La migración rellena token a las filas antiguas, así que no queda ninguna accesible sin él.
- ✅ **Validación del dominio de entrada** (`app/seguridad.py`): normaliza lo que escriba el usuario (`https://www.x.es/contacto?a=1` → `www.x.es`), rechaza IPs, puertos, `localhost`, sufijos internos, y **comprueba que resuelve a una IP pública** antes de tocar nada — un dominio normal puede apuntar a `127.0.0.1` a propósito (el patrón SSRF).
- ✅ **El consentimiento de titularidad ahora se guarda de verdad** (`declara_titularidad`, obligatorio, con IP y fecha). La FAQ decía "queda registrado" y era la única frase de la web que prometía algo que el código no hacía — y justo la que protege a Alberto.
- ✅ **El texto de la IA ya no se inyecta con `innerHTML`** en `informe.html`, sino con `textContent` sobre nodos creados a mano. Ese texto describe contenido de la web analizada, así que había un camino estrecho pero real desde una web hostil hasta código ejecutándose en el dominio de Pipo.
- ✅ **Se quitó de la landing lo que no existía**: el check de "Brechas conocidas" (HIBP está aparcado desde el principio, decisión #4) y el botón de suscripción a "Vigilancia", que ahora aparece como *En preparación* y capta el email en vez de fingir un producto. El **43%** inventado del titular se sustituyó por el dato real de `/api/estadisticas`, que se oculta solo si todavía hay menos de 10 webs revisadas.

### ✅ P0 — Bloqueante legal, HECHO (10 ago 2026)
- **Checkbox de consentimiento** en la landing (`index.html`): "Declaro ser el titular de este dominio o tener autorización para analizarlo". El botón "Analizar" empieza deshabilitado y solo se activa al marcarlo; además hay una comprobación en el `submit` por si se reactiva el botón desde devtools. **Importante:** este checkbox NO se envía como `consiento=true` al backend — es solo la puerta legal del escaneo en sí, distinta del parámetro `consiento` que activa el check ámbar (`archivos_expuestos`), que sigue sin tocarse en el escaneo gratis (decisión #3 intacta).
- **Páginas legales reales**: `aviso-legal.html`, `privacidad.html`, `cookies.html`, enlazadas desde el footer y desde el propio checkbox. Identificación con datos reales de Alberto Yules (persona física) y `alberyules11@gmail.com`; NIF y domicilio quedan como `[PENDIENTE]` a propósito — el proyecto sigue en `localhost`, sin operar comercialmente, así que no hace falta darse de alta como autónomo todavía. Cuando se formalice como actividad económica real, rellenar esos dos huecos.
- **Bonus no pedido en el planning**: página `404.html` con Pipo desorientado (animación de balanceo + ojos mirando a los lados + varios interrogantes flotando). Pendiente de activarla de verdad en el hosting final (ver P1, "desplegar backend real" — anotar ahí también activar el 404 del hosting de la landing).

### ✅ P1 — Necesario antes de enseñar el producto fuera de tu propio ordenador, HECHO (10-11 ago 2026)

> **Pipo ya está entero en internet**: landing en `https://piposcan.vercel.app` → backend en `https://pipo-analiza-production.up.railway.app`. Un `git push` a `main` despliega las dos cosas.
>
> ✅ **El bloqueante de la cuota de Gemini (20 peticiones/día) se resolvió el 11 ago 2026** cambiando el proveedor de IA a Claude (Anthropic) — ver decisión #5 y #6. Probado en local con escaneo real: `/api/informe/{id}` y `/api/informe/{id}/soluciones` responden bien con Claude. **Pendiente antes de que funcione en producción:** añadir `ANTHROPIC_API_KEY` a las variables de entorno de Railway (dashboard, igual que se hizo con `GOOGLE_GEMINI_API_KEY`) y hacer `git push`.
- ✅ **Rate limiting en `/api/informe/{id}` y `/api/informe/{id}/soluciones`** — hecho (10 ago 2026), mismo patrón `slowapi` que `/api/scan`, 5/minuto por IP. Probado con curl real: la 6ª petición seguida da `429` en ambos endpoints. De paso se confirmó con el log que los `502` puntuales de estos endpoints son el fallo de cuota de Gemini del punto siguiente, no un bug del rate limiting.
- ✅ **Caché de resultados de IA y PageSpeed** — hecho (10 ago 2026). `escaneos` tiene 3 columnas nuevas (`informe_json`, `soluciones_json`, `rendimiento_json`), añadidas con una migración automática en `inicializar_db()` (mira con `PRAGMA table_info` y hace `ALTER TABLE` solo si falta la columna — segura de re-ejecutar, no borra datos existentes). `/api/informe/{id}`, `/api/informe/{id}/soluciones` y el nuevo `/api/scan/{id}/rendimiento` miran la caché antes de llamar a la IA/Google; si ya existe, la devuelven y no gastan cuota. Probado: con IA real (endpoint de rendimiento) la 2ª petición pasó de ~10s a ~23ms con resultado idéntico; con IA simulada (mock, para no gastar la cuota agotada de Gemini) se confirmó que `/api/informe` y `/soluciones` solo llaman a la IA una vez por escaneo aunque se pidan dos veces. Caso límite cubierto: si PageSpeed no tiene clave configurada o falla la red, ese resultado vacío **no se cachea** (se comprueba que `datos` no esté vacío antes de guardar), para no dejar un escaneo con "velocidad no disponible" para siempre. El botón "Comprobar velocidad" de `informe.html` ahora llama a `/api/scan/{id}/rendimiento` en vez de al antiguo `/check/rendimiento?dominio=` (ese endpoint de depuración se mantiene, pero ya no lo usa el frontend).
- ✅ **Investigado la latencia de Gemini** (10 ago 2026) — **hallazgo importante, cambia el diagnóstico**: el problema no es (solo) latencia, es que el plan gratuito de `gemini-3.5-flash` tiene una **cuota diaria de solo 20 peticiones** por proyecto (`RESOURCE_EXHAUSTED`, metric `generate_content_free_tier_requests`, `quotaValue: 20`). Se agotó sola durante las pruebas de esta sesión (escaneos + tests de rate limiting + benchmark). Esto es mucho más urgente que la latencia en sí: **con 20 peticiones/día, Pipo no aguanta ni un puñado de visitas reales**, y la caché recién montada ayuda (cada escaneo ahora gasta como mucho 2 peticiones de por vida, informe + soluciones, en vez de una por cada clic) pero no resuelve el fondo. Antes de enseñárselo a nadie fuera de pruebas propias, hay que mirar el plan de facturación de Gemini (`https://ai.google.dev/gemini-api/docs/rate-limits`) — probablemente haga falta activar un tier de pago, lo cual reabre la pregunta de la decisión #5 (¿merece la pena resolver el problema de la tarjeta con Anthropic/Claude en vez de pagar por Gemini?). No se pudo medir la latencia real dentro de la cuota (los pocos segundos que sí respondió, la llamada trivial tardó ~0.2-0.3s en fallar por cuota, no es dato de latencia real) — pendiente remedir cuando haya cuota u otro plan.
- ✅ **Backend desplegado en un servidor real** — hecho (10 ago 2026), en **Railway**. Repo en GitHub: `albertoyules/pipo-analiza` (privado; cuenta `gh` local tiene también una `domingocroman-afk`, activa por defecto — comprobar con `gh auth status` y `gh auth switch --user albertoyules` si hace falta volver a subir algo). URL pública: `https://pipo-analiza-production.up.railway.app`. Detalles:
  - `backend/Procfile` nuevo (`web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`) — Railway lo detecta solo junto con `requirements.txt`.
  - En Railway, el "Root Directory" del servicio está puesto a `backend` (el repo tiene `backend/` y `landing/` juntos; Railway solo necesita la primera).
  - Variables de entorno puestas a mano en el dashboard de Railway: `GOOGLE_GEMINI_API_KEY`, `GOOGLE_PAGESPEED_API_KEY` (mismos valores que `backend/.env` local).
  - `.gitignore` nuevo en la raíz del repo — antes no existía ninguno, así que hasta ahora nada estaba realmente protegido de subirse a git por accidente. Excluye `.env`, `pipo.db`, `.venv/`.
  - Probado desde fuera con curl real: `/health` y `/api/scan` responden bien en la URL de Railway.
  - Redeploy automático: cualquier `git push` a `main` dispara un redeploy solo, sin tocar nada en el dashboard.
  - Nota: el repo de GitHub se renombró a `albertoyules/piposcan` (la URL vieja `pipo-analiza` sigue redirigiendo, por eso `git push` funciona igual desde el remoto antiguo).
  - ✅ **El disco de Railway es efímero — arreglado y verificado** (11 ago 2026). Se detectó al ver que un escaneo nuevo volvía a dar `id: 1` después de un `git push`, cuando el día anterior ya se habían hecho escaneos: el contenedor se borra entero en cada despliegue, así que `pipo.db` se vaciaba y **todos los enlaces `informe.html?id=X` compartidos dejaban de funcionar**. Solución: `database.py` lee la variable de entorno **`PIPO_DB_DIR`**; si existe, guarda `pipo.db` ahí, y si no existe usa `backend/` como siempre (compatible hacia atrás — en local no hay que configurar nada). En Railway se creó un volumen montado en `/data` y se puso `PIPO_DB_DIR=/data` en las variables del servicio. **Probado de verdad**: se guardó un escaneo, se forzó un redeploy completo desde el panel, y el escaneo seguía recuperable con la misma fecha tras el redeploy; el siguiente escaneo siguió la numeración (`id: 2`) en vez de reiniciar a `id: 1`.

- ✅ **Landing desplegada en Vercel** — hecho (10 ago 2026). URL pública: **`https://piposcan.vercel.app`**. Con esto P1 queda cerrado del todo. Detalles:
  - **El fallo inicial**: Vercel daba `404: NOT_FOUND` porque desplegaba la raíz del repo, donde no hay ningún `index.html` (está dentro de `landing/`). Se arregla en **Settings → General → Root Directory = `landing`**, igual que Railway usa `backend`. Ojo: cambiar ese campo **no** dispara redeploy solo — hay que ir a Deployments → `...` → **Redeploy** a mano.
  - Usar siempre el dominio estable `piposcan.vercel.app`, no las URLs largas con hash (`piposcan-nem2cnubs-...`), que son de cada deployment concreto y cambian con cada push.
  - Redeploy automático con cada `git push` a `main`, igual que Railway: un solo push despliega backend y landing a la vez.
  - Su dominio ya está en `allow_origins` de `main.py` (ver decisión #8).

- ✅ **Vida y "modo invierno" en la landing** (11 ago 2026) — idea de Alberto, solo frontend, solo `index.html`, sin backend ni librerías:
  - Pipo ahora está posado en un árbol (nuevo `<symbol id="tree">`), gira un poco la cabeza, mueve los ojos y parpadea. Si le haces clic, salta con squash & stretch y saluda con la lupa.
  - Un copo de nieve flota a su lado ("¡Haz que Pipo tenga frío!"); al pulsarlo, el hielo se propaga **en círculo desde el propio copo** (`clip-path` animado, con las coordenadas del clic en las variables `--ox`/`--oy`), con onda de choque, escarcha en los bordes, nieve con viento y Pipo tiritando. A los ~5,8s se deshiela.
  - **Por qué se ve bien sin repintar cada color a mano**: la capa azul usa `mix-blend-mode: color`, que cambia el tono pero respeta la luminosidad, así el texto sigue legible.
  - **Bug ya corregido, no reintroducirlo**: la primera versión congelaba con `body.modo-invierno *{animation-play-state:paused}`. Ese `*` paralizaba también la nieve y a Pipo, y el efecto se veía como un simple filtro azul plano. Ahora solo se pausan los elementos decorativos concretos.
  - Rendimiento (preocupación explícita de Alberto): todo se anima con `transform`/`opacity` (compositor de la GPU) y los ~33 elementos de nieve/viento se crean al pulsar y **se borran del DOM al terminar** — en reposo el coste es cero.

- ✅ **Pipo vuela a ver la nota + bocadillo de viñeta** (12 ago 2026, `index.html`) — sustituye a la reacción anterior (una simple inclinación de 0,9s). Al pintarse el resultado del escaneo gratis, `reaccionarPipo()` monta una escena de 4,2s: despega del árbol → se acerca volando a la tarjeta del resultado → se queda ~2s mirándola **de reojo** → vuelve a posarse → le sale un **bocadillo estilo viñeta** sobre la cabeza con lo que opina (`MENSAJES_ANIMO`, según el semáforo global).
  - **El banner `.mensaje-animo` que había encima de la tarjeta se ha eliminado**: decía exactamente la misma frase que ahora dice el bocadillo, y verlo dos veces seguidas quedaba redundante. Si alguna vez se quiere recuperar, está en el historial de git.
  - **Adónde vuela son variables CSS, no números fijos** (`--vx`/`--vy` en `.pipo`): en ordenador la tarjeta está a su izquierda (dos columnas) y en móvil justo encima (una columna), así que el mismo keyframe sirve para los dos casos cambiando solo las variables en el `@media(max-width:880px)`.
  - **El bocadillo se ancla por abajo** (`bottom:265px`), no por arriba: Pipo también está anclado al fondo del escenario, así el pico le queda siempre a la misma distancia de la cabeza aunque el escenario crezca al aparecer la tarjeta.
  - **Respeta la limitación conocida de `<use>`** (ver el comentario largo del CSS): lo que va dentro de `<symbol id="pipo">` —aleteo de las alas, mirada de reojo, cejas— usa solo **valores estáticos con transición** que JS activa/desactiva (el aleteo son dos posturas que se alternan cada 170ms), nunca `@keyframes` añadidos por JS; el vuelo sí es `@keyframes`, pero aplicado al `<svg id="pipo-hero">` de fuera, donde sí es fiable.
  - Comprobado con Chrome headless de verdad (capturas en ordenador y móvil, congelando fotogramas concretos del vuelo y de la aparición del bocadillo): posición al llegar a la tarjeta, cara de reojo, alas levantadas y bocadillo con su pico apuntando a la cabeza.

- ✅ **Escena de carga del informe: Pipo encima de la pantalla que analiza** (12 ago 2026, `informe.html`) — antes el búho de espaldas estaba **al lado** del documento, así que no se leía que estuviera analizándolo. Ahora `.escena-figuras` apila en columna (Pipo arriba, pantalla justo debajo). Se probaron dos versiones con lupa (colgando al lado, luego centrada por delante con el cristal asomando bajo el cuerpo) y Alberto decidió quitarla del todo — queda más limpio sin ella, solo el búho posado mirando hacia abajo. `#pipo-espaldas` volvió a su `viewBox` normal (`0 0 240 260`, como el símbolo de frente) y recuperó los pies.

### ✅ Ampliación del escáner: de 7 a 10 comprobaciones (11 ago 2026) — y a 11 el 13 ago (ver `experiencia_check.py`)
Alberto pidió revisar si Pipo estaba haciendo "todo el análisis posible" dentro de la regla 100% pasiva, y valorar una checklist de 20 puntos de un TikTok sobre qué le falta a cualquier web antes de lanzarla. De ahí salieron dos bloques de trabajo:

**A) 3 checks nuevos (nuevas filas en el semáforo):**
- `dominio_check.py` (check `dominio`): CAA (qué entidades pueden emitir certificados para el dominio) + DNSSEC. Para DNSSEC, **no vale con mirar la flag AD** de la respuesta del resolver (se probó y Cloudflare no la marca de forma fiable para clientes públicos) — la técnica que funciona de verdad es pedir la respuesta con la flag EDNS "DO" y comprobar si el servidor devuelve un registro RRSIG junto a la respuesta normal (su sola presencia confirma que la zona está firmada). Verificado con `isc.org` (tiene DNSSEC) y `cloudflare.com` (no lo tenía activo en su propio dominio, curiosamente).
- `whois_check.py` (check `whois`): fecha de caducidad del dominio. Consulta en dos pasos (primero `whois.iana.org` para saber qué servidor es responsable del TLD, luego ese servidor para el dominio en sí) porque no hay un único formato ni servidor WHOIS. **Ojo con esto si se retoca**: IANA no siempre usa el campo `refer:` para decir cuál es el servidor autoritativo — `.org` (y otros) usan `whois:` en su lugar; hay que aceptar los dos nombres de campo. Si no se reconoce el dominio o el formato de fecha, el resultado es **verde** con "no disponible", nunca rojo — no poder consultar WHOIS es una limitación nuestra, no un problema del sitio analizado.
- `accesibilidad_check.py` (check `accesibilidad`): atributo `lang` en `<html>` y campos de formulario sin ninguna etiqueta asociada (ni `<label>`, ni `aria-label`, ni envuelto en un label). No mide contraste de color ni nada que exija renderizar la página de verdad — sigue siendo 100% pasivo, solo HTML. Motivación explícita: desde junio de 2025 hay obligación legal en España/UE (Ley 11/2023, transposición de la European Accessibility Act) para bastantes negocios, así que esto no es solo "nice to have".

**B) Ampliaciones a checks que ya existían (mismo check, más señales, sin añadir filas nuevas):**
- `headers_check.py`: además de las 4 cabeceras "core" (que siguen siendo las únicas que mandan en el semáforo), ahora también avisa si hay cookies sin `Secure`/`HttpOnly`/`SameSite`, si faltan `Referrer-Policy`/`Permissions-Policy`, y si el servidor filtra su versión exacta en `Server`/`X-Powered-By`. Estos avisos van en el `detalle` y en `datos`, pero **no** bajan el semáforo por sí solos — se consideró que penalizar doble por encima de las 4 cabeceras core sería demasiado severo.
- `ssl_check.py`: comprueba también que `http://dominio` (sin cifrar) redirige de verdad a `https://`. Si el puerto 80 ni responde, se cuenta como correcto (no hay puerta sin cifrar que redirigir). Los problemas del certificado en sí (caducado, a punto de caducar, TLS viejo) siempre mandan sobre este aviso.
- `mixed_content_check.py`: además de recursos `http://` en una página `https://` (como antes), ahora detecta scripts/hojas de estilo cargadas desde **otro dominio** (típicamente un CDN) sin el atributo `integrity` (Subresource Integrity/SRI). Si el CDN se ve comprometido algún día, ese código se ejecutaría igual en la web del cliente. Nunca sube a rojo por sí solo, y el mixed content de verdad (más grave) manda si aparecen los dos a la vez.

**Conectado en `scanner.py`** (los 3 checks nuevos se lanzan en paralelo con el resto, igual que todos) y con endpoints de depuración `/check/dominio`, `/check/whois`, `/check/accesibilidad`. Probado un escaneo completo real (`github.com`): 10 checks, 1.2s de duración total — el paralelismo sigue absorbiendo bien la carga extra. `NOMBRES_CHECK` en `index.html` actualizado con los 3 checks nuevos, y el "Semáforo de las 7 comprobaciones" de la tarjeta de precios pasó a "10 comprobaciones".

### ✅ Huecos de SEO/marca de la propia web (11 ago 2026)
Mismo encargo de arriba, pero aplicado a `piposcan.vercel.app` en vez de a las webs que Pipo analiza — irónico no pasar el propio escaneo de Pipo. Verificado todo con curl real contra producción, no de memoria:
- **Favicon** con el búho de Pipo: `favicon.svg` (vectorial, recorte del símbolo `#pipo` sin lupa ni pies porque a 16-32px son ruido) + `favicon-32.png`/`favicon-192.png`/`apple-touch-icon.png`/`favicon.ico` generados con `cairosvg` (instalado en `backend/.venv`, que ya tenía Pango/Cairo funcionando gracias a WeasyPrint) en todas las páginas.
- `robots.txt` + `sitemap.xml` — no existían. `robots.txt` excluye `pedidos.html` (el panel privado) por si acaso, aunque ya tiene `noindex`.
- Meta description en todas las páginas; Open Graph + Twitter Card completos en `index.html`, con imagen de marca propia (`og-image.png`, generada igual que el favicon a partir de un SVG con el owl + texto).
- Datos estructurados `schema.org` (`Organization`) en `index.html`.
- CTA fija en móvil (`#cta-fija-movil`): el menú entero (con el único botón "Revisar mi web") se ocultaba por completo en pantallas pequeñas (`nav-links{display:none}` en `@media(max-width:780px)`), sin ningún CTA visible mientras se hacía scroll. Se esconde sola cuando el formulario real (`#demo`) ya está a la vista, para no duplicar el CTA.
- Promesa de tiempo de respuesta ("confirmamos el pago normalmente en menos de 24 horas") añadida en la FAQ, el email de pedido (`app/notificaciones/mensajes.py`) y la confirmación en pantalla — checklist del TikTok, punto "response time promise".
- **Falsa alarma corregida sobre la marcha**: se pensó que el 404 personalizado (`404.html`) no se estaba sirviendo en Vercel, porque `curl -o /dev/null -w "%{http_code}"` daba `404`. Eso es tratar el código de estado como si probara "página genérica" — un 404 bien hecho **debe** devolver estado 404 aunque enseñe contenido propio. Al mirar el cuerpo real de la respuesta (`content-disposition: filename="404.html"`, título "Página no encontrada — Pipo"), se confirmó que ya funcionaba bien desde que se desplegó. No se tocó nada, no hacía falta.
- **No hecho hoy, sí confirmado que hace falta más adelante**: Google Analytics. Se preguntó primero porque instalarlo de verdad exige un banner de consentimiento (una cookie de analytics no puede cargar antes de aceptar, por LSSI/RGPD) y una propiedad de Analytics que Alberto no ha creado. Por ahora solo se confirmó que `cookies.html`/`privacidad.html` siguen describiendo la realidad actual (solo Google Fonts, nada de analítica) — **queda pendiente de verdad, ver la lista de "Qué falta por hacer" más abajo**, no descartado.
- **Matización legal importante, corregida tras aviso de Alberto**: el primer intento de actualizar `aviso-legal.html`/`privacidad.html` decía que Pipo "ya procesa pagos y tiene clientes reales" — Alberto corrigió que sigue en fase de pruebas sobre sus propios dominios (trabajos ya desplegados por él), sin haber contactado todavía a ninguna empresa. Las páginas legales quedaron con esa redacción más precisa: publicado en internet, pero en pruebas, sin clientes reales todavía.

### ✅ Modelo de precios reescrito (13 ago 2026) — sustituye al reparto de 19€

El escalón de 19€ tenía tres problemas: el nivel de 19€/mes costaba lo mismo que el pago único e incluía más (nadie elegiría el único), 19€ no paga los quince minutos de gestión manual que costaba cada pedido, y se cobraba por lo que sale barato (el PDF) en vez de por lo que el cliente quiere (que el problema desaparezca). Estructura actual:

| Nivel | Qué incluye | Precio | Estado |
|---|---|---|---|
| **Revisión** | Escaneo, semáforo por áreas, informe interpretado y **PDF** | Gratis | Funcionando |
| **Te lo arreglamos** | Alberto aplica los cambios y enseña el antes/después | 89-149€, calculado por `calcular_precio_arreglo()` | Funcionando (solicitud + email, sin cobro automático) |
| **Tranquilidad** | Revisión mensual, avisos, arreglos pequeños | 15-25€/mes | **No existe**: en la landing como "En preparación", capta email |
| **Para profesionales** | Informes en lote con marca de la agencia | A convenir | Media pieza hecha: `?marca=` en el PDF y `herramientas/lote.py` |

- **Nada se cobra por adelantado**: es un servicio, primero se presupuesta. Por eso desaparecieron el Bizum en pantalla, la referencia de pago y el "plan B" si fallaba el email. `TELEFONO_BIZUM` deja de usarse en el código (la variable puede quedarse en Railway sin molestar).
- La tabla `pedidos` se queda huérfana con los datos de prueba de la demo; la nueva es `solicitudes` (con `estado`: nueva → presupuestada → hecha).
- El PDF **no lleva las soluciones** (ver decisión #7) pero sí un desglose por áreas y una llamada a "¿prefieres que lo arreglemos nosotros?".

### ✅ El envío de email — resuelto el 13 ago 2026, cambiando de Gmail SMTP a Resend

**El problema:** Railway bloquea el tráfico SMTP saliente por completo. Se probaron los dos puertos estándar (465 y 587) con las credenciales de Gmail bien puestas, y los dos fallaban con el mismo patrón exacto: la petición a `/api/solicitudes` tardaba ~30 segundos (dos llamadas en serie con `timeout=15` cada una) antes de devolver `email_enviado: false`. Esa cifra tan exacta es la firma de que la conexión de red ni se establece — un fallo de credenciales se ve casi al instante, no justo al límite del timeout. No era un problema de la contraseña de Alberto.

**La solución:** dejar de usar SMTP. `app/notificaciones/enviar.py` ahora llama a la API de **Resend** por HTTPS (puerto 443, que ningún hosting bloquea) en vez de abrir una conexión SMTP. `RESEND_API_KEY` en Railway; `GMAIL_EMAIL` se queda solo como el buzón donde Alberto recibe los avisos internos, `GMAIL_APP_PASSWORD` ya no se usa en ningún sitio.

**Verificado con curl real contra producción**, no en local: la petición pasó de tardar ~30s a 0,3s (confirma que ya no intenta SMTP), y `/api/solicitudes` devolvió `email_enviado: true` de verdad, con los dos emails (cliente + aviso a Alberto) llegando a su bandeja.

**Diagnóstico rápido cuando falló la primera vez:** el fallo inicial no fue de Resend, fue que `RESEND_API_KEY` llegaba vacía al proceso — Alberto había guardado la variable en Railway pero el deploy vigente no la había recogido todavía. Se añadió un endpoint temporal (`GET /api/diagnostico-email?clave=&destinatario=`, ya borrado) que llamaba a `enviar_email()` y devolvía el error real de Resend en vez del `email_enviado: false` silencioso de `/api/solicitudes` — así se vio en un segundo que la clave estaba vacía, no que Resend la rechazara. Si algún día el email vuelve a fallar, ese es el patrón a repetir: no adivinar, exponer el error real con un endpoint protegido por `CLAVE_ADMIN` y borrarlo después.

**Pendiente de verdad, no bloqueante:** sin un dominio propio verificado en Resend, los emails salen desde `onboarding@resend.dev`, no desde algo con marca (`pipo@pipo.es`). En cuanto se decida el dominio de Pipo (ver más abajo, todavía sin decidir), hay que verificarlo en el panel de Resend (añadir unos registros DNS) y cambiar `REMITENTE` en `enviar.py`.

---

### ✅ Panel CRM privado (`landing/panel.html`) y captura de email para marketing — hecho el 13 ago 2026

Pedido explícito de Alberto tras la auditoría: quitar cualquier muro delante del informe gratis, pero tener un punto claro donde capturar el email para poder recordarle a un negocio que vuelva más adelante; y una pantalla privada donde ver de un vistazo todo lo que tiene abierto (quién ha entrado, quién ha dejado su email, quién ha pedido un arreglo, quién ha pagado).

**El informe sigue sin muro** — eso no cambió. Lo que se añadió es un único punto de captura de email, honesto sobre su propósito:

- El formulario "Avísame si algo empeora" de `informe.html` se retextó a **"No pierdas de vista tu web"**, y su casilla dejó de ser un consentimiento genérico ("acepto que me contacten") para ser explícitamente de marketing: *"Quiero recibir por email avisos sobre mi web y, de vez en cuando, consejos y ofertas de Pipo. Puedo darme de baja cuando quiera."* Al marcarla se manda `marketing=true` a `/api/leads`, que se guarda en la nueva columna `leads.consiente_marketing` — es la base legal (RGPD art. 6.1.a, consentimiento expreso y específico) que permite mandar campañas más adelante; sin ella marcada, ese email solo debería usarse para lo que se pidió en el momento. `privacidad.html` actualizado con esta base legal.

**`landing/panel.html`** — nuevo, sustituye a `pedidos.html` como panel principal (`pedidos.html` se deja tal cual, funcional pero superado; se puede borrar más adelante). Misma protección de siempre (`?clave=` contra `CLAVE_ADMIN`), tres pestañas:

- **Solicitudes**: el pipeline se amplió de 3 pasos a 6 — `nuevo → contactado → presupuesto_enviado → pagado → arreglado → cerrado` (antes: `nueva/presupuestada/hecha`). Cada tarjeta tiene un selector de estado (no solo "avanzar al siguiente": se puede saltar a cualquier estado, un caso real no siempre es lineal), notas libres editables con botón de guardar, y "Registrar cobro" (pide el importe con un `prompt()`, guarda importe y fecha). Filtro "solo lo que necesita mi atención" que esconde los casos en `cerrado`.
- **Leads**: tabla de emails captados por el formulario de avisos, con si consintieron marketing o no.
- **Actividad reciente**: los últimos 60 escaneos, con el email asociado si lo hay — "quién ha entrado a la web", tal cual se pidió.

**Migración de datos**: la tabla `solicitudes` ya existía en producción desde esta misma mañana con el pipeline viejo. `CREATE TABLE IF NOT EXISTS` no toca el `DEFAULT` de una tabla que ya existe, así que hicieron falta dos cosas: (1) `guardar_solicitud()` pasa `estado='nuevo'` explícito en el INSERT en vez de confiar en el DEFAULT de la columna, y (2) una migración de una sola vez en `inicializar_db()` que traduce las filas viejas (`nueva→nuevo`, `presupuestada→presupuesto_enviado`, `hecha→cerrado`). Verificado en producción: las 5 solicitudes de pruebas de esta mañana pasaron limpiamente al pipeline nuevo.

**Bug real encontrado con Playwright antes de desplegar**: `importe_cobrado` es una columna `TEXT` (por cómo funciona `_asegurar_columna`), así que en el panel `suma + s.importe_cobrado` concatenaba strings en vez de sumar (`"0" + "120" + "0"` → `"01200€"`). Arreglado forzando `Number(...)` antes de sumar.

**Datos de ejemplo en producción, a propósito**: por petición de Alberto, se sembraron 6 solicitudes y 2 leads ficticios (uno por cada paso del pipeline) para poder ver el panel con contenido real antes de tener casos de verdad — emails y notas con la palabra **DEMO** en mayúsculas, dominios reales que sí resuelven (wordpress.org, github.com, apple.com, wikipedia.org, mozilla.org) porque `/api/scan` valida que el dominio existe. El propio panel avisa arriba del todo si detecta la palabra DEMO en algún dato. **Hay que borrar estas filas antes de enseñarle el panel a nadie o de lanzar de verdad** — quedan mezcladas con las 5 solicitudes reales de las pruebas de hoy (ids 1-5, dominio `cristiyules.com`, email de Alberto) y con los ~68 escaneos de prueba acumulados en `escaneos`. Limpiar `pipo.db` en Railway (o las filas con "DEMO" y los ids de prueba conocidos) es una de las tareas de "preparar para producción", junto con activar Resend para el email.

### ✅ La propia web de Pipo aprueba su escáner (14 ago 2026): 71 → 87

El zapatero iba descalzo: `piposcan.vercel.app` sacaba **71/100 en rojo** en su propio Pipo. Lo
primero que hace un curioso (o un competidor) al ver la publicidad es escanear la web de Pipo, así
que era el mayor riesgo de credibilidad del lanzamiento. Ahora **87/100**, con 8 verdes / 2 ámbar /
1 rojo. Medido con dos escaneos reales contra producción, antes y después de desplegar.

- **`landing/vercel.json`, nuevo** (`headers` rojo → verde). Vercel no manda ninguna cabecera de
  seguridad por su cuenta salvo HSTS. La CSP es estricta de verdad porque el sitio se lo puede
  permitir: no hay `<img>`, ni iframes, ni `data:`, ni formularios que envíen fuera. Solo necesita
  `'unsafe-inline'` en `script-src`/`style-src` porque todo el CSS y el JS viven dentro del HTML —
  con hosting estático no hay forma de poner nonces, haría falta middleware.
  **Ojo: `vercel.json` es JSON estricto, no admite comentarios**; por eso se documenta aquí.
  **Cómo probar una CSP antes de desplegarla:** `python3 -m http.server` no manda cabeceras, así
  que en local todo parece funcionar y el fallo solo sale en producción. Se montó un servidor de
  15 líneas que lee las cabeceras del propio `vercel.json` y las aplica, y se hizo un escaneo
  completo de punta a punta con la CSP activa. Cero violaciones. Repetir eso si se toca la CSP.
- **Fuentes autohospedadas** (`landing/fonts/` + `landing/fonts.css`), `mixed_content` ámbar →
  verde. Arregla tres cosas de un golpe: el aviso de SRI (un `<link>` a un CDN ajeno es código de
  terceros con permiso para ejecutarse), la privacidad (la IP de cada visitante viajaba a Google) y
  la velocidad. Son **4 archivos, 204 KB**: Fraunces y Nunito son fuentes *variables*, así que un
  archivo cubre todos los pesos; solo se incluyen los subsets `latin` y `latin-ext`.
  **Efecto secundario que hubo que arreglar:** `cookies.html` declaraba que la web carga las fuentes
  desde Google. Al dejar de ser cierto, esa sección se reescribió — una página legal que miente es
  peor que el problema original.
- **Meta description** de `index.html`: 162 → 145 caracteres (`seo` ámbar → verde).

**Lo que sigue en rojo y por qué no es código:** `dns` (SPF/DMARC) sigue rojo, y con peso 2 en la
familia crítica "seguridad" eso basta para que el informe global siga en ROJO (decisión #2). Igual
`dominio` (CAA/DNSSEC) y `experiencia` (la variante `www.` no responde) en ámbar. **Los tres
dependen de registros DNS, y el DNS de un subdominio `.vercel.app` es de Vercel, no nuestro.** Se
cierran los tres al mover el sitio a un dominio propio, no antes. Con eso la nota sube a ~97-100.

Truco útil: la fórmula de `puntuacion.py` (`PESOS`) es determinista, así que **se puede calcular
qué nota dará un arreglo antes de hacerlo**. Se predijo el 87 exacto antes de tocar una línea.

### ✅ La landing ya no se arrastra de lado en el móvil (14 ago 2026)

Con `scrollWidth=422` contra `clientWidth=390` en un iPhone, la página se podía arrastrar de lado y
aparecía una franja vacía a la derecha. Sensación de web rota en el primer segundo, y el tráfico de
publicidad es sobre todo móvil. Verificado ahora en producción: **6 páginas × 6 anchos
(320/360/390/414/768/1024), cero arrastre**.

**Cómo medirlo, que es la mitad del trabajo.** `scrollWidth > clientWidth` **no** es el criterio:
da falsos positivos (un adorno que sobresale por la izquierda no genera scroll) y falsos negativos.
El criterio bueno es el del usuario: `window.scrollTo(9999, y)` y mirar si `window.scrollX` acaba
distinto de 0. Y **no usar `is_mobile=True` en Playwright**: aplica el "shrink to fit" de Chrome
(zoom out hasta que quepa todo) y esconde justo lo que se quiere medir. Además hay que recorrer la
página entera, porque los bloques `.reveal-*` están desplazados hasta que entran en pantalla.

Con ese criterio aparecieron **cuatro causas independientes**, no la que estaba apuntada:

1. Los `.reveal-left/right` (±56px en horizontal). El corte estaba en 880px, que tapaba el móvil
   pero dejaba rota cualquier pantalla **entre 881 y 1183px** (un iPad en horizontal). Ahora en
   1200px, con la cuenta escrita en el comentario del CSS.
2. **`min-width:auto` en items de grid y de flex** — la causa más repetida y la menos evidente.
   Significa "nunca más estrecho que mi contenido". En el hero lo fijaba el `<input>` del
   formulario (un input reserva de fábrica el ancho de ~20 caracteres → 340px de suelo); en las
   páginas legales, una tabla dentro de `<main>`, que es flex item por el patrón sticky footer.
   Se arregla con `min-width:0` **y `width:100%`** — solo con `min-width:0`, `<main>` seguía
   midiendo 568px dentro de un body de 320px.
3. `transform:rotate(20deg) translateY(var(--py))` en las hojas decorativas. **Como `rotate` va
   primero, el parallax vertical se aplicaba en el sistema de coordenadas ya girado** y movía la
   hoja también en horizontal al hacer scroll. Se arregla invirtiendo el orden de las funciones.
4. Halos decorativos con `width:340px` fijos, más anchos que un móvil de 320px → `min(340px,86vw)`.

**`overflow-x:hidden` en el body no vale como arreglo**: ya estaba puesto en `index.html` y NO
evitaba el arrastre (comprobado midiendo `scrollX`). Además rompe `position:sticky`.

De paso, la medición destapó desbordamientos que nadie había mirado en `privacidad.html` (la tabla
de datos tratados, que ahora tiene su propio scroll horizontal) y en `404.html`.

### ✅ Primer estudio de campo real: 38 negocios de Churriana y Alhaurín (16 ago 2026)

Encargo de Alberto: buscar negocios de Churriana y Alhaurín de la Torre con web, pasarlos por Pipo
y sacar un top de "los peores y más asequibles" para visitar. Se usó `herramientas/lote.py`, que
para esto es exactamente la herramienta buena (llama a `ejecutar_escaneo` en local, sin pasar por
`/api/scan`, así que no toca el consentimiento de titularidad).

**Selección de sectores, que es la mitad del trabajo:** solo negocios donde la web es un activo y
un fallo tiene consecuencias — gestorías, inmobiliarias, clínicas (dental/veterinaria), abogados,
informática, ingeniería, talleres, instaladores. Fuera peluquerías, bares y comercio pequeño: su
web no les da de comer. Hubo que filtrar a mano dos cosas que ensucian cualquier búsqueda de estas:
los **portales/directorios** (idealista, habitaclia, páginas amarillas) y las **granjas de landing
pages SEO** ("reformas en [pueblo]" de una empresa que no tiene oficina allí). Ojo también con que
**"Churriana de la Vega" es Granada**, no la Churriana de Málaga: varios resultados mezclan las dos.

**Resultado:** 38 webs, nota media 69/100, 87% con algún fallo grave (tras corregir los ocho falsos positivos que destapó el propio estudio). Informe publicado como
Artifact privado (`Ruta Churriana–Alhaurín`).

**Lo que el estudio le enseñó al producto, que vale más que la lista:**

- **`headers` sale en ROJO en la gran mayoría de las webs.** No es un hallazgo, es el estado normal de la
  pyme española. Como argumento de venta no distingue a nadie y suena a vendedor genérico. Lo que
  sí distingue: cifrado realmente roto (1 de 38) y páginas legales ausentes (42%).
- **Verificar a mano cambió el ranking dos veces.** La primera versión de la lista tenía tres de
  sus cinco primeros puestos mal, por fiarse de la nota sin contrastarla. De ahí salieron los dos
  bugs del `www` y de los banners de cookies (decisión #12 y `GESTORES_DE_COOKIES`). **Antes de
  poner un negocio delante de un cliente —o de Alberto— hay que comprobar el hallazgo con `curl`,
  `openssl` o `dig`.** El coste de acusar en falso es la venta entera.
- **Los resultados varían entre pasadas.** Alguna descarga trae la página a medias. Antes de una
  visita concreta, reescanear ese dominio solo.

**Aviso legal que hay que repetir cada vez que se retome esto:** escanear estas webs es legal
(Pipo solo mira lo que ve cualquier visitante), pero **mandarles después un email o un WhatsApp
comercial que no han pedido no lo es** — LSSI art. 21, sin excepción B2B en España, y la AEPD ha
sancionado por ello. Recoger sus datos de contacto públicos sí es legal; usarlos para comunicación
comercial en frío, no. La lista es para **presentarse en persona**, que no está regulado por esa
ley. Ver también el docstring de `herramientas/lote.py` y el punto 5.3 del `PIPO_PLANNING.md`.

### 🟡 P2 — Monetización (Fase 6 del planning)
- ✅ **Generador de PDF** con la marca de Pipo — hecho (11 ago 2026). Se eligió **WeasyPrint** sobre ReportLab (la otra opción que dejaba abierta el planning) porque compone el PDF a partir de HTML+CSS, reaprovechando el mismo lenguaje visual de la web en vez de maquetar cada elemento a mano. Detalles:
  - Endpoint `GET /api/informe/{id}/pdf` (ver tabla de endpoints arriba). Genera el informe interpretado si aún no estaba en caché (igual que `/api/informe`) y añade una sección de soluciones solo si `/soluciones` ya se había pedido antes para ese escaneo — no dispara ninguna llamada a la IA que no fuera a hacer falta de todos modos.
  - `app/pdf/generar_pdf.py` construye el HTML a mano (f-strings, no Jinja2 — es una sola plantilla, no compensa añadir esa dependencia) con los colores de marca, y usa fuentes genéricas (Georgia/Helvetica) en vez de Fraunces/Nunito **a propósito**: esas son fuentes de Google Fonts, y WeasyPrint tendría que descargarlas por red en cada PDF generado — una dependencia y una latencia que no compensan por una diferencia tipográfica menor.
  - **Railway necesita un archivo nuevo, `backend/railpack.json`**, con `deploy.aptPackages` para las librerías de sistema que pide WeasyPrint (Pango, Cairo, gdk-pixbuf, GLib) — sin él, el `import weasyprint` falla en producción aunque funcione en local (donde esas librerías ya estaban instaladas vía Homebrew). **Ojo, esto costó dos vueltas**: el primer intento fue un `nixpacks.toml` con `aptPkgs`, que es la config correcta para el builder **Nixpacks** — pero Railway ya no usa Nixpacks por defecto, usa su sucesor **Railpack** (se nota porque los build logs mencionan `mise`, no `nix`), que ignora `nixpacks.toml` por completo y sin avisar (build "exitoso", pero el archivo simplemente no se lee). Railpack usa `railpack.json` con dos listas separadas: `buildAptPackages` (solo durante el build) y `deploy.aptPackages` (en la imagen final que corre) — WeasyPrint carga estas librerías dinámicamente en tiempo de ejecución (vía `cffi`/`ctypes`), así que tienen que estar en `deploy.aptPackages`, no en `buildAptPackages`. Si algún día Railway cambia de builder otra vez, el síntoma para reconocerlo es el mismo: el archivo de config "no hace nada" sin ningún error, y hay que mirar qué build tool aparece en los logs.
  - `railpack.json` también fija `deploy.startCommand` explícitamente (mismo comando que `Procfile`) para no depender de si Railpack sigue leyendo `Procfile` o no — no se confirmó cuál de los dos manda, así que se puso en los dos sitios a propósito.
  - Frontend: nuevo botón "Descargar informe en PDF" en `informe.html`, dentro del mismo bloque `#detalle-difuminable` que ya estaba detrás del gate de email (ver captura de email más abajo) — **no está detrás de ningún pago todavía**, solo del email, igual que las soluciones y la velocidad. Cuando se añada Stripe (punto siguiente), decidir si el PDF pasa a requerir pago o se queda como parte de lo que desbloquea el email.
  - Probado con curl real en local y en Railway: PDF de 2-3 páginas (crece a 3 si ya hay soluciones cacheadas), contenido en español verificado extrayendo el texto del PDF con `pypdf`, `Content-Disposition: attachment` fuerza la descarga en el navegador en vez de abrirlo inline.
- 🟡 **Cobro manual por Bizum (en vez de Stripe)** — decisión tomada el 11 ago 2026: Alberto prefiere cobrar a mano por Bizum mientras no esté de alta como autónomo (ver conversación sobre Stripe vs. Lemon Squeezy/Paddle — Stripe es sencillo de programar, pero cobrar de verdad en España pide alta de autónomo/empresa, mismo bloqueante que el NIF pendiente en `aviso-legal.html`). **Estructura de niveles decidida** (sustituye el reparto "todo gratis tras email" del punto 5.2 de más abajo):
  - **Gratis tras email**: informe interpretado (hallazgos) + comprobación de velocidad.
  - **19€, Bizum**: soluciones paso a paso + PDF descargable. Precio elegido tras descartar cobrar solo por el PDF ("se ve tontería pagar solo por descargar un PDF" — palabras de Alberto) y decidir empaquetarlo con las soluciones.
  - **59-99€, contacto manual**: que Pipo aplique las soluciones él mismo. Precio **orientativo**, calculado con fórmula fija (nunca IA) en `puntuacion.py::calcular_precio_arreglo()` — base 59€ + puntos por dificultad real de cada check que no esté en verde (baja=3, media=8, alta=15), tope 99€. Se muestra en la pantalla de confirmación del pedido de 19€, con un `mailto:` a Alberto — no hay automatización de contacto todavía (ver más abajo).
  - Lo construido hoy: tabla `pedidos` (`app/database.py`) y endpoint `POST /api/pedidos` (ver tabla de endpoints arriba). Genera una `referencia` corta (`PIPOxx-YYYY`) para que Alberto identifique el Bizum entrante. El número de Bizum vive en `TELEFONO_BIZUM` (`.env` / Railway), no en el código — es un dato personal, se trata como una clave más.
  - ✅ **Rediseño "todo en privado" (11 ago 2026)** — Alberto no quería el Bizum ni la referencia a la vista de cualquiera en la web pública, ni tantos datos del caso en la página. Diseño final: el bloque `.accion-pago` ("¿Cómo lo arreglo?") solo enseña el precio (19€) y un botón "Pedir informe completo"; al pulsar pide **email + teléfono (opcional, para identificar el Bizum entrante)** y, al enviarlo, el diagnóstico completo (nota + checks a mejorar) y cómo pagar le llegan al cliente **por email, en privado** — no en la página. Alberto recibe un segundo email avisando del pedido nuevo (dominio, email/teléfono del cliente, referencia, precio orientativo del nivel superior) para poder hacer seguimiento manual.
    - Envío de email nuevo: `app/notificaciones/enviar.py` (función genérica `enviar_email`, por Gmail SMTP con una "contraseña de aplicación" — gratis, sin proveedor nuevo, de sobra para el volumen de esta fase) y `app/notificaciones/mensajes.py` (contenido de los dos emails, separado del envío igual que `interpretar.py` está separado de `cliente.py`). Nombrado `notificaciones/` y no `email/` a propósito: un paquete `app.email` habría podido dar problemas al importar el módulo `email` de la librería estándar de Python dentro de él.
    - Nueva columna `pedidos.telefono` (migración seguridad con `_asegurar_columna`, igual que las columnas de caché).
    - **Plan B si el email falla** (Gmail sin configurar, corte de red...): el endpoint devuelve `email_enviado: false`, y el frontend cae entonces a enseñar el Bizum y la referencia directamente en la página — mejor eso que dejar a alguien que ya ha pedido esto sin ninguna forma de pagar. Los dos envíos (cliente y Alberto) están en `try/except` independientes: que falle el aviso a Alberto nunca debe romper la respuesta al cliente.
    - **Pendiente de credenciales para activarse de verdad**: `GMAIL_EMAIL` y `GMAIL_APP_PASSWORD` (`.env` / Railway) — hasta que Alberto genere la contraseña de aplicación en `myaccount.google.com/apppasswords`, `email_enviado` será siempre `false` y todo el mundo verá el plan B (Bizum en la página), que sigue siendo funcional.
  - ✅ **Panel de pedidos + restricción real, hecho el mismo 11 ago 2026** (Alberto pidió pasar a otra tarea mientras conseguía la contraseña de Gmail, así que se completó esto en la misma sesión en vez de dejarlo pendiente):
    - `landing/pedidos.html?clave=...` — panel privado, protegido por una clave compartida (`CLAVE_ADMIN`, `.env`/Railway, comparada con `secrets.compare_digest` para evitar timing attacks), **no** es un sistema de usuarios de verdad, es un enlace secreto de uso personal. `<meta name="robots" content="noindex,nofollow">` para que no lo indexe Google. Lista todos los pedidos (email, teléfono, referencia, precio, estado); en los pendientes hay un botón "Marcar pagado", y en los ya pagados aparecen "Descargar PDF" (enlace directo, ya desbloqueado) y "Ver soluciones" (lo pide a la API y lo enseña en la propia página, en crudo — sin diseño, es una herramienta interna). La entrega final al cliente sigue siendo manual: Alberto copia/descarga esto y se lo reenvía él mismo por email desde su propio Gmail (no hay automatización de adjuntar el PDF al email de confirmación todavía).
    - Backend nuevo: `GET /api/pedidos?clave=` (lista) y `POST /api/pedidos/{id}/pagado?clave=` (marca pagado), ambos protegidos por `_verificar_clave_admin()`. Límite de 20/min en vez de 5/min — es Alberto recargando su propio panel, no tráfico público, y no cuesta cuota de IA.
    - **`/api/informe/{id}/soluciones` y `/api/informe/{id}/pdf` ahora sí están restringidos de verdad**: `database.py::existe_pedido_pagado(id_escaneo)` comprueba si hay algún pedido con `pagado=1` para ese escaneo; si no, `402 Payment Required`. El candado es por escaneo, no por email de quien pregunta — coherente con que Pipo nunca ha tenido cuentas de usuario.
    - Probado de punta a punta con curl real: `402` antes de pagar en ambos endpoints, `403` con clave incorrecta, `200` en ambos justo después de marcar pagado, `404` al marcar un id de pedido que no existe.
  - **Sobre el método de pago**: Alberto preguntó por algo tipo Apple Pay/tarjeta con un toque — eso es Stripe Checkout, pero cobrar de verdad con Stripe en España pide alta de autónomo (igual que arriba). De momento el email al cliente ofrece Bizum como vía principal y "contesta a este email" como vía manual para tarjeta/PayPal, sin cerrar la puerta a integrar Stripe Checkout más adelante.
- 🟡 **Google Analytics — pendiente de verdad, no descartado** (confirmado explícitamente por Alberto el 11 ago 2026: "lo haremos pero apúntalo en cosas pendientes"). Se planteó al hacer el repaso de SEO/marca de la web y se dejó fuera *ese día* solo porque instalarlo bien exige dos cosas que no estaban listas: 1) una propiedad de GA4 creada en analytics.google.com (necesita el ID de medición `G-XXXXXXX`, que Alberto tiene que generar, no se puede inventar), y 2) un banner de consentimiento real — en la UE una cookie de analytics no puede cargar antes de que el visitante acepte (LSSI/RGPD), así que no basta con pegar el script de gtag.js sin más. Cuando se retome: pedir el ID a Alberto, montar el banner (aceptar/rechazar, cargar gtag.js solo tras aceptar), y actualizar `cookies.html`/`privacidad.html` para declarar las cookies `_ga`/`_ga_*` de verdad (hoy dicen explícitamente "solo Google Fonts, nada de analítica" — quedaría desactualizado en cuanto se instale).
- ✅ **Captura de email** — hecho (11 ago 2026, punto 5.2 del planning), pasó por **dos diseños** antes del definitivo (ver los porqués abajo — no repetir ninguno de los dos pasos intermedios sin releer esto). **Diseño final**: el semáforo completo (los 7 checks) se enseña siempre en `index.html`, sin pedir nada — es el gancho que demuestra que hay problemas de verdad. En `informe.html`, el informe **se genera siempre** (la cabecera con dominio/nota/resumen de la IA se ve siempre), pero el detalle — hallazgos uno a uno + las acciones de velocidad/soluciones — sale **difuminado** (`filter:blur()`) con una tarjeta flotante encima pidiendo el email para desbloquearlo.
  - **Primer diseño descartado** (difuminar 4 de 7 checks en la propia `index.html`): Alberto vio el riesgo de que ocultar resultados en crudo generase desconfianza y espantase visitas en vez de convertirlas — mejor enseñar todo el diagnóstico gratis (crea la urgencia de "tengo 3 críticos") y cobrar la puerta de entrada por la parte que sí cuesta generar (la IA).
  - **Segundo diseño descartado** (pedir el email en `informe.html` *antes* de llamar a `/api/informe`, con una tarjeta de bloqueo previa a cualquier contenido): ahorraba cuota de IA a cambio de peor conversión — Alberto prefirió enseñar el informe ya generado (aunque difuminado) porque genera más curiosidad/FOMO que una tarjeta vacía pidiendo el email sin haber demostrado nada todavía. **Contrapartida asumida a propósito**: la llamada a `/api/informe` (cuota de Gemini) se dispara en cuanto se abre `informe.html`, la ha dejado o no el email — ya no hay ahorro de cuota por no convertir. Si la cuota vuelve a ser un problema real, el primer sitio donde mirar es aquí.
  - Backend: endpoint `POST /api/leads?email=&dominio=&id_escaneo=`, validación ligera de formato de email (regex, no RFC completo), comprueba que el `id_escaneo` existe, guarda en tabla `leads` (sin FOREIGN KEY hacia `escaneos` a propósito, para no perder el lead si algún día se limpian escaneos antiguos). Mismo límite de 5/minuto por IP que el resto de endpoints "de escritura".
  - Frontend (`informe.html`): `cargarInforme()` se llama siempre al entrar. Dentro de `pintarInforme()`, si no hay email guardado para ese escaneo (`localStorage`, clave `pipo_desbloqueado_<id>`), se añade la clase `difuminado` al contenedor `#detalle-difuminable` (hallazgos + acciones) y se inyecta la tarjeta flotante (`#capa-desbloqueo-informe`, `position:sticky` para que seguir bajando la página no la pierda de vista). Al enviar el email con éxito, se quita la clase y se oculta la tarjeta — sin volver a pedir nada al backend, los datos ya estaban en memoria. La casilla de consentimiento (`check-consiento-lead`) es **distinta** de la de titularidad del dominio del punto P0 — esta es específica para que Pipo pueda contactar sobre el informe/sus servicios.
  - `index.html` quedó igual que estaba antes de tocar nada (7 filas, sin bloqueo); el bullet de la tarjeta "Vistazo" en precios se corrigió a "Semáforo de las 7 comprobaciones" (antes decía "3 comprobaciones clave", que ya no era cierto).
  - `privacidad.html` actualizado: nueva fila en la tabla de datos tratados, base legal de consentimiento expreso (art. 6.1.a RGPD) para el email, y mención del derecho a retirarlo en la sección de derechos.
  - `informe.html`: el `nav` pasó de mostrar el búho + "Pipo" a mostrar **"← Pipo"** (enlace de vuelta al inicio, sin icono) a la izquierda y **"Informe"** como título de página a la derecha de la misma franja — ya no hay una cabecera de página aparte debajo del nav.
  - **Footer pegado al contenido, arreglado en las 4 páginas que lo tenían** (`informe.html`, `aviso-legal.html`, `cookies.html`, `privacidad.html`): la causa real no era poco padding, era que solo `informe.html` tenía el patrón "sticky footer" (`html,body{height:100%}` + `body{min-height:100vh;display:flex;flex-direction:column}` + `main{flex:1 0 auto}` + `footer{flex-shrink:0}`) — las otras tres solo tenían un padding-bottom fijo en `<main>`, así que con poco contenido el footer quedaba pegado justo debajo del texto en vez de asentarse abajo del todo. Se les añadió el mismo patrón de `informe.html`.
  - Probado con Playwright real, de punta a punta: `index.html` enseña las 7 filas sin formulario; al entrar en `informe.html` sin haber dejado email antes, aparece el bloqueo y la IA no se llama todavía; tras enviar el email, se ve el estado de carga y luego el informe real (Gemini respondió de verdad, no un mock); recargar la página del mismo escaneo con el `localStorage` ya puesto salta el bloqueo directamente.
  - Probado con Playwright real: el formulario aparece y el link al informe está oculto antes de dejar el email; tras enviarlo, las 7 filas se ven y el lead queda guardado en `pipo.db` (comprobado por SQL directo). También probado el límite de 5/minuto y los casos de email inválido (400) y escaneo inexistente (404).

### 🟢 P3 — Crecimiento, más adelante
- **Nivel "Vigilancia" (19€/mes)**: re-escaneo automático mensual, comparación con el histórico ("esto ha empeorado desde la última vez"), alertas por email. Necesita tareas programadas (cron/Celery) que hoy no existen.
- **HIBP**, pero solo dentro del futuro servicio de "acompañamiento" manual (ver decisión #4 arriba) — nunca en el flujo self-service.
- Volver a intentar el pago con Anthropic si se resuelve el problema de la tarjeta, y plantearse si migrar la capa de IA de Gemini a Claude (calidad de escritura en español, mejor seguimiento de instrucciones anti-alucinación).

---

## Cosas para tener en cuenta al seguir trabajando

- **Sigue construyendo en trozos pequeños y explicando el qué/por qué** — es una preferencia explícita del usuario, no solo un estilo por defecto.
- **Prueba siempre con curl/requests reales antes de dar algo por terminado** — así se detectaron y arreglaron ya varios bugs reales (fallo del resolver DNS local, modelo de Gemini deprecado, proceso zombi en el puerto 8000, latencia de IA, y la cuota diaria de 20 peticiones del plan gratuito de Gemini — ver P1).
- ✅ **Resuelto (11 ago 2026):** `gemini-3.5-flash` en plan gratuito tenía cuota de solo 20 peticiones/día (se descubrió el 10 ago 2026), lo que tumbaba `/api/informe` y `/soluciones` con `502` en cuanto se agotaba. Se cambió el proveedor de IA a Claude (Anthropic) — ver decisión #5. Si algún día se vuelve a Gemini, recordar esta limitación.
- **Nunca borres `pipo.db` para probar una migración** — cópialo primero (`cp pipo.db pipo.db.bak` o pruébalo contra una copia en otro path) y prueba ahí. El 10 ago 2026 se borró el `pipo.db` de desarrollo sin querer al probar la migración de las columnas de caché desde cero; no se perdió nada importante (solo escaneos de prueba), pero fue un descuido que no debería repetirse.
- El punto **5.3 del `PIPO_PLANNING.md`** ("auditoría sorpresa enviada en frío por email") es **legalmente arriesgado** (LSSI, sin excepción B2B en España) — si se retoma el planning original, hay que avisar de esto otra vez o reescribir ese punto.
- La landing (`index.html`) también existe publicada como Artifact de Claude (una copia estática, sin backend real detrás — solo para enseñar el diseño). No confundir esa copia con el sitio real en desarrollo.
