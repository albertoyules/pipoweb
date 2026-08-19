import React from "react";
import { AbsoluteFill, interpolate, random, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { ALTO, ANCHO, COLOR, h, u } from "./marca";

const SERIF = "Fraunces, Georgia, serif";
const PALO = "Nunito, system-ui, sans-serif";

/* ---------- ENTRADA ESCALONADA ----------
   Cada bloque de una escena entra un poco después que el anterior. El
   retardo lo marca `orden`, igual que la variable --i del deck. */
export const Aparece: React.FC<{ orden: number; children: React.ReactNode }> = ({
  orden,
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({
    frame: frame - (5 + orden * 4),
    fps,
    config: { damping: 200, mass: 0.6 },
  });
  return (
    <div style={{ opacity: p, transform: `translateY(${(1 - p) * u(2.2)}px)` }}>{children}</div>
  );
};

/* ---------- FONDO ----------
   La luz cálida del deck: un halo ámbar arriba a la derecha y otro
   terracota abajo a la izquierda, sobre el crema de la marca. */
export const Fondo: React.FC = () => (
  <AbsoluteFill
    style={{
      backgroundColor: COLOR.crema,
      backgroundImage: [
        "radial-gradient(70% 55% at 88% 6%, rgba(217,164,65,.20), transparent 62%)",
        "radial-gradient(60% 50% at 6% 96%, rgba(201,123,90,.15), transparent 64%)",
      ].join(","),
    }}
  />
);

/* ---------- HOJAS DE OTOÑO ----------
   Caen durante todo el vídeo, atravesando el corte entre escenas: son
   lo único que dice que las doce diapositivas son el mismo sitio.
   `random(semilla)` en vez de Math.random porque Remotion reparte los
   fotogramas entre varios procesos y cada uno tiene que dibujar
   exactamente la misma hoja en el mismo sitio. */
export const Hojas: React.FC<{ cuantas?: number }> = ({ cuantas = 11 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tonos = [COLOR.marron, COLOR.terracota, COLOR.ambar, COLOR.salvia];

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {new Array(cuantas).fill(0).map((_, i) => {
        const tam = random(`t${i}`) * u(2.4) + u(1.6);
        const dur = (random(`d${i}`) * 14 + 20) * fps;
        const desfase = random(`f${i}`) * dur;
        const avance = ((frame + desfase) % dur) / dur;
        const x = random(`x${i}`) * (ANCHO * 0.92) + ANCHO * 0.02;
        const deriva = (random(`v${i}`) * 2 - 1) * h(5);
        const giro = (random(`g${i}`) * 2 - 1) * 220;
        return (
          <svg
            key={i}
            viewBox="0 0 24 24"
            style={{
              position: "absolute",
              width: tam,
              left: x,
              top: -ALTO * 0.08,
              opacity: 0.34,
              transform: `translate(${deriva * avance}px, ${avance * ALTO * 1.18}px) rotate(${
                giro * avance
              }deg)`,
            }}
          >
            <path d="M12 2 C18 6 21 12 12 22 C3 12 6 6 12 2Z" fill={tonos[i % tonos.length]} />
          </svg>
        );
      })}
    </AbsoluteFill>
  );
};

/* ---------- ARMAZÓN DE ESCENA ---------- */
type Lado = "izquierda" | "derecha";

export const Escena: React.FC<{
  /** a qué lado se arrima el texto (el contrario de donde está Pipo) */
  lado?: Lado;
  ancho?: number;
  junta?: boolean;
  children: React.ReactNode;
}> = ({ lado = "izquierda", ancho = u(142), junta = false, children }) => (
  <AbsoluteFill
    style={{
      padding: `${u(8)}px ${h(6)}px`,
      display: "grid",
      alignContent: "center",
      justifyItems: lado === "derecha" ? "end" : "start",
    }}
  >
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: junta ? u(2.1) : u(3.2),
        width: "100%",
        maxWidth: ancho,
      }}
    >
      {children}
    </div>
  </AbsoluteFill>
);

/* ---------- TIPOGRAFÍA ---------- */
export const Rotulo: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p
    style={{
      fontFamily: PALO,
      fontSize: u(2.15),
      fontWeight: 800,
      textTransform: "uppercase",
      letterSpacing: "0.2em",
      color: COLOR.terracota,
      display: "flex",
      alignItems: "center",
      gap: "0.7em",
      margin: 0,
    }}
  >
    <span style={{ width: "2.2em", height: 2, background: COLOR.terracota, borderRadius: 2 }} />
    {children}
  </p>
);

export const Titular: React.FC<{ children: React.ReactNode; grande?: boolean }> = ({
  children,
  grande = false,
}) => (
  <h2
    style={{
      fontFamily: SERIF,
      fontWeight: 600,
      fontSize: grande ? u(10.66) : u(7.8),
      letterSpacing: "-0.025em",
      lineHeight: 1.04,
      color: COLOR.marronHondo,
      margin: 0,
      fontVariationSettings: grande ? '"opsz" 144' : '"opsz" 120',
    }}
  >
    {children}
  </h2>
);

export const Entradilla: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p style={{ fontFamily: PALO, fontSize: u(3.38), color: COLOR.tintaTenue, maxWidth: "32ch", margin: 0, lineHeight: 1.6 }}>
    {children}
  </p>
);

export const Pie: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p style={{ fontFamily: PALO, fontSize: u(2.6), color: COLOR.tintaDebil, maxWidth: "60ch", margin: 0, lineHeight: 1.5 }}>
    {children}
  </p>
);

export const Fuerte: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <strong style={{ color: COLOR.marronHondo, fontWeight: 800 }}>{children}</strong>
);

/* ---------- LISTAS ---------- */
export const Lista: React.FC<{ items: React.ReactNode[]; tam?: number; hueco?: number }> = ({
  items,
  tam = u(2.34),
  hueco = u(0.7),
}) => (
  <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: hueco, margin: 0, padding: 0 }}>
    {items.map((it, i) => (
      <li
        key={i}
        style={{
          fontFamily: PALO,
          fontSize: tam,
          color: COLOR.tintaTenue,
          lineHeight: 1.4,
          paddingLeft: "1.2em",
          position: "relative",
        }}
      >
        <span
          style={{
            position: "absolute",
            left: 0,
            top: "0.6em",
            width: "0.45em",
            height: "0.45em",
            borderRadius: "50%",
            background: "currentColor",
            opacity: 0.5,
          }}
        />
        {it}
      </li>
    ))}
  </ul>
);

/* ---------- TARJETAS ---------- */
export const Tarjeta: React.FC<{
  area: string;
  colorArea: string;
  titulo: string;
  children: React.ReactNode;
}> = ({ area, colorArea, titulo, children }) => (
  <div
    style={{
      background: COLOR.cremaHonda,
      border: `1px solid ${COLOR.linea}`,
      borderRadius: u(2.4),
      padding: u(3),
      display: "flex",
      flexDirection: "column",
      gap: u(0.9),
      minWidth: 0,
    }}
  >
    <span
      style={{
        fontFamily: PALO,
        fontSize: u(1.95),
        fontWeight: 800,
        textTransform: "uppercase",
        letterSpacing: "0.16em",
        color: colorArea,
      }}
    >
      {area}
    </span>
    <h3
      style={{
        fontFamily: PALO,
        fontSize: u(2.79),
        fontWeight: 800,
        lineHeight: 1.25,
        color: COLOR.marronHondo,
        margin: 0,
      }}
    >
      {titulo}
    </h3>
    {children}
  </div>
);

export const TextoTarjeta: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p style={{ fontFamily: PALO, fontSize: u(2.47), color: COLOR.tintaTenue, lineHeight: 1.45, margin: 0 }}>
    {children}
  </p>
);

export const Rejilla: React.FC<{ columnas: number; children: React.ReactNode }> = ({
  columnas,
  children,
}) => (
  <div style={{ display: "grid", gap: u(2.2), gridTemplateColumns: `repeat(${columnas},1fr)` }}>
    {children}
  </div>
);

/* ---------- UTILIDADES DE TIEMPO ---------- */
/** Cuenta de un número a otro con frenada suave. */
export const cuenta = (frame: number, desde: number, hasta: number, arranque: number, dur: number) => {
  const k = interpolate(frame, [arranque, arranque + dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return Math.round(desde + (hasta - desde) * (1 - Math.pow(1 - k, 3)));
};

export { PALO, SERIF };
