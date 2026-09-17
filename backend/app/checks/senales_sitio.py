"""
Rutas y huellas usadas para detectar señales del perfil de un sitio
(checkout, login, blog) — compartidas entre perfil_sitio.py y
area_privada_check.py, para que las dos ubicaciones digan siempre lo
mismo del mismo HTML.

Extraído el 17 sep 2026: hasta esta fecha area_privada_check.py tenía
su PROPIA copia de RUTAS_LOGIN, a propósito ("no se importan"), y al
ampliar la lista real (PrestaShop, Shopify) solo se actualizó una de
las dos copias en el primer intento — el mismo tipo de fallo silencioso
que ya había costado un hallazgo perdido con la detección de CMS de
PrestaShop. Una sola fuente de verdad para las rutas evita que vuelva
a pasar.
"""

# Rutas de checkout/carrito. PrestaShop usa /commande y /panier
# (francés, su idioma de fábrica) incluso en tiendas en español;
# Shopify usa /checkouts/ (con "s").
RUTAS_CHECKOUT = (
    "/carrito", "/cart", "/checkout", "/checkouts/", "/cesta", "/finalizar-compra",
    "/commande", "/panier",
)

# Rutas de login/acceso. Incluye las de PrestaShop (/connexion,
# /identity) y Shopify (/account/login), y variantes con y sin guion
# de "mi cuenta" que se ven en tiendas reales.
RUTAS_LOGIN = (
    "/wp-login.php", "/wp-admin",
    "/mi-cuenta", "/micuenta", "/my-account", "/account/login",
    "/login", "/acceso", "/area-cliente", "/area-privada",
    "/connexion", "/identity",
)

# Señales de blog/web de contenido: feed RSS, o estructura típica de
# posts (/blog/, /category/, /tag/, /author/).
RUTAS_BLOG = ("/feed", "/blog/", "/category/", "/tag/", "/author/", "rss+xml")
