import React from "react";
import {
  AbsoluteFill,
  interpolate,
  Sequence,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { ALTO, ANCHO, ARRANQUES, ESCENAS, u } from "./marca";
import { Fondo, Hojas } from "./piezas";
import { Fuentes } from "./Fuentes";
import { Pipo } from "./Pipo";
import { CONTENIDOS } from "./escenas/todas";

/** Cuántos fotogramas se solapan dos escenas al cambiar. */
const CRUCE = 10;

/* =======================================================
   EL BÚHO QUE VUELA POR TODO EL VÍDEO

   Pipo vive fuera de las escenas, en una capa propia. Por eso puede
   cruzar el corte entre una diapositiva y la siguiente: no se corta y
   vuelve a aparecer, se desplaza. Es lo que convierte doce láminas en
   una sola presentación.
   ======================================================= */
const PipoVolando: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // En qué escena estamos
  let i = 0;
  while (i + 1 < ESCENAS.length && frame >= ARRANQUES[i + 1]) i++;
  const local = frame - ARRANQUES[i];
  const desde = ESCENAS[Math.max(0, i - 1)].pipo;
  const hasta = ESCENAS[i].pipo;

  // Muelle con un pelín de rebote al llegar: un vuelo que frena en seco
  // parece un objeto, no un bicho.
  const p = spring({ frame: local, fps, config: { damping: 17, mass: 1.1, stiffness: 65 } });
  const recorrido = Math.hypot(hasta.x - desde.x, hasta.y - desde.y);

  const entre = (a: number, b: number) => a + (b - a) * p;
  const x = entre(desde.x, hasta.x);
  const escala = entre(desde.escala, hasta.escala);
  const opacidad = entre(desde.opacidad, hasta.opacidad);

  // Sube un poco a mitad de trayecto: un vuelo describe un arco, no
  // una línea recta. Solo si de verdad se está desplazando.
  const arco = -Math.sin(Math.PI * Math.min(1, p)) * (recorrido > 200 ? 70 : 12);
  // Y respira flotando cuando está posado (6 s por ciclo, como en el deck)
  const flote = Math.sin((frame / (6 * fps)) * Math.PI * 2) * 17;
  const y = entre(desde.y, hasta.y) + arco + flote;

  // Aletea mientras vuela y para al posarse
  const aleteo = recorrido > 150 && p < 0.92 ? Math.sin(local * 0.9) * 26 * (1 - p) : 0;

  // Parpadeo con ritmo irregular: dos seguidos y una pausa larga
  const ciclo = ((frame % (7 * fps)) / (7 * fps)) * 100;
  const cerrado = (a: number, b: number) => ciclo > a && ciclo < b;
  const parpadeo = cerrado(2, 3.2) || cerrado(5.4, 6.6) ? 0.08 : 1;

  // La lupa rastrea despacio
  const lupa = Math.sin((frame / (5 * fps)) * Math.PI * 2);

  const ancho = u(34);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: ANCHO / 2,
          top: ALTO / 2,
          width: ancho,
          height: (ancho * 260) / 240,
          opacity: opacidad,
          transform: `translate(-50%,-50%) translate(${x}px, ${y}px) scale(${escala})`,
          filter: "drop-shadow(0 32px 43px rgba(111,78,55,.32))",
        }}
      >
        {/* Halo cálido, el mismo que lleva en la landing */}
        <div
          style={{
            position: "absolute",
            inset: "-34%",
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(217,164,65,.30), transparent 62%)",
          }}
        />
        {/* position:relative no es decorativo: sin él, el halo de arriba
            —que sí está posicionado— se pinta POR ENCIMA del búho y lo
            deja lavado, con la pupila en un marrón claro en vez de en
            el color de tinta. Se ve comparando píxeles, no a ojo. */}
        <div style={{ position: "relative", width: "100%", height: "100%" }}>
          <Pipo gesto={ESCENAS[i].gesto} parpadeo={parpadeo} aleteo={aleteo} lupa={lupa} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** Una escena, que entra fundiéndose sobre la anterior. */
const Lamina: React.FC<{ indice: number; children: React.ReactNode }> = ({ indice, children }) => {
  const frame = useCurrentFrame();
  const dur = ESCENAS[indice].duracion;
  const entra = interpolate(frame, [0, 9], [0, 1], { extrapolateRight: "clamp" });
  const sale = interpolate(frame, [dur, dur + CRUCE], [1, 0], { extrapolateLeft: "clamp" });
  return <AbsoluteFill style={{ opacity: entra * sale }}>{children}</AbsoluteFill>;
};

export const Presentacion: React.FC = () => (
  <AbsoluteFill>
    <Fuentes />
    <Fondo />
    {/* Las hojas van por debajo del texto y por encima del fondo, y no
        se reinician en cada escena: son de todo el vídeo. */}
    <Hojas />

    {ESCENAS.map((escena, i) => {
      const Contenido = CONTENIDOS[escena.id];
      return (
        <Sequence
          key={escena.id}
          from={ARRANQUES[i]}
          durationInFrames={escena.duracion + CRUCE}
          name={escena.id}
        >
          <Lamina indice={i}>
            <Contenido />
          </Lamina>
        </Sequence>
      );
    })}

    <PipoVolando />
  </AbsoluteFill>
);
