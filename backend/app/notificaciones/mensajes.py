"""
Contenido de los dos emails del flujo de pedido (ver CLAUDE.md, P2):
uno al cliente, en privado, con su caso concreto y cómo pagar; otro a
Alberto, avisando de que hay un pedido nuevo que atender.

Separado de enviar.py a propósito: enviar.py solo sabe mandar un email
genérico (asunto + cuerpo), y no tiene que saber nada de pedidos,
precios ni checks — igual que app/ia/cliente.py no sabe de hallazgos.
"""

from app.puntuacion import calcular_puntuacion


def _checks_a_mejorar(checks: list[dict]) -> str:
    """
    Lista en texto plano de los checks que no están en verde, usando el
    campo "detalle" que ya escribe cada check — no hace falta duplicar
    esas frases aquí, ya están pensadas para leerse en cristiano.
    """
    problematicos = [check for check in checks if check["estado"] != "verde"]
    if not problematicos:
        return "Ahora mismo no hay ningún punto en rojo o ámbar — buena señal."
    return "\n".join(f"- {check['detalle']}" for check in problematicos)


def mensaje_pedido_cliente(
    dominio: str,
    checks: list[dict],
    precio: int,
    telefono_bizum: str,
    referencia: str,
    precio_arreglo_estimado: int,
) -> tuple[str, str]:
    """Devuelve (asunto, cuerpo) del email privado al cliente."""
    nota = calcular_puntuacion(checks)
    asunto = f"Pipo — tu diagnóstico de {dominio} y cómo desbloquear las soluciones"
    cuerpo = f"""Hola,

Acabas de pedir el informe completo de {dominio} en Pipo. Este es tu diagnóstico:

Nota actual: {nota}/100

{_checks_a_mejorar(checks)}

Para acceder a las soluciones paso a paso de cada punto y al PDF descargable con la marca de Pipo, el pago es único, {precio}€.

La forma más rápida es Bizum al {telefono_bizum}, indicando en el concepto esta referencia: {referencia}

Si prefieres pagar de otra forma (tarjeta, PayPal...), contesta a este email y lo vemos.

En cuanto confirmemos el pago, te escribimos con todo desbloqueado.

Si prefieres que seamos nosotros quienes apliquemos los cambios en vez de hacerlos tú, el precio orientativo para tu web es de {precio_arreglo_estimado}€ — contesta a este email y hablamos.

Un saludo,
Pipo (Alberto)
"""
    return asunto, cuerpo


def mensaje_pedido_alberto(
    dominio: str,
    email_cliente: str,
    telefono_cliente: str | None,
    referencia: str,
    precio: int,
    precio_arreglo_estimado: int,
) -> tuple[str, str]:
    """Devuelve (asunto, cuerpo) del aviso interno para Alberto."""
    asunto = f"Nuevo pedido Pipo: {dominio} — {precio}€"
    cuerpo = f"""Nuevo pedido registrado.

Dominio: {dominio}
Email del cliente: {email_cliente}
Teléfono: {telefono_cliente or "no facilitado"}
Referencia: {referencia}
Precio: {precio}€
Precio orientativo "lo arreglamos nosotros": {precio_arreglo_estimado}€

Cuando confirmes el Bizum, avisa al cliente a mano — todavía no hay un panel para marcar pedidos como pagados.
"""
    return asunto, cuerpo
