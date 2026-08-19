import React from "react";
import { COLOR, Gesto } from "./marca";

type Props = {
  gesto: Gesto;
  /** 1 = ojo abierto, 0 = cerrado */
  parpadeo: number;
  /** grados de aleteo extra mientras vuela */
  aleteo: number;
  /** balanceo de la lupa, de -1 a 1 */
  lupa: number;
};

/**
 * El búho, dibujado pieza a pieza para poder moverle los ojos, las cejas,
 * las alas y la lupa por separado. Es el mismo SVG de la presentación y
 * de la landing; lo que cambia es que aquí nada se anima con CSS: todo
 * llega ya calculado desde el fotograma actual, porque Remotion compone
 * el vídeo cuadro a cuadro y una animación de CSS no avanzaría con él.
 */
export const Pipo: React.FC<Props> = ({ gesto, parpadeo, aleteo, lupa }) => {
  // Gestos: los mismos que en presentacion/apaisada.plantilla.html
  const pupila =
    gesto === "mira" ? { x: -5, y: 3 } : gesto === "alerta" ? { x: 0, y: -2 } : { x: 0, y: 0 };
  const cejaIzq = gesto === "alerta" ? 11 : 0;
  const cejaDer = gesto === "alerta" ? -11 : 0;
  const cejaSube = gesto === "orgullo" ? -4 : 0;
  const alaIzq = (gesto === "saluda" ? 8 : gesto === "orgullo" ? -6 : 0) - aleteo;
  const alaDer = (gesto === "saluda" ? -32 : gesto === "orgullo" ? 6 : 0) + aleteo;

  const ojo = (cx: number, pupilaCx: number, brilloCx: number) => (
    <g transform={`translate(${cx} 120) scale(1 ${parpadeo}) translate(${-cx} -120)`}>
      <circle cx={cx} cy={120} r={30} fill="#fff" />
      <circle
        cx={pupilaCx + pupila.x}
        cy={122 + pupila.y}
        r={15}
        fill={COLOR.tinta}
      />
      <circle cx={brilloCx} cy={117} r={5} fill="#fff" />
    </g>
  );

  return (
    <svg viewBox="0 0 240 260" style={{ width: "100%", height: "100%", overflow: "visible" }}>
      <ellipse cx={120} cy={150} rx={82} ry={90} fill={COLOR.marron} />
      <ellipse cx={120} cy={162} rx={58} ry={66} fill="#E8D6BF" />
      <path d="M54 82 Q44 40 78 60 Q70 84 54 82Z" fill={COLOR.marronHondo} />
      <path d="M186 82 Q196 40 162 60 Q170 84 186 82Z" fill={COLOR.marronHondo} />

      <g transform={`rotate(${cejaIzq} 93 86) translate(0 ${cejaSube})`}>
        <path d="M70 92 Q92 80 116 92" stroke={COLOR.marronHondo} strokeWidth={6} fill="none" strokeLinecap="round" />
      </g>
      <g transform={`rotate(${cejaDer} 147 86) translate(0 ${cejaSube})`}>
        <path d="M124 92 Q148 80 170 92" stroke={COLOR.marronHondo} strokeWidth={6} fill="none" strokeLinecap="round" />
      </g>

      {ojo(92, 95, 100)}
      {ojo(148, 145, 150)}

      <path d="M120 132 L110 150 Q120 158 130 150Z" fill={COLOR.ambar} />

      <g transform={`rotate(${alaIzq} 48 150)`}>
        <path d="M40 140 Q22 170 44 200 Q52 170 56 150Z" fill={COLOR.marronHondo} />
      </g>
      <g transform={`rotate(${alaDer} 192 150)`}>
        <path d="M200 140 Q218 170 196 200 Q188 170 184 150Z" fill={COLOR.marronHondo} />
      </g>

      <path d="M100 236 l0 14 M92 250 h16" stroke={COLOR.ambar} strokeWidth={5} strokeLinecap="round" />
      <path d="M140 236 l0 14 M132 250 h16" stroke={COLOR.ambar} strokeWidth={5} strokeLinecap="round" />

      <g transform={`translate(${lupa * -10} ${lupa * 6}) rotate(${lupa * -11} 182 196)`}>
        <circle cx={182} cy={196} r={26} fill="none" stroke={COLOR.terracota} strokeWidth={7} />
        <circle cx={182} cy={196} r={20} fill="rgba(217,164,65,.18)" />
        <line x1={200} y1={214} x2={222} y2={238} stroke={COLOR.terracota} strokeWidth={9} strokeLinecap="round" />
      </g>
    </svg>
  );
};
