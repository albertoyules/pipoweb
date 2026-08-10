# Pipo — Planning maestro

> **"¿Dudas de tu web? Pipo te la revisa y te informa."**
> Analizador de webs para pymes: un personaje que audita tu presencia online (seguridad básica, RGPD, SEO técnico, rendimiento) sin tocar nada de tu servidor, y te entrega un informe que entiendes.

Este documento es el mapa de todo el proyecto. Está pensado para que lo abras en Cursor y vayas ejecutando fase por fase, aprendiendo mientras construyes. No es código: es el "qué hay que hacer y por qué".

---

## 0. Decisiones de arranque (cerrar antes de la primera línea de código)

- **Nombre:** Pipo = este producto (analizador de webs). Si el producto de reseñas QR sigue vivo, renómbralo para no colisionar en marca/dominio.
- **Alcance legal v1:** SOLO reconocimiento pasivo. Cero escaneo activo, cero pentesting, cero Strix en el flujo público. Esto no es una limitación técnica: es el núcleo de tu propuesta de valor ("Pipo mira tu web como la ve Google, sin entrar en tus sistemas").
- **Idioma:** español primero. i18n preparado en estructura pero sin traducir aún.
- **Un solo fundador:** cada decisión técnica se juzga por "¿esto lo puedo mantener yo solo sin que se convierta en un segundo trabajo?".
- **Dominio:** comprar `pipo.*` disponible (pipoweb, piporevisa, holapipo... comprobar). Reservar handle social igual en todas las redes.

---

## 1. Qué es Pipo y qué NO es

**Es:** un servicio que, a partir de un dominio, ejecuta una batería de comprobaciones 100% pasivas (información pública, lo que cualquier navegador o buscador ve) y genera un informe con semáforo de riesgos + explicaciones en lenguaje llano + recomendaciones priorizadas.

**No es:** un pentester automático, un escáner de vulnerabilidades intrusivo, ni una herramienta que "entra" en sistemas ajenos. Esa línea es legal (art. 197 bis CP) y también de producto: Pipo vende tranquilidad, no ataque.

**El personaje Pipo:** mascota/dibujo simpático (búho o zorro otoñal encajan con la paleta) que "revisa" la web. Aparece en hero, en estados de carga (Pipo "mirando" con lupa), en el informe (Pipo te explica cada hallazgo), en emails. Le da carácter y hace accesible un tema árido para el dueño de una peluquería.

---

## 2. Qué ofrece a los clientes (catálogo de checks — el corazón del producto)

Todos pasivos. Agrupados en 5 categorías con semáforo verde/ámbar/rojo:

### Seguridad básica
- Certificado SSL: válido, caducidad, protocolo TLS.
- Cabeceras de seguridad HTTP (HSTS, X-Frame-Options, CSP, X-Content-Type-Options...).
- Versión de CMS/tecnología expuesta en el HTML (WordPress desactualizado, etc.).
- Archivos sensibles expuestos por error públicamente (`/.env`, `/.git/`, backups `.bak`, `/wp-config.php.bak`). — documentar como "exposición pública", nunca como "ataque".
- Mixed content (recursos http en web https).

### Privacidad y cumplimiento (RGPD/LSSI)
- ¿Existe aviso legal, política de privacidad y política de cookies?
- ¿Hay banner de cookies antes de cargar terceros?
- Detección de trackers de terceros (Analytics, Meta Pixel...) y si se cargan sin consentimiento.
- Formularios: ¿mandan datos por HTTPS? ¿tienen checkbox de consentimiento?

### Reputación de dominio / email
- Registros SPF, DKIM, DMARC (protección anti-suplantación en phishing).
- Dominio en brechas conocidas (API Have I Been Pwned a nivel dominio).

### SEO técnico
- Meta title y description presentes y con longitud razonable.
- Etiquetas Open Graph (cómo se ve al compartir en WhatsApp/redes).
- `robots.txt` y `sitemap.xml` presentes.
- Datos estructurados (schema.org) presentes o ausentes.
- Encabezados H1 únicos, alt en imágenes.

### Rendimiento y experiencia
- Peso de la página, tiempo de carga aproximado.
- ¿Responsive / mobile-friendly?
- Integrar Google PageSpeed Insights API (gratuita) para Core Web Vitals.

> **El entregable que se vende no es la lista de checks: es el INFORME.** La IA (capa de interpretación) coge estos datos crudos y los traduce a "esto significa X para tu negocio, arréglalo así, prioridad alta/media/baja". Ahí está tu margen.

---

## 3. Niveles de producto y monetización

| Nivel | Qué es | Precio orientativo | Modelo |
|---|---|---|---|
| **Escaneo gratis (lead magnet)** | 3-4 checks básicos + nota global, en la propia web. Gancho de captación. | 0 € | Genera el lead (pide email para informe completo) |
| **Informe completo (one-shot)** | Todos los checks + PDF interpretado por IA + recomendaciones priorizadas | 49–99 € | Pago único |
| **Revisión recurrente** | Re-escaneo mensual + alertas si algo empeora (SSL caduca, cae la web, aparece en brecha) + histórico | 15–29 €/mes | Suscripción (MRR) |
| **Pipo + acompañamiento** | Informe + tú aplicas/coordinas las correcciones (aquí enlazas con tu servicio de webs) | Presupuesto | Servicio, ticket alto |

**Lógica de negocio:** el gratis capta, el one-shot valida que pagan, la suscripción construye MRR, el acompañamiento es donde de verdad monetizas tu tiempo y conecta con lo que ya haces (landing pages, arreglar webs). Encaja con Kit Digital como canal: si el informe detecta que necesitan "backup gestionado" o "web nueva", puedes derivar a soluciones subvencionables como agente digitalizador.

**Cuánto esperar realista (primeros 3-6 meses, tú solo, compaginando):** unos pocos informes al mes + un puñado de suscripciones = varios cientos de €/mes con mantenimiento casi nulo. No es hacerse rico; es "dinerillo defendible" + activo de CV brutal.

---

## 4. Perfil de cliente objetivo (a quién vender)

**Verde (ataca primero):**
- Negocios locales con web propia reciente y ganas de crecer (no el de toda la vida por boca a boca).
- Sectores con web transaccional o de captación real: reformas, clínicas dentales/estética, hostelería con reservas, inmobiliarias pequeñas, talleres, comercios con tienda online modesta.
- Negocios con web claramente rota/anticuada (SSL caducado, no responsive) — el informe se vende solo.
- Los que ya manejan datos de clientes (formularios, reservas) → el ángulo RGPD les toca por ley.

**Ámbar (más adelante):**
- Autónomos con web muy básica (ticket bajo, pero volumen).
- Negocios en crecimiento que empiezan a preocuparse por cumplimiento (NIS2 les suena).

**Rojo (evita al principio):**
- Grandes empresas con su propio equipo IT (ciclo de venta largo, no eres competitivo aún).
- Negocios sin web ninguna (no hay nada que Pipo revise — a esos les vendes web, no Pipo).

**Tu ventaja de acceso:** ya haces cold-visits en Málaga (Churriana/Alhaurín). Pipo es un add-on natural a esa ruta: entras con "te reviso la web gratis en 2 min" (el escaneo gratis en tu móvil/tablet delante del dueño) y de ahí subes al informe.

---

## 5. Cómo acceder a clientes (go-to-market)

1. **Cold-visit con demo en vivo:** llevas Pipo en el móvil, metes su dominio delante del dueño, sale el semáforo con 2-3 rojos → gancho emocional inmediato. Es tu canal más fuerte porque ya lo tienes montado.
2. **Escaneo gratis en la web como imán de leads:** cualquiera mete su dominio, ve un adelanto, deja email para el informe completo. Alimenta una lista.
3. **Auditoría "sorpresa" enviada en frío:** corres el escaneo pasivo de un negocio (legal, es info pública), le mandas por email/WhatsApp los 3 hallazgos top con Pipo → "¿quieres el informe completo?".
4. **Kit Digital / agente digitalizador:** canal institucional para derivar soluciones subvencionables detectadas en el informe.
5. **Contenido:** LinkedIn/Instagram mostrando "Pipo revisa la web de X y encuentra Y" (con permiso o anonimizado). Tu hermana Cristy (UGC) puede ayudarte con formato.
6. **Malt/Upwork:** empaquetar "auditoría web exprés" como servicio.

---

## 6. Marca y ámbito visual

**Concepto:** Pipo es cálido, cercano, otoñal. Transmite "un amigo experto que te echa un cable", no "consultora de ciberseguridad con corbata". El tema es árido; el personaje y el color lo hacen amable.

**Paleta otoñal (marrón clarito como principal):**
- Fondo crema cálido: `#F5EFE6`
- Marrón principal (Pipo): `#B08968`
- Marrón oscuro (texto/acento): `#6F4E37`
- Terracota (CTA/alertas cálidas): `#C97B5A`
- Verde salvia (semáforo OK / naturaleza otoñal): `#8A9A5B`
- Ámbar/mostaza (semáforo aviso): `#D9A441`
- Rojo teja (semáforo crítico, sobrio no chillón): `#B34733`

**Tipografía:**
- Display con carácter y calidez (redondeada, amable) para titulares y nombre Pipo.
- Body legible y neutra para el contenido del informe (tiene que leerse bien en PDF).

**El personaje Pipo:** un búho o zorro otoñal (mi voto: búho — "sabio que vigila/revisa", encaja con lupa e informe). Versiones: mirando con lupa (carga), señalando hallazgos (informe), saludando (hero), pulgar arriba (todo OK). Empieza con SVG simple; puedes iterar el diseño más tarde.

**Estados con personalidad:** carga = "Pipo está revisando tu web..." con animación de lupa; vacío/error = Pipo confundido con mensaje claro de qué pasó; éxito = Pipo contento.

---

## 7. Arquitectura técnica (v1, mantenible por una persona)

```
[ Navegador ]
     │  dominio + consentimiento
     ▼
[ Frontend ]  landing + formulario + vista de informe
     │  POST /api/scan
     ▼
[ Backend API (FastAPI) ]
     │  lanza checks en paralelo (asyncio)
     ├── módulo ssl        ├── módulo headers
     ├── módulo dns        ├── módulo rgpd
     ├── módulo seo        ├── módulo archivos_expuestos
     ├── módulo brechas (HIBP)   └── módulo rendimiento (PageSpeed API)
     │
     ▼  datos crudos (JSON)
[ Capa IA ]  interpreta y prioriza → texto llano por hallazgo
     │
     ▼
[ Base de datos ]  guarda escaneo + resultado (SQLite v1)
     │
     ├──> vista web del informe (semáforo)
     └──> generador de PDF (informe descargable de marca Pipo)
```

**Stack recomendado (elige lo que ya conoces para aprender sin fricción extra):**
- **Backend:** Python + **FastAPI** (async nativo, ideal para lanzar checks en paralelo; ya lo usaste en miband). Alternativa Flask si prefieres lo de JumeX, pero FastAPI encaja mejor aquí.
- **Checks:** `httpx` (async), `dnspython`, `cryptography`/`ssl` para certificados, `beautifulsoup4` para parsear HTML.
- **IA:** API de un LLM para la capa de interpretación (prompt estricto, sin alucinar: "solo interpreta estos datos, no inventes hallazgos").
- **DB:** SQLite v1 → Postgres cuando escale.
- **PDF:** WeasyPrint (HTML→PDF, reaprovechas el diseño de la vista web) o ReportLab.
- **Frontend:** empieza con HTML/CSS/JS vanilla o Astro para la landing (rápido, SEO bueno); si el panel de informe crece, React.
- **Tareas en segundo plano:** `BackgroundTasks` de FastAPI para v1; Celery/RQ + Redis solo si hay concurrencia real.
- **Deploy:** landing en Vercel/Netlify; API en Railway/Render/Fly.io (gratis o barato para empezar).

---

## 8. Blindaje legal (NO negociable — es parte del producto, no burocracia aparte)

- **Solo pasivo en el flujo público.** Nada que "vulnere medidas de seguridad" (art. 197 bis CP). Los checks solo piden información que el servidor publica a cualquier visitante.
- **Checkbox de consentimiento obligatorio** antes de escanear: "Declaro ser titular de este dominio o tener autorización para analizarlo." Te protege como proveedor de la herramienta.
- **Rate limiting agresivo** en `/api/scan`: evita que alguien use Pipo como arma contra terceros y que esa responsabilidad te salpique.
- **Logs de quién escanea qué y cuándo:** trazabilidad por si hay que demostrar que un escaneo no lo lanzaste tú.
- **Términos de servicio + aviso legal + política de privacidad** propios de Pipo desde el día 1 (predica con el ejemplo).
- **Nada de Strix ni escaneo activo** hasta tener carta de autorización firmada (Rules of Engagement) — y eso es un servicio manual aparte, fuera del producto self-service.
- **No te presentes como DPO** salvo que lo seas: puedes hacer el diagnóstico RGPD, pero si necesitan Delegado formal, derivas a un abogado.
- **Seguro de responsabilidad civil profesional** cuando empieces a facturar de forma seria.

---

## 9. Roadmap por fases (orden de construcción)

**Fase 0 — Fundamentos (fin de semana 1)**
- Repo, estructura de carpetas, entorno Python, FastAPI "hola mundo", decisión de dominio/marca.

**Fase 1 — Motor de checks (semanas 1-2)**
- Implementa los checks uno a uno, empezando por los fáciles y visuales: SSL → headers → DNS/SPF → SEO básico. Cada check = función independiente que devuelve `{estado, detalle, prioridad}`. Testéalos contra tus propias webs demo.

**Fase 2 — API + informe crudo (semana 3)**
- Endpoint `/api/scan` que orquesta los checks en paralelo y devuelve JSON. Guardado en SQLite. Sin IA aún: enseña los datos crudos.

**Fase 3 — Capa IA + PDF (semana 4)**
- Prompt de interpretación (estricto, anti-alucinación). Genera el informe legible. Generador de PDF con marca Pipo.

**Fase 4 — Frontend + landing (semanas 5-6)**
- Landing (usa la que te dejo como base). Formulario con consentimiento. Vista de informe con semáforo. Estados con el personaje Pipo.

**Fase 5 — Blindaje y lanzamiento (semana 7)**
- Rate limiting, logs, ToS/privacidad, dominio en producción, deploy. Primer escaneo real de un negocio conocido.

**Fase 6 — Monetización (semana 8+)**
- Pasarela de pago (Stripe) para el informe one-shot. Lead magnet gratis conectado a email. Primeras cold-visits con Pipo en el móvil.

**Fase 7 — Recurrencia (más adelante)**
- Suscripción, re-escaneos programados, alertas por email, histórico. Aquí nace el MRR.

---

## 10. Qué aprendes (valor para tu CV)

FastAPI async en serio · orquestación de tareas concurrentes · integración de APIs externas (HIBP, PageSpeed) · diseño de prompts anti-alucinación en producción · generación de PDF · pasarela de pago · deploy y blindaje legal de un SaaS real · diseño de marca y landing que convierte. Es un proyecto end-to-end completo, no un ejercicio — eso pesa mucho más en un CV que otra práctica académica.

---

## 11. Riesgos y cómo mitigarlos

- **Falsos positivos que asustan de más:** calibra el semáforo con cabeza, no marques rojo lo que es ámbar. Tu credibilidad depende de esto.
- **La IA inventa hallazgos:** prompt estricto + siempre parte de datos crudos reales, nunca genera hallazgos desde cero.
- **Que se te vaya el tiempo del proyecto grande:** Pipo es el "fácil"; si un módulo te está costando semanas, simplifícalo o córtalo.
- **Mal uso de la herramienta por terceros:** rate limiting + consentimiento + logs.
- **Un cliente pide "y ya de paso hazme un pentest":** eso es el servicio manual con contrato firmado, nunca por el flujo self-service.
