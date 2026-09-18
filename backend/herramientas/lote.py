"""
Modo lote: revisa una lista de dominios y los ordena por quién está peor.

ESTO NO ES PARTE DEL PRODUCTO. Es una herramienta interna, para usar
desde tu propio ordenador antes de salir a visitar negocios: llegas
sabiendo qué falla en su web en vez de preguntando si necesitan una.

Cómo se usa:

    cd backend
    .venv/bin/python herramientas/lote.py dominios.txt
    .venv/bin/python herramientas/lote.py dominios.txt --csv resultados.csv

`dominios.txt` es un dominio por línea (las líneas vacías y las que
empiezan por # se saltan). También acepta un CSV exportado de cualquier
sitio: se queda con la primera columna de cada fila.

Va de tres en tres a propósito (LOTE_SIMULTANEO). No es por rendimiento
—el servidor aguantaría más— sino por prudencia: lanzar cincuenta
escaneos a la vez desde la misma IP se parece a un barrido automático,
y todo el diseño de Pipo está pensado para no parecer eso nunca.

NOTA LEGAL, importante antes de usarlo con webs de terceros: mirar
información pública de una web (lo que hace Pipo) es lo mismo que hace
Google, y es legal. Lo que NO es legal en España es mandarles después un
email comercial sin que te lo hayan pedido — la LSSI no tiene excepción
B2B (ver CLAUDE.md). Presentarte en persona, en cambio, no está regulado
por esa ley. Este script es para preparar visitas, no para mandar
correos en frío.
"""

import argparse
import asyncio
import csv
import sys
from pathlib import Path

# Permite ejecutar el script directamente ("python herramientas/lote.py")
# sin tener que instalar el proyecto como paquete.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.puntuacion import calcular_precio_arreglo  # noqa: E402
from app.scanner import ejecutar_escaneo  # noqa: E402
from app.seguridad import DominioNoValido, comprobar_dominio_publico, normalizar_dominio  # noqa: E402

LOTE_SIMULTANEO = 3

SEMAFORO = {"rojo": "ROJO ", "ambar": "ÁMBAR", "verde": "VERDE"}


def leer_dominios(ruta: Path) -> list[str]:
    """Un dominio por línea, o la primera columna si es un CSV."""
    dominios = []
    with ruta.open(encoding="utf-8") as archivo:
        for fila in csv.reader(archivo):
            if not fila:
                continue
            texto = fila[0].strip()
            if not texto or texto.startswith("#"):
                continue
            dominios.append(texto)
    return dominios


async def revisar(dominio: str) -> dict:
    """Un escaneo, devolviendo siempre una fila aunque falle."""
    try:
        limpio = normalizar_dominio(dominio)
        await comprobar_dominio_publico(limpio)
    except DominioNoValido as error:
        return {"dominio": dominio, "error": str(error)}

    try:
        resultado = await ejecutar_escaneo(limpio)
    except Exception as error:  # noqa: BLE001 - una web caída no debe parar el lote entero
        return {"dominio": limpio, "error": f"{type(error).__name__}: {error}"}

    resumen = resultado["resumen"]
    problemas = [c for c in resultado["checks"] if c["estado"] != "verde"]
    return {
        "dominio": limpio,
        "nota": resumen["puntuacion"],
        "estado": resumen["estado_global"],
        "graves": resumen["conteo"]["rojo"],
        "a_mejorar": resumen["conteo"]["ambar"],
        "precio_estimado": calcular_precio_arreglo(resultado["checks"], resultado.get("perfil_sitio")),
        "peor": "; ".join(c["check"] for c in problemas if c["estado"] == "rojo") or "—",
        "error": None,
    }


async def revisar_todos(dominios: list[str]) -> list[dict]:
    """Lanza los escaneos en grupos pequeños, enseñando el avance."""
    filas = []
    for inicio in range(0, len(dominios), LOTE_SIMULTANEO):
        grupo = dominios[inicio : inicio + LOTE_SIMULTANEO]
        print(f"  revisando {inicio + 1}-{inicio + len(grupo)} de {len(dominios)}...", file=sys.stderr)
        filas.extend(await asyncio.gather(*(revisar(d) for d in grupo)))
    return filas


def imprimir_tabla(filas: list[dict]) -> None:
    """Los peores primero: son a los que merece la pena ir a ver."""
    correctas = sorted((f for f in filas if not f["error"]), key=lambda f: f["nota"])
    fallidas = [f for f in filas if f["error"]]

    print(f"\n{'DOMINIO':<32} {'NOTA':>4}  {'SEMÁFORO':<7} {'GRAVES':>6} {'~PRECIO':>8}  PUNTOS EN ROJO")
    print("-" * 110)
    for fila in correctas:
        print(
            f"{fila['dominio'][:32]:<32} {fila['nota']:>4}  {SEMAFORO[fila['estado']]:<7} "
            f"{fila['graves']:>6} {str(fila['precio_estimado']) + '€':>8}  {fila['peor'][:38]}"
        )

    if fallidas:
        print("\nNo se han podido revisar:")
        for fila in fallidas:
            print(f"  {fila['dominio']}: {fila['error']}")

    if correctas:
        media = round(sum(f["nota"] for f in correctas) / len(correctas))
        con_graves = sum(1 for f in correctas if f["graves"])
        print(
            f"\n{len(correctas)} webs revisadas · nota media {media}/100 · "
            f"{con_graves} con algún fallo grave ({round(100 * con_graves / len(correctas))}%)"
        )


def guardar_csv(filas: list[dict], ruta: Path) -> None:
    """Para abrirlo en una hoja de cálculo y llevártelo a la visita."""
    columnas = ["dominio", "nota", "estado", "graves", "a_mejorar", "precio_estimado", "peor", "error"]
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        for fila in sorted(filas, key=lambda f: (f["error"] is not None, f.get("nota", 999))):
            escritor.writerow({columna: fila.get(columna, "") for columna in columnas})
    print(f"\nGuardado en {ruta}")


def main() -> None:
    analizador = argparse.ArgumentParser(description="Revisa una lista de dominios con Pipo.")
    analizador.add_argument("archivo", type=Path, help="archivo con un dominio por línea (o CSV)")
    analizador.add_argument("--csv", type=Path, help="guardar el resultado en este archivo CSV")
    argumentos = analizador.parse_args()

    if not argumentos.archivo.exists():
        analizador.error(f"No existe el archivo {argumentos.archivo}")

    dominios = leer_dominios(argumentos.archivo)
    if not dominios:
        analizador.error("El archivo no tiene ningún dominio.")

    print(f"Revisando {len(dominios)} dominios de {len(dominios) // LOTE_SIMULTANEO + 1} tandas...", file=sys.stderr)
    filas = asyncio.run(revisar_todos(dominios))

    imprimir_tabla(filas)
    if argumentos.csv:
        guardar_csv(filas, argumentos.csv)


if __name__ == "__main__":
    main()
