"""
Acceso a la base de datos SQLite.

SQLite guarda todo en un único archivo (pipo.db), sin necesidad de
levantar un servidor de base de datos aparte. Es la opción del
planning para v1: cuando el proyecto crezca de verdad, se puede migrar
a Postgres sin cambiar demasiado el resto del código, pero hoy sería
complicar algo que no hace falta todavía.
"""

import json
import sqlite3
from pathlib import Path

# El archivo de la base de datos vive junto a este módulo, dentro de
# backend/. Está en .gitignore: no se sube a git porque son datos,
# no código.
RUTA_DB = Path(__file__).parent.parent / "pipo.db"


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
