/**
 * La marca de Pipo, en un solo sitio.
 *
 * Los mismos colores que landing/index.html y que la presentación de
 * presentacion/apaisada.plantilla.html — este vídeo es esa presentación,
 * no una versión libre de ella.
 */

export const COLOR = {
  crema: "#F5EFE6",
  cremaHonda: "#EBE1D2",
  marron: "#B08968",
  marronHondo: "#6F4E37",
  terracota: "#C97B5A",
  salvia: "#8A9A5B",
  ambar: "#D9A441",
  ladrillo: "#B34733",
  tinta: "#3A2E24",
  tintaTenue: "rgba(58,46,36,.72)",
  tintaDebil: "rgba(58,46,36,.58)",
  linea: "rgba(111,78,55,.16)",
} as const;

export const ALTO = 1080;
export const ANCHO = 1920;
export const FPS = 30;

/**
 * La presentación en HTML mide todo en cqh (1% del alto del marco).
 * Aquí el alto es fijo, así que 1cqh son 10,8 px exactos: `u(7.8)` es
 * el mismo tamaño de letra que `font-size:7.8cqh` en el deck. Se
 * conservan los números tal cual para que las dos piezas no se
 * separen con el tiempo.
 */
export const u = (cqh: number) => cqh * (ALTO / 100);

/** Lo mismo para el eje horizontal (1cqw = 19,2 px). */
export const h = (cqw: number) => cqw * (ANCHO / 100);

export type Gesto = "mira" | "alerta" | "orgullo" | "saluda";

export type Sitio = {
  /** desplazamiento desde el centro del cuadro, en píxeles */
  x: number;
  y: number;
  escala: number;
  opacidad: number;
};

export type Escena = {
  id: string;
  duracion: number;
  gesto: Gesto;
  pipo: Sitio;
};

/**
 * Dónde se pone Pipo en cada escena. Son las mismas posiciones que las
 * de data-px/data-py del deck, ya pasadas a píxeles.
 */
export const ESCENAS: Escena[] = [
  { id: "portada",   duracion: 120, gesto: "mira",    pipo: { x: h(-24), y: 0,        escala: 1.15, opacidad: 1 } },
  { id: "problema",  duracion: 165, gesto: "alerta",  pipo: { x: h(30),  y: u(-4),    escala: 0.75, opacidad: 1 } },
  { id: "idea",      duracion: 150, gesto: "mira",    pipo: { x: h(40),  y: u(-34),   escala: 0.34, opacidad: 0.6 } },
  { id: "regla",     duracion: 180, gesto: "alerta",  pipo: { x: h(-30), y: u(6),     escala: 0.75, opacidad: 1 } },
  { id: "revisa",    duracion: 180, gesto: "mira",    pipo: { x: h(41),  y: u(-36),   escala: 0.30, opacidad: 0.5 } },
  { id: "nota",      duracion: 180, gesto: "orgullo", pipo: { x: h(40),  y: u(-34),   escala: 0.34, opacidad: 0.6 } },
  { id: "traducido", duracion: 165, gesto: "mira",    pipo: { x: h(40),  y: u(34),    escala: 0.34, opacidad: 0.6 } },
  { id: "honestidad",duracion: 195, gesto: "alerta",  pipo: { x: h(-30), y: u(-6),    escala: 0.75, opacidad: 1 } },
  { id: "campo",     duracion: 165, gesto: "mira",    pipo: { x: h(41),  y: u(36),    escala: 0.30, opacidad: 0.55 } },
  { id: "algodon",   duracion: 180, gesto: "orgullo", pipo: { x: h(30),  y: u(8),     escala: 0.80, opacidad: 1 } },
  { id: "modelo",    duracion: 180, gesto: "mira",    pipo: { x: h(41),  y: u(-36),   escala: 0.30, opacidad: 0.5 } },
  { id: "cierre",    duracion: 150, gesto: "saluda",  pipo: { x: h(-24), y: 0,        escala: 1.15, opacidad: 1 } },
];

/** Fotograma en el que empieza cada escena. */
export const ARRANQUES = ESCENAS.reduce<number[]>((acc, e, i) => {
  acc.push(i === 0 ? 0 : acc[i - 1] + ESCENAS[i - 1].duracion);
  return acc;
}, []);

export const DURACION_TOTAL = ESCENAS.reduce((t, e) => t + e.duracion, 0);
