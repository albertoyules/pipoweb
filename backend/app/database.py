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
import sqlite3
from pathlib import Path

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

        # Pedidos del nivel de pago "soluciones + PDF" (19€, cobrado por
        # Bizum a mano — ver CLAUDE.md, P2). `pagado` empieza en 0 y hoy
        # no hay ningún mecanismo automático que lo cambie a 1: eso es
        # trabajo pendiente (un panel para marcar pedidos como pagados a
        # mano tras comprobar el Bizum). Igual que en `leads`, sin
        # FOREIGN KEY hacia escaneos a propósito.
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referencia TEXT NOT NULL,
                email TEXT NOT NULL,
                dominio TEXT NOT NULL,
                id_escaneo INTEGER NOT NULL,
                precio INTEGER NOT NULL,
                pagado INTEGER NOT NULL DEFAULT 0,
                fecha TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        # Teléfono opcional del cliente (para identificar su Bizum entrante,
        # ya que Bizum solo enseña el número de quien paga). Añadida después
        # de crear la tabla, así que usa la misma migración seguridad que
        # las columnas de caché de arriba.
        _asegurar_columna(conexion, "pedidos", "telefono")


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


def guardar_escaneo(dominio: str, estado_global: str, resultado: dict) -> int:
    """
    Guarda un escaneo completo. El informe entero (resultado) se
    guarda como texto JSON en una sola columna en vez de repartirlo en
    muchas columnas: para v1 es más simple, y como todavía no hacemos
    búsquedas dentro del contenido de cada check, no hace falta más.
    Devuelve el id de la fila creada, por si el frontend quiere
    enlazar directamente a "ver este informe".
    """
    with obtener_conexion() as conexion:
        cursor = conexion.execute(
            """
            INSERT INTO escaneos (dominio, estado_global, resultado_json)
            VALUES (?, ?, ?)
            """,
            (dominio, estado_global, json.dumps(resultado)),
        )
        return cursor.lastrowid


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


def guardar_lead(email: str, dominio: str, id_escaneo: int) -> None:
    """
    Guarda un lead: alguien que ha dejado su email para desbloquear el
    resto del informe de un escaneo. Se permite dejarlo más de una vez
    para el mismo escaneo (por ejemplo, si recarga la página) sin que
    eso sea un error — simplemente queda otra fila con la fecha.
    """
    with obtener_conexion() as conexion:
        conexion.execute(
            "INSERT INTO leads (email, dominio, id_escaneo) VALUES (?, ?, ?)",
            (email, dominio, id_escaneo),
        )


def guardar_pedido(
    referencia: str, email: str, dominio: str, id_escaneo: int, precio: int, telefono: str | None = None
) -> None:
    """Guarda un pedido del nivel de pago, pendiente de confirmar por Bizum."""
    with obtener_conexion() as conexion:
        conexion.execute(
            "INSERT INTO pedidos (referencia, email, dominio, id_escaneo, precio, telefono) VALUES (?, ?, ?, ?, ?, ?)",
            (referencia, email, dominio, id_escaneo, precio, telefono),
        )
