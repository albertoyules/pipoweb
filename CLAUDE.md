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
    ├── nixpacks.toml             → librerías de sistema (Pango/Cairo) que necesita WeasyPrint en Railway
    ├── pipo.db                   → SQLite con historial de escaneos (tampoco se sube a git)
    └── app/
        ├── main.py                → todos los endpoints FastAPI
        ├── config.py               → lee .env (claves de Anthropic, Gemini y PageSpeed)
        ├── database.py              → guardar/leer escaneos en SQLite
        ├── scanner.py                → orquestador: lanza todos los checks en paralelo
        ├── puntuacion.py              → nota 0-100, calculada por FÓRMULA FIJA, nunca por la IA
        ├── checks/
        │   ├── pagina.py                → descarga compartida de la home (evita pedir la misma página 3 veces)
        │   ├── ssl_check.py              → verde
        │   ├── headers_check.py           → verde
        │   ├── dns_check.py                → verde (SPF/DKIM/DMARC)
        │   ├── seo_check.py                 → verde
        │   ├── privacidad_check.py           → verde (aviso legal/cookies/trackers)
        │   ├── mixed_content_check.py         → verde
        │   ├── tecnologia_check.py             → verde (CMS desactualizado)
        │   ├── rendimiento_check.py            → verde, opt-in (PageSpeed, móvil+ordenador, 4 categorías cada uno)
        │   └── archivos_expuestos.py            → ÁMBAR, opt-in solo con consentimiento
        ├── ia/
        │   ├── cliente.py               → envoltorio del proveedor de IA (hoy Claude/Anthropic — ver nota abajo)
        │   ├── interpretar.py            → botón 1: hallazgos en lenguaje llano
        │   └── soluciones.py              → botón 2: soluciones + nota estimada tras aplicarlas
        └── pdf/
            └── generar_pdf.py             → informe de marca en PDF (WeasyPrint), reaprovecha informe+soluciones ya cacheados
```

No hay `__init__.py` en ningún paquete — funciona porque Python 3.3+ soporta "namespace packages" implícitos. No hace falta añadirlos.

---

## Endpoints de la API

| Endpoint | Qué hace | Notas |
|---|---|---|
| `GET /health` | Salud del servidor | — |
| `GET /check/{ssl,headers,dns,seo,privacidad,mixed-content,archivos-expuestos,rendimiento}?dominio=` | Cada check por separado | Utilidades de depuración, sin rate limit |
| `GET /api/scan?dominio=&consiento=&incluir_rendimiento=` | Orquesta todos los checks en paralelo, guarda en DB | **Rate limited: 5/min por IP.** `consiento=true` activa `archivos_expuestos`; `incluir_rendimiento=true` añade PageSpeed (+10-15s) |
| `GET /api/scan/{id}` | Recupera un escaneo guardado | — |
| `GET /api/scan/{id}/rendimiento` | Audita velocidad (PageSpeed) del dominio de ese escaneo | Rate limited 5/min. **Cacheado** en `rendimiento_json`; sustituye al uso directo de `/check/rendimiento?dominio=` desde `informe.html` |
| `GET /api/informe/{id}` | Hallazgos interpretados por IA + nota (determinista) | Rate limited 5/min. **Cacheado** en `informe_json` — la 2ª petición para el mismo escaneo no vuelve a llamar a Gemini |
| `POST /api/informe/{id}/soluciones` | Soluciones + nota estimada tras aplicarlas | Es POST a propósito (dispara gasto de IA cada vez, no debe cachear el navegador). Rate limited 5/min. **Cacheado** en `soluciones_json` |
| `GET /api/informe/{id}/pdf` | Informe en PDF con marca Pipo (`app/pdf/generar_pdf.py`) | Rate limited 5/min. Genera el informe si no estaba cacheado (igual que `/api/informe`); incluye soluciones solo si ya se pidieron antes. No usa fuentes de marca (Fraunces/Nunito) a propósito, para no depender de una descarga de red en cada PDF |

---

## Decisiones de diseño ya tomadas (no las repitas ni las cuestiones sin motivo)

1. **La nota (0-100) nunca la calcula la IA** — la calcula `puntuacion.py` con una fórmula fija (verde=100, ámbar=60, rojo=20, media). Es determinista y reproducible a propósito, para que la IA no pueda "inventar" una puntuación. La IA solo pone el texto explicativo.
2. **El peor check manda en el semáforo global** (`scanner.py::_resumir`) — no se promedia, un solo rojo tira todo el resumen a rojo. Es intencionado: en seguridad, el eslabón débil pesa más que la media.
3. **`archivos_expuestos` es el único check ámbar**, apagado por defecto en `/api/scan`, solo se activa con `consiento=true`. Nunca debe entrar en el escaneo gratis.
4. **HIBP (Have I Been Pwned) está aparcado** — su API exige verificar la propiedad del dominio antes de consultarlo, lo cual no encaja con escanear dominios de terceros en self-service. Solo tendría sentido en el futuro nivel "Pipo + acompañamiento" (servicio manual, el cliente coopera).
5. ✅ **La capa de IA está desacoplada del proveedor** (`app/ia/cliente.py`) — el 11 ago 2026 se resolvió el problema de pago y se cambió de Google Gemini a **Claude (Anthropic)**, precisamente para dejar atrás la cuota gratuita de Gemini (ver P1 más abajo). El cambio solo tocó ese archivo — `interpretar.py` y `soluciones.py` no saben qué proveedor hay detrás, tal y como estaba pensado. `GOOGLE_GEMINI_API_KEY` se deja en `config.py` y en las variables de Railway sin usar, por si algún día hiciera falta volver atrás; `google-genai` se queda en `requirements.txt` por la misma razón.
6. **Modelo de Claude en uso:** `claude-haiku-4-5-20251001` (ver `app/ia/cliente.py`) — elegido por precio sobre `claude-sonnet-5` dado el volumen bajo de peticiones por escaneo (máximo 2, informe + soluciones, gracias a la caché del punto P1). Si la calidad de redacción no convence, el candidato a probar es `claude-sonnet-5`, más caro pero con mejor pluma en español.
7. **El botón "soluciones" es un segundo paso deliberadamente separado** del informe interpretado — no todo el que ve el diagnóstico quiere ya los pasos técnicos, y deja la puerta abierta a que sea una función de pago aparte del informe básico.
8. ✅ **CORS restringido** (10 ago 2026) — ya no es `allow_origins=["*"]`. Con el backend en Railway (internet real) y la cuota de Gemini tan ajustada, dejarlo abierto permitía que cualquier página web disparase peticiones a la API desde el navegador de cualquier visitante. Hoy permite `http://127.0.0.1:5500` y `http://localhost:5500` (desarrollo local) y `https://piposcan.vercel.app` (la landing real, añadida el 10 ago 2026). Si algún día la landing cambia de dominio, hay que añadirlo aquí **y hacer `git push`** — si no, el navegador bloquea todas las llamadas a la API y la landing parece rota sin dar error claro.

---

## Qué falta por hacer, con prioridad

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

### 🟡 P2 — Monetización (Fase 6 del planning)
- ✅ **Generador de PDF** con la marca de Pipo — hecho (11 ago 2026). Se eligió **WeasyPrint** sobre ReportLab (la otra opción que dejaba abierta el planning) porque compone el PDF a partir de HTML+CSS, reaprovechando el mismo lenguaje visual de la web en vez de maquetar cada elemento a mano. Detalles:
  - Endpoint `GET /api/informe/{id}/pdf` (ver tabla de endpoints arriba). Genera el informe interpretado si aún no estaba en caché (igual que `/api/informe`) y añade una sección de soluciones solo si `/soluciones` ya se había pedido antes para ese escaneo — no dispara ninguna llamada a la IA que no fuera a hacer falta de todos modos.
  - `app/pdf/generar_pdf.py` construye el HTML a mano (f-strings, no Jinja2 — es una sola plantilla, no compensa añadir esa dependencia) con los colores de marca, y usa fuentes genéricas (Georgia/Helvetica) en vez de Fraunces/Nunito **a propósito**: esas son fuentes de Google Fonts, y WeasyPrint tendría que descargarlas por red en cada PDF generado — una dependencia y una latencia que no compensan por una diferencia tipográfica menor.
  - **Railway necesita un archivo nuevo, `backend/nixpacks.toml`**, con `aptPkgs` para las librerías de sistema que pide WeasyPrint (Pango, Cairo, gdk-pixbuf) — sin él, el `import weasyprint` fallaría en producción aunque funcione en local (donde esas librerías ya estaban instaladas vía Homebrew). Es un archivo de configuración de Nixpacks, no de la app; Railway lo recoge solo al hacer build si vive en el mismo directorio que `requirements.txt` (con el Root Directory puesto a `backend`, como ya estaba).
  - Frontend: nuevo botón "Descargar informe en PDF" en `informe.html`, dentro del mismo bloque `#detalle-difuminable` que ya estaba detrás del gate de email (ver captura de email más abajo) — **no está detrás de ningún pago todavía**, solo del email, igual que las soluciones y la velocidad. Cuando se añada Stripe (punto siguiente), decidir si el PDF pasa a requerir pago o se queda como parte de lo que desbloquea el email.
  - Probado con curl real en local y en Railway: PDF de 2-3 páginas (crece a 3 si ya hay soluciones cacheadas), contenido en español verificado extrayendo el texto del PDF con `pypdf`, `Content-Disposition: attachment` fuerza la descarga en el navegador en vez de abrirlo inline.
- **Pasarela de pago (Stripe)** para el informe one-shot — siguiente paso de P2. Ver conversación sobre Stripe vs. Lemon Squeezy/Paddle (Merchant of Record): Stripe es sencillo de programar, pero cobrar de verdad en España pide estar dado de alta como autónomo/empresa (mismo bloqueante que el NIF pendiente en `aviso-legal.html`); se puede desarrollar en modo test sin ese papeleo.
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
