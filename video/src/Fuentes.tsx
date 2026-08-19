import { continueRender, delayRender, staticFile } from "remotion";
import { useEffect, useState } from "react";

/**
 * Fraunces y Nunito, las de la marca, servidas desde public/fuentes.
 *
 * El delayRender es imprescindible: Remotion fotografía cada fotograma
 * en cuanto el componente está montado, y sin esperar a que las fuentes
 * estén cargadas los primeros fotogramas salen con la tipografía de
 * respaldo. Es un fallo que solo se ve en el vídeo final, nunca en el
 * estudio.
 */
export const Fuentes: React.FC = () => {
  const [espera] = useState(() => delayRender("Cargando Fraunces y Nunito"));

  useEffect(() => {
    const cargar = async () => {
      const caras = [
        new FontFace("Fraunces", `url(${staticFile("fuentes/fraunces-latin.woff2")})`, {
          weight: "400 700",
        }),
        new FontFace("Nunito", `url(${staticFile("fuentes/nunito-latin.woff2")})`, {
          weight: "400 800",
        }),
      ];
      await Promise.all(
        caras.map(async (cara) => {
          await cara.load();
          document.fonts.add(cara);
        })
      );
      continueRender(espera);
    };
    cargar();
  }, [espera]);

  return null;
};
