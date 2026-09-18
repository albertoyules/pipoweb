"""
Acceso a la base de datos SQLite.

SQLite guarda todo en un único archivo (pipo.db), sin necesidad de
levantar un servidor de base de datos aparte. Es la opción del
planning para v1: cuando el proyecto crezca de verdad, se puede migrar
a Postgres sin cambiar demasiado el resto del código, pero hoy sería
complicar algo que no hace falta todavía.
"""

import json
import os
import secrets
import sqlite3
from pathlib import Path

# Estados por los que pasa una solicitud de arreglo — el pipeline del
# panel CRM (ver CLAUDE.md, panel.html). Es el flujo manual de Alberto,
# no un sistema de pedidos automático: sirve para que no se le pierda
# nadie por el camino, y para saber de un vistazo quién necesita que
# actúe hoy.
#
# Ampliado el 13 ago 2026 de 3 a 6 pasos (antes: nueva/presupuestada/
# hecha). Los valores antiguos pueden seguir existiendo en filas creadas
# antes del cambio; el panel los muestra tal cual en vez de fallar.
ESTADOS_SOLICITUD = ("nuevo", "contactado", "presupuesto_enviado", "pagado", "arreglado", "cerrado")

# Dónde vive el archivo de la base de datos.
#
# En local: junto a este módulo, dentro de backend/. Está en .gitignore
# porque son datos, no código.
#
# En Railway: el disco del contenedor es EFÍMERO — se borra entero en
# cada despliegue. Con la ruta de local, cada `git push` vaciaba la base
# de datos y los enlaces a informe.html?id=X de escaneos anteriores
# dejaban de funcionar. Por eso en producción se define la variable de
# entorno PIPO_DB_DIR apuntando a un volumen persistente (ver CLAUDE.md).
_DIRECTORIO_DB = Path(os.getenv("PIPO_DB_DIR") or Path(__file__).parent.parent)
_DIRECTORIO_DB.mkdir(parents=True, exist_ok=True)
RUTA_DB = _DIRECTORIO_DB / "pipo.db"


def obtener_conexion() -> sqlite3.Connection:
    """
    Abre una conexión a la base de datos. `row_factory = sqlite3.Row`
    hace que cada fila se pueda leer como un diccionario (por nombre
    de columna) en vez de como una tupla posicional — más cómodo y
    menos propenso a errores al leer los datos después.
    """
    conexion = sqlite3.connect(RUTA_DB)
    conexion.row_factory = sqlite3.Row
    return conexion


def inicializar_db() -> None:
    """
    Crea la tabla de escaneos si todavía no existe. Se llama una vez
    al arrancar la aplicación (ver main.py). 'IF NOT EXISTS' hace que
    sea seguro llamarla cada vez que arranca el servidor, sin borrar
    nada de lo que ya hubiera.
    """
    with obtener_conexion() as conexion:
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS escaneos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dominio TEXT NOT NULL,
                fecha TEXT NOT NULL DEFAULT (datetime('now')),
                estado_global TEXT NOT NULL,
                resultado_json TEXT NOT NULL
            )
            """
        )

        # Caché de resultados caros de IA/PageSpeed, guardados junto al
        # escaneo al que pertenecen. Empiezan NULL: se rellenan la
        # primera vez que alguien los pide (ver main.py), y a partir de
        # ahí se sirven desde aquí sin volver a gastar cuota de Gemini
        # ni pedirle otra auditoría a Google PageSpeed. No hace falta
        # invalidarlos nunca: un escaneo, una vez guardado, no cambia
        # (un "re-escaneo" futuro crea una fila nueva, no reescribe esta).
        for columna in ("informe_json", "soluciones_json", "rendimiento_json"):
            _asegurar_columna(conexion, "escaneos", columna)

        # Token del enlace del informe. Los ids son correlativos, así que
        # sin esto cualquiera podía recorrer /api/scan/1, /2, /3... y leer
        # todos los escaneos hechos con Pipo (comprobado en producción el
        # 13 ago 2026). El token no convierte esto en un sistema de
        # cuentas: el enlace se sigue pudiendo compartir tal cual, solo
        # deja de poder adivinarse.
        _asegurar_columna(conexion, "escaneos", "token")

        # Registro de la declaración de titularidad ("declaro ser el
        # titular de este dominio o tener autorización"). La FAQ decía
        # que quedaba registrado y no era verdad: el checkbox no salía
        # del navegador. Se guarda cuándo y desde qué IP se declaró.
        _asegurar_columna(conexion, "escaneos", "ip_solicitante")

        _rellenar_tokens_que_falten(conexion)

        # Leads captados en el escaneo gratis: al enseñar solo un
        # adelanto del informe (ver /api/leads en main.py), quien quiere
        # ver el resto deja su email. Es lo que convierte el escaneo
        # gratis en algo que alimenta una lista de leads de verdad, en
        # vez de enseñarlo todo sin pedir nada a cambio (punto 5.2 del
        # planning). No hay FOREIGN KEY hacia escaneos a propósito: si
        # algún día se borra un escaneo antiguo, no queremos perder el
        # lead por una restricción de integridad — son datos con ciclos
        # de vida distintos.
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                dominio TEXT NOT NULL,
                id_escaneo INTEGER NOT NULL,
                fecha TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        # Consentimiento de marketing (13 ago 2026): la casilla del
        # formulario "avísame" pasó a ser explícitamente sobre recibir
        # consejos y ofertas, no solo sobre ese aviso puntual — es la
        # base legal (RGPD art. 6.1.a, consentimiento expreso y
        # específico) que permite mandar campañas más adelante. Sin esta
        # columna, un lead solo se podría usar para lo que pidió en su
        # momento, nunca para recordarle que vuelva.
        _asegurar_columna(conexion, "leads", "consiente_marketing")

        # Solicitudes de "arregladlo vosotros" — el producto de pago
        # desde el 13 ago 2026 (antes era un pedido de 19€ por el informe
        # con soluciones; ver CLAUDE.md, P2, para el porqué del cambio).
        #
        # Aquí no se cobra nada por adelantado: es un servicio, así que
        # el flujo es "llega la solicitud → Alberto responde con
        # presupuesto → se hace el trabajo". `estado` es esa nota para
        # él mismo. `precio_estimado` es el orientativo que calcula
        # puntuacion.py, no un precio cerrado.
        #
        # La tabla antigua `pedidos` se queda como está si existía: son
        # datos de pruebas de la demo y borrarlos no aporta nada.
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS solicitudes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referencia TEXT NOT NULL,
                email TEXT NOT NULL,
                telefono TEXT,
                dominio TEXT NOT NULL,
                id_escaneo INTEGER NOT NULL,
                precio_estimado INTEGER NOT NULL,
                mensaje TEXT,
                estado TEXT NOT NULL DEFAULT 'nuevo',
                fecha TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        # Campos del panel CRM (13 ago 2026): notas libres de Alberto
        # sobre el caso, y cuánto/cuándo se cobró. Sin esto, "quién ha
        # pagado y cuánto" solo vivía en su cabeza — es justo lo que el
        # panel existe para evitar.
        _asegurar_columna(conexion, "solicitudes", "notas")
        _asegurar_columna(conexion, "solicitudes", "importe_cobrado")
        _asegurar_columna(conexion, "solicitudes", "fecha_cobro")

        # Migra las pocas filas que se crearon el mismo 13 ago 2026 con
        # el pipeline viejo de 3 pasos, antes de ampliarlo a 6. Sin esto
        # se quedarían con un estado que ya no aparece en ningún menú.
        for viejo, nuevo in (("nueva", "nuevo"), ("presupuestada", "presupuesto_enviado"), ("hecha", "cerrado")):
            conexion.execute("UPDATE solicitudes SET estado = ? WHERE estado = ?", (nuevo, viejo))

        # Nivel "Tranquilidad" (18 sep 2026, ver CLAUDE.md P3): re-escaneo
        # mensual con aviso por email. Sin cobro automático todavía —
        # Alberto da de alta la suscripción a mano desde el panel cuando
        # cierra un cliente, igual que ya hace con `solicitudes`. Por eso
        # no hay ninguna referencia de pago aquí: es solo "a quién y a
        # qué dominio hay que volver a mirar cada mes".
        #
        # `ultima_ejecucion` es lo que decide a quién le toca cuando el
        # cron llama al endpoint de re-escaneo: NULL significa "nunca se
        # ha ejecutado, tócale ya". No hay FOREIGN KEY hacia escaneos
        # (id_escaneo_origen es solo referencia informativa de con qué
        # escaneo empezó) por el mismo motivo que en `leads`: ciclos de
        # vida distintos, no hace falta que la integridad de uno bloquee
        # al otro.
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS suscripciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                dominio TEXT NOT NULL,
                id_escaneo_origen INTEGER,
                activa INTEGER NOT NULL DEFAULT 1,
                fecha_alta TEXT NOT NULL DEFAULT (datetime('now')),
                ultimo_escaneo_id INTEGER,
                ultima_ejecucion TEXT
            )
            """
        )


def _asegurar_columna(conexion: sqlite3.Connection, tabla: str, columna: str) -> None:
    """
    Añade una columna TEXT a una tabla si todavía no existe. SQLite no
    soporta 'ADD COLUMN IF NOT EXISTS' directamente, así que miramos
    primero con PRAGMA table_info. Así, quien ya tenía un pipo.db de
    antes de la caché no pierde su historial de escaneos: la próxima
    vez que arranque el servidor, la tabla se actualiza sola.
    """
    columnas_existentes = {
        fila["name"] for fila in conexion.execute(f"PRAGMA table_info({tabla})")
    }
    if columna not in columnas_existentes:
        conexion.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} TEXT")


def _rellenar_tokens_que_falten(conexion: sqlite3.Connection) -> None:
    """
    Da un token a los escaneos que se guardaron antes de que existieran
    (los de la demo). Sin esto, esas filas se quedarían con token NULL y
    habría que decidir entre dejarlas accesibles a cualquiera —el
    agujero que estamos cerrando— o romper sus enlaces sin avisar.
    """
    filas = conexion.execute("SELECT id FROM escaneos WHERE token IS NULL").fetchall()
    for fila in filas:
        conexion.execute(
            "UPDATE escaneos SET token = ? WHERE id = ?",
            (secrets.token_urlsafe(16), fila["id"]),
        )


def guardar_escaneo(
    dominio: str, estado_global: str, resultado: dict, ip_solicitante: str | None = None
) -> tuple[int, str]:
    """
    Guarda un escaneo completo. El informe entero (resultado) se
    guarda como texto JSON en una sola columna en vez de repartirlo en
    muchas columnas: para v1 es más simple, y como todavía no hacemos
    búsquedas dentro del contenido de cada check, no hace falta más.

    Devuelve (id, token): el id identifica la fila y el token es lo que
    hace que su enlace no se pueda adivinar. `ip_solicitante` queda
    guardado junto a la fecha como registro de quién declaró ser el
    titular del dominio.
    """
    token = secrets.token_urlsafe(16)
    with obtener_conexion() as conexion:
        cursor = conexion.execute(
            """
            INSERT INTO escaneos (dominio, estado_global, resultado_json, token, ip_solicitante)
            VALUES (?, ?, ?, ?, ?)
            """,
            (dominio, estado_global, json.dumps(resultado), token, ip_solicitante),
        )
        return cursor.lastrowid, token


def escaneo_anterior(dominio: str) -> dict | None:
    """
    El escaneo previo más reciente de ese dominio, si lo hay. Es lo que
    permite decir "esto ha mejorado desde la última vez" sin necesitar
    todavía ninguna tarea programada.
    """
    with obtener_conexion() as conexion:
        fila = conexion.execute(
            "SELECT resultado_json, fecha FROM escaneos WHERE dominio = ? ORDER BY id DESC LIMIT 1",
            (dominio,),
        ).fetchone()

    if fila is None:
        return None
    anterior = json.loads(fila["resultado_json"])
    anterior["fecha"] = fila["fecha"]
    return anterior


def estadisticas_globales() -> dict:
    """
    Resumen de todo lo que Pipo ha revisado, contando cada dominio una
    sola vez (su escaneo más reciente). Analizar diez veces la misma web
    mientras se programa no debe deformar la media que luego se enseña
    en la landing.
    """
    with obtener_conexion() as conexion:
        filas = conexion.execute(
            """
            SELECT e.estado_global, e.resultado_json
            FROM escaneos e
            JOIN (SELECT dominio, MAX(id) AS ultimo FROM escaneos GROUP BY dominio) u
              ON e.id = u.ultimo
            """
        ).fetchall()

    if not filas:
        return {"webs_analizadas": 0, "nota_media": None, "porcentaje_con_fallo_grave": None}

    notas = []
    con_fallo_grave = 0
    for fila in filas:
        resultado = json.loads(fila["resultado_json"])
        nota = resultado.get("resumen", {}).get("puntuacion")
        if nota is not None:
            notas.append(nota)
        if fila["estado_global"] == "rojo":
            con_fallo_grave += 1

    return {
        "webs_analizadas": len(filas),
        "nota_media": round(sum(notas) / len(notas)) if notas else None,
        "porcentaje_con_fallo_grave": round(100 * con_fallo_grave / len(filas)),
    }


def obtener_escaneo(id_escaneo: int) -> dict | None:
    """
    Recupera un escaneo guardado por su id. None si no existe.
    Los campos de caché (informe/soluciones/rendimiento) vienen ya
    parseados a dict, o None si todavía no se han pedido nunca.
    """
    with obtener_conexion() as conexion:
        fila = conexion.execute(
            "SELECT * FROM escaneos WHERE id = ?", (id_escaneo,)
        ).fetchone()

    if fila is None:
        return None

    return {
        "id": fila["id"],
        "dominio": fila["dominio"],
        "fecha": fila["fecha"],
        "token": fila["token"],
        "estado_global": fila["estado_global"],
        "resultado": json.loads(fila["resultado_json"]),
        "informe": json.loads(fila["informe_json"]) if fila["informe_json"] else None,
        "soluciones": json.loads(fila["soluciones_json"]) if fila["soluciones_json"] else None,
        "rendimiento": json.loads(fila["rendimiento_json"]) if fila["rendimiento_json"] else None,
    }


def guardar_informe(id_escaneo: int, informe: dict) -> None:
    """Cachea el informe interpretado por IA para no volver a llamarla."""
    with obtener_conexion() as conexion:
        conexion.execute(
            "UPDATE escaneos SET informe_json = ? WHERE id = ?",
            (json.dumps(informe), id_escaneo),
        )


def guardar_soluciones(id_escaneo: int, soluciones: dict) -> None:
    """Cachea las soluciones generadas por IA para no volver a llamarla."""
    with obtener_conexion() as conexion:
        conexion.execute(
            "UPDATE escaneos SET soluciones_json = ? WHERE id = ?",
            (json.dumps(soluciones), id_escaneo),
        )


def guardar_rendimiento(id_escaneo: int, rendimiento: dict) -> None:
    """Cachea la auditoría de PageSpeed para no volver a pedírsela a Google."""
    with obtener_conexion() as conexion:
        conexion.execute(
            "UPDATE escaneos SET rendimiento_json = ? WHERE id = ?",
            (json.dumps(rendimiento), id_escaneo),
        )


def guardar_lead(email: str, dominio: str, id_escaneo: int, consiente_marketing: bool = False) -> None:
    """
    Guarda un lead: alguien que ha dejado su email a través del
    formulario de avisos de informe.html. Se permite dejarlo más de una
    vez para el mismo escaneo (por ejemplo, si recarga la página) sin
    que eso sea un error — simplemente queda otra fila con la fecha.

    `consiente_marketing` viene del checkbox específico de ese
    formulario ("quiero recibir consejos y ofertas..."); sin él a True,
    este email solo debería usarse para lo que se pidió en su momento,
    nunca para campañas (ver decisión de RGPD en inicializar_db).
    """
    with obtener_conexion() as conexion:
        conexion.execute(
            "INSERT INTO leads (email, dominio, id_escaneo, consiente_marketing) VALUES (?, ?, ?, ?)",
            (email, dominio, id_escaneo, "1" if consiente_marketing else "0"),
        )


def listar_leads() -> list[dict]:
    """Todos los leads (emails captados por el formulario de avisos), más recientes primero."""
    with obtener_conexion() as conexion:
        filas = conexion.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()
    return [
        {**dict(fila), "consiente_marketing": fila["consiente_marketing"] == "1"}
        for fila in filas
    ]


def listar_actividad_reciente(limite: int = 60) -> list[dict]:
    """
    Los últimos escaneos, con el email captado para ese escaneo si lo
    hay (puede que ninguno, un dominio se puede analizar sin dejar
    nada). Es la vista de "quién ha entrado a la web" del panel: no
    todo el que escanea deja un lead, y aun así interesa ver que
    analizó su dominio y qué nota sacó.

    `limite` existe porque en producción esto puede acumular escaneos
    de prueba sin parar — el panel no necesita verlos todos, con los
    últimos basta para saber qué está pasando ahora mismo.
    """
    with obtener_conexion() as conexion:
        filas = conexion.execute(
            """
            SELECT e.id, e.dominio, e.fecha, e.estado_global, e.resultado_json,
                   (SELECT email FROM leads WHERE id_escaneo = e.id ORDER BY id DESC LIMIT 1) AS email
            FROM escaneos e
            ORDER BY e.id DESC
            LIMIT ?
            """,
            (limite,),
        ).fetchall()

    actividad = []
    for fila in filas:
        resultado = json.loads(fila["resultado_json"])
        actividad.append(
            {
                "id": fila["id"],
                "dominio": fila["dominio"],
                "fecha": fila["fecha"],
                "estado_global": fila["estado_global"],
                "nota": resultado.get("resumen", {}).get("puntuacion"),
                "email": fila["email"],
            }
        )
    return actividad


def guardar_solicitud(
    referencia: str,
    email: str,
    dominio: str,
    id_escaneo: int,
    precio_estimado: int,
    telefono: str | None = None,
    mensaje: str | None = None,
) -> None:
    """Guarda una solicitud de arreglo, pendiente de que Alberto la conteste."""
    with obtener_conexion() as conexion:
        conexion.execute(
            """
            INSERT INTO solicitudes
                (referencia, email, telefono, dominio, id_escaneo, precio_estimado, mensaje, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'nuevo')
            """,
            # 'nuevo' se pasa explícito, no confiando en el DEFAULT de la
            # columna: la tabla ya existía en producción con DEFAULT
            # 'nueva' (el pipeline de 3 pasos, anterior al de 6 del 13
            # ago 2026) — CREATE TABLE IF NOT EXISTS no toca el DEFAULT
            # de una tabla que ya existe, así que confiar en él habría
            # seguido creando solicitudes con el estado viejo.
            (referencia, email, telefono, dominio, id_escaneo, precio_estimado, mensaje),
        )


def listar_solicitudes() -> list[dict]:
    """Todas las solicitudes, más recientes primero — para el panel de Alberto."""
    with obtener_conexion() as conexion:
        filas = conexion.execute(
            """
            SELECT s.*, e.token AS token_escaneo
            FROM solicitudes s
            LEFT JOIN escaneos e ON e.id = s.id_escaneo
            ORDER BY s.id DESC
            """
        ).fetchall()
    return [dict(fila) for fila in filas]


def marcar_estado_solicitud(id_solicitud: int, estado: str) -> bool:
    """Cambia el estado de una solicitud. Devuelve False si ese id no existía."""
    with obtener_conexion() as conexion:
        cursor = conexion.execute(
            "UPDATE solicitudes SET estado = ? WHERE id = ?", (estado, id_solicitud)
        )
        return cursor.rowcount > 0


def guardar_notas_solicitud(id_solicitud: int, notas: str) -> bool:
    """
    Sustituye las notas libres de una solicitud (qué le dijo Alberto,
    qué pidió el cliente). Sustituye, no acumula: es un cuaderno de
    caso, no un histórico de mensajes — más simple de mantener.
    """
    with obtener_conexion() as conexion:
        cursor = conexion.execute(
            "UPDATE solicitudes SET notas = ? WHERE id = ?", (notas, id_solicitud)
        )
        return cursor.rowcount > 0


def marcar_cobro_solicitud(id_solicitud: int, importe_cobrado: int) -> bool:
    """
    Registra cuánto se ha cobrado por una solicitud, con la fecha de
    hoy. No cambia el estado por su cuenta — es Alberto quien decide si
    "cobrado" significa ya "pagado" en el pipeline o algo más adelante
    (por ejemplo, si cobra una señal antes de terminar el trabajo).
    """
    with obtener_conexion() as conexion:
        cursor = conexion.execute(
            "UPDATE solicitudes SET importe_cobrado = ?, fecha_cobro = datetime('now') WHERE id = ?",
            (importe_cobrado, id_solicitud),
        )
        return cursor.rowcount > 0


def guardar_suscripcion(email: str, dominio: str, id_escaneo_origen: int | None) -> int:
    """
    Da de alta una suscripción al nivel Tranquilidad. `ultima_ejecucion`
    empieza NULL a propósito: así el motor de re-escaneo (ver
    app/tareas.py) la coge en la primera pasada, en vez de esperar 30
    días desde el alta para el primer aviso.
    """
    with obtener_conexion() as conexion:
        cursor = conexion.execute(
            "INSERT INTO suscripciones (email, dominio, id_escaneo_origen) VALUES (?, ?, ?)",
            (email, dominio, id_escaneo_origen),
        )
        return cursor.lastrowid


def listar_suscripciones(solo_activas: bool = False) -> list[dict]:
    """Todas las suscripciones, más recientes primero."""
    consulta = "SELECT * FROM suscripciones"
    if solo_activas:
        consulta += " WHERE activa = 1"
    consulta += " ORDER BY id DESC"
    with obtener_conexion() as conexion:
        filas = conexion.execute(consulta).fetchall()
    return [{**dict(fila), "activa": fila["activa"] == 1} for fila in filas]


def suscripciones_pendientes_de_re_escaneo(dias: int = 30) -> list[dict]:
    """
    Suscripciones activas a las que les toca re-escaneo: nunca
    ejecutadas, o con la última ejecución de hace `dias` o más. Es la
    cola que consume el cron (ver app/tareas.py) — llamarlo de más no
    duplica trabajo, porque cada pasada solo coge lo que ya tocaba.
    """
    with obtener_conexion() as conexion:
        filas = conexion.execute(
            f"""
            SELECT * FROM suscripciones
            WHERE activa = 1
              AND (ultima_ejecucion IS NULL OR ultima_ejecucion <= datetime('now', '-{int(dias)} days'))
            ORDER BY id ASC
            """
        ).fetchall()
    return [{**dict(fila), "activa": fila["activa"] == 1} for fila in filas]


def marcar_ejecutada_suscripcion(id_suscripcion: int, id_escaneo_nuevo: int) -> None:
    """Registra que se ha re-escaneado esta suscripción ahora mismo."""
    with obtener_conexion() as conexion:
        conexion.execute(
            "UPDATE suscripciones SET ultimo_escaneo_id = ?, ultima_ejecucion = datetime('now') WHERE id = ?",
            (id_escaneo_nuevo, id_suscripcion),
        )


def dar_de_baja_suscripcion(id_suscripcion: int) -> bool:
    """Desactiva una suscripción. No la borra: queda el histórico de que existió."""
    with obtener_conexion() as conexion:
        cursor = conexion.execute(
            "UPDATE suscripciones SET activa = 0 WHERE id = ?", (id_suscripcion,)
        )
        return cursor.rowcount > 0
