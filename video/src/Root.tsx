import React from "react";
import { Composition } from "remotion";
import { ALTO, ANCHO, DURACION_TOTAL, FPS } from "./marca";
import { Presentacion } from "./Presentacion";

export const Root: React.FC = () => (
  <Composition
    id="Presentacion"
    component={Presentacion}
    durationInFrames={DURACION_TOTAL}
    fps={FPS}
    width={ANCHO}
    height={ALTO}
  />
);
