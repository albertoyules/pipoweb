# El vídeo de la presentación de Pipo

La presentación de `presentacion/apaisada.html`, convertida en un MP4 de
1920×1080 con [Remotion](https://remotion.dev) (React que se dibuja
fotograma a fotograma).

## Usarlo

```bash
cd video
npm install          # solo la primera vez

npm run estudio      # previsualizar en el navegador, con línea de tiempo
npm run render       # genera out/pipo-presentacion.mp4
```

## Cómo está montado

| Archivo | Qué es |
|---|---|
| `src/marca.ts` | Colores, unidades y **las doce escenas**: cuánto dura cada una y dónde se pone Pipo. Casi todo lo que se quiera retocar está aquí. |
| `src/escenas/todas.tsx` | El texto de las doce diapositivas, palabra por palabra el mismo que el del deck. |
| `src/Pipo.tsx` | El búho, dibujado pieza a pieza para poder moverle ojos, cejas, alas y lupa por separado. |
| `src/Presentacion.tsx` | Monta el vídeo: fondo, hojas, las escenas en orden y el búho volando por encima de todas. |
| `src/piezas.tsx` | Titulares, listas, tarjetas... las piezas de las que se hacen las escenas. |

**Las medidas son las mismas que en el deck.** `u(7.8)` en el código es
`font-size:7.8cqh` en `apaisada.plantilla.html`. Se conservan los números
tal cual para que las dos piezas no se separen con el tiempo: si cambias
un tamaño en un sitio, cámbialo en el otro.

## Dos cosas que costaron encontrar

**Nada se anima con CSS.** Remotion no reproduce el vídeo, lo fotografía
cuadro a cuadro: una animación de CSS se quedaría congelada en su primer
fotograma. Todo —el vuelo, el parpadeo, el aleteo, el aro de la nota, los
números que suben— se calcula a partir de `useCurrentFrame()`. Por lo
mismo, las hojas usan `random("semilla")` de Remotion y no `Math.random`:
los fotogramas se reparten entre varios procesos y cada uno tiene que
dibujar exactamente la misma hoja en el mismo sitio.

**El búho vive fuera de las escenas.** Por eso puede cruzar el corte
entre una diapositiva y la siguiente volando, en vez de desaparecer y
reaparecer. Es lo que convierte doce láminas sueltas en una presentación.

## Si algo falla

**«No browser found for rendering frames»** — Remotion se descarga su
propio Chrome, pero con Node 26 la descompresión se queda a medias (deja
solo `ABOUT` y `LICENSE`). El zip sí está entero; se arregla
extrayéndolo a mano:

```bash
cd node_modules/.remotion/chrome-headless-shell/mac-arm64
unzip -oq ../chrome-headless-shell-mac-arm64.zip
chmod +x chrome-headless-shell-mac-arm64/chrome-headless-shell
```

**Pipo sale lavado, con la pupila marrón claro en vez de negra** — es el
halo ámbar pintándose por encima de él. En CSS un elemento posicionado se
dibuja sobre uno que no lo está, así que el `<div>` que envuelve al búho
necesita `position:relative`. No se ve a ojo en el estudio; se ve
comparando el valor de un píxel con el del deck.
