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
    ├── pipo.db                   → SQLite con historial de escaneos (tampoco se sube a git)
    └── app/
        ├── main.py                → todos los endpoints FastAPI
        ├── config.py               → lee .env (claves de Gemini y PageSpeed)
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
        │   ├── rendimiento_check.py            → verde, opt-in (PageSpeed, móvil+ordenador, 4 categorías cada uno)
        │   └── archivos_expuestos.py            → ÁMBAR, opt-in solo con consentimiento
        └── ia/
            ├── cliente.py               → envoltorio del proveedor de IA (hoy Gemini — ver nota abajo)
            ├── interpretar.py            → botón 1: hallazgos en lenguaje llano
            └── soluciones.py               → botón 2: soluciones + nota estimada tras aplicarlas
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

---

## Decisiones de diseño ya tomadas (no las repitas ni las cuestiones sin motivo)

1. **La nota (0-100) nunca la calcula la IA** — la calcula `puntuacion.py` con una fórmula fija (verde=100, ámbar=60, rojo=20, media). Es determinista y reproducible a propósito, para que la IA no pueda "inventar" una puntuación. La IA solo pone el texto explicativo.
2. **El peor check manda en el semáforo global** (`scanner.py::_resumir`) — no se promedia, un solo rojo tira todo el resumen a rojo. Es intencionado: en seguridad, el eslabón débil pesa más que la media.
3. **`archivos_expuestos` es el único check ámbar**, apagado por defecto en `/api/scan`, solo se activa con `consiento=true`. Nunca debe entrar en el escaneo gratis.
4. **HIBP (Have I Been Pwned) está aparcado** — su API exige verificar la propiedad del dominio antes de consultarlo, lo cual no encaja con escanear dominios de terceros en self-service. Solo tendría sentido en el futuro nivel "Pipo + acompañamiento" (servicio manual, el cliente coopera).
5. **La capa de IA está desacoplada del proveedor** (`app/ia/cliente.py`) — hoy usa Google Gemini (gratis, sin tarjeta) en vez de Claude/Anthropic porque hubo problemas de pago con la tarjeta del usuario (rechazos repetidos, sin resolver a fecha de este documento). Si se resuelve el pago y se quiere cambiar a Claude, **solo hay que tocar ese archivo**, el resto de la IA (`interpretar.py`, `soluciones.py`) no sabe qué proveedor hay detrás.
6. **Modelo de Gemini en uso:** `gemini-3.5-flash` (ver `app/ia/cliente.py`). Los nombres de modelo de Google cambian con frecuencia — si un día da 404 "modelo no disponible", volver a listar modelos disponibles con `cliente.models.list()` antes de adivinar un nombre nuevo (así se resolvió la primera vez).
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
> **Pero sigue habiendo un bloqueante para enseñárselo a gente de verdad: la cuota de Gemini (20 peticiones/día).** No es una tarea de P1 sino una decisión de proveedor de IA — ver el punto de abajo y la decisión #5. Mientras no se resuelva, el informe con IA se cae con `502` en cuanto lo usen unas pocas personas.
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
- **Generador de PDF** con la marca de Pipo (WeasyPrint o ReportLab, según planning) — el informe completo de pago (59€) necesita un entregable descargable, no solo una página web.
- **Pasarela de pago (Stripe)** para el informe one-shot.
- **Captura de email** antes de enseñar el resultado completo en el escaneo gratis (punto 5.2 del planning) — hoy el escaneo gratis enseña todo sin pedir nada a cambio, no nutre ninguna lista de leads.

### 🟢 P3 — Crecimiento, más adelante
- **Nivel "Vigilancia" (19€/mes)**: re-escaneo automático mensual, comparación con el histórico ("esto ha empeorado desde la última vez"), alertas por email. Necesita tareas programadas (cron/Celery) que hoy no existen.
- **HIBP**, pero solo dentro del futuro servicio de "acompañamiento" manual (ver decisión #4 arriba) — nunca en el flujo self-service.
- Volver a intentar el pago con Anthropic si se resuelve el problema de la tarjeta, y plantearse si migrar la capa de IA de Gemini a Claude (calidad de escritura en español, mejor seguimiento de instrucciones anti-alucinación).

---

## Cosas para tener en cuenta al seguir trabajando

- **Sigue construyendo en trozos pequeños y explicando el qué/por qué** — es una preferencia explícita del usuario, no solo un estilo por defecto.
- **Prueba siempre con curl/requests reales antes de dar algo por terminado** — así se detectaron y arreglaron ya varios bugs reales (fallo del resolver DNS local, modelo de Gemini deprecado, proceso zombi en el puerto 8000, latencia de IA, y la cuota diaria de 20 peticiones del plan gratuito de Gemini — ver P1).
- **`gemini-3.5-flash` en plan gratuito tiene cuota de solo 20 peticiones/día** por proyecto (se descubrió el 10 ago 2026 al agotarla en pruebas normales de sesión). Cualquier prueba manual con curl/scripts durante una sesión de trabajo cuenta para esa cuota — si `/api/informe` o `/soluciones` empiezan a dar `502` sin motivo aparente, mirar esto antes que nada.
- **Nunca borres `pipo.db` para probar una migración** — cópialo primero (`cp pipo.db pipo.db.bak` o pruébalo contra una copia en otro path) y prueba ahí. El 10 ago 2026 se borró el `pipo.db` de desarrollo sin querer al probar la migración de las columnas de caché desde cero; no se perdió nada importante (solo escaneos de prueba), pero fue un descuido que no debería repetirse.
- El punto **5.3 del `PIPO_PLANNING.md`** ("auditoría sorpresa enviada en frío por email") es **legalmente arriesgado** (LSSI, sin excepción B2B en España) — si se retoma el planning original, hay que avisar de esto otra vez o reescribir ese punto.
- La landing (`index.html`) también existe publicada como Artifact de Claude (una copia estática, sin backend real detrás — solo para enseñar el diseño). No confundir esa copia con el sitio real en desarrollo.
