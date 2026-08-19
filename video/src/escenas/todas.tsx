import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLOR, u } from "../marca";
import {
  Aparece,
  cuenta,
  Entradilla,
  Escena,
  Fuerte,
  Lista,
  PALO,
  Pie,
  Rejilla,
  Rotulo,
  SERIF,
  Tarjeta,
  TextoTarjeta,
  Titular,
} from "../piezas";

/* =======================================================
   Las doce escenas, una por diapositiva del deck.
   El texto es el mismo palabra por palabra que el de
   presentacion/apaisada.plantilla.html.
   ======================================================= */

const Portada: React.FC = () => (
  <Escena lado="derecha" ancho={u(92)} junta>
    <Aparece orden={0}><Rotulo>Proyecto Pipo · pipoweb.com</Rotulo></Aparece>
    <Aparece orden={1}>
      <Titular grande>
        Hay un búho
        <br />
        mirando tu web
      </Titular>
    </Aparece>
    <Aparece orden={2}>
      <Entradilla>
        Un analizador que revisa cualquier web desde fuera y cuenta en cristiano qué falla.
      </Entradilla>
    </Aparece>
  </Escena>
);

const Problema: React.FC = () => (
  <Escena ancho={u(100)}>
    <Aparece orden={0}><Rotulo>El problema</Rotulo></Aparece>
    <Aparece orden={1}>
      <Titular>
        Tu web habla de ti
        <br />
        cuando tú no estás
      </Titular>
    </Aparece>
    <Aparece orden={2}>
      <Entradilla>El dueño ve su página bonita. El visitante ve otra cosa.</Entradilla>
    </Aparece>
    <Aparece orden={3}>
      <Lista
        tam={u(2.73)}
        items={[
          "El candado del navegador dice «no seguro»",
          "Recoge datos de un formulario sin aviso legal ni cookies",
          "Tarda seis segundos en abrirse en el móvil",
          "Google no la encuentra por lo que el negocio hace",
        ]}
      />
    </Aparece>
    <Aparece orden={4}>
      <Pie>
        Y nadie se lo dice, porque para saberlo hay que ser técnico o pagar una auditoría.
      </Pie>
    </Aparece>
  </Escena>
);

const Idea: React.FC = () => (
  <Escena>
    <Aparece orden={0}><Rotulo>La idea</Rotulo></Aparece>
    <Aparece orden={1}>
      <Titular>
        Escribes tu dominio.
        <br />
        Un minuto después, lo sabes.
      </Titular>
    </Aparece>
    <Aparece orden={2}>
      <Rejilla columnas={3}>
        <Tarjeta area="Paso 1" colorArea={COLOR.ladrillo} titulo="Escribes la dirección">
          <TextoTarjeta>Nada que instalar, ninguna contraseña, ningún acceso.</TextoTarjeta>
        </Tarjeta>
        <Tarjeta area="Paso 2" colorArea={COLOR.ambar} titulo="Pipo mira desde fuera">
          <TextoTarjeta>Once comprobaciones a la vez, en poco más de un segundo.</TextoTarjeta>
        </Tarjeta>
        <Tarjeta area="Paso 3" colorArea={COLOR.salvia} titulo="Te lo cuenta">
          <TextoTarjeta>Semáforo, nota del 0 al 100 e informe escrito sin jerga.</TextoTarjeta>
        </Tarjeta>
      </Rejilla>
    </Aparece>
    <Aparece orden={3}>
      <Pie>Gratis, sin registro y sin dejar el correo.</Pie>
    </Aparece>
  </Escena>
);

const Marca: React.FC<{ tipo: "cruz" | "visto" }> = ({ tipo }) => (
  <span
    style={{
      flexShrink: 0,
      width: u(2.9),
      height: u(2.9),
      borderRadius: "50%",
      border: tipo === "cruz" ? `${u(0.22)}px solid ${COLOR.ladrillo}` : "none",
      background: tipo === "visto" ? COLOR.salvia : "transparent",
      color: tipo === "cruz" ? COLOR.ladrillo : COLOR.crema,
      display: "grid",
      placeItems: "center",
      fontFamily: PALO,
      fontSize: u(1.95),
      fontWeight: 800,
      marginTop: u(0.35),
    }}
  >
    {tipo === "cruz" ? "✕" : "✓"}
  </span>
);

const Regla: React.FC = () => (
  <Escena lado="derecha" ancho={u(100)}>
    <Aparece orden={0}><Rotulo>La regla que lo gobierna todo</Rotulo></Aparece>
    <Aparece orden={1}>
      <Titular>
        Pipo mira.
        <br />
        Nunca entra.
      </Titular>
    </Aparece>
    <Aparece orden={2}>
      <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: u(1.6), margin: 0, padding: 0 }}>
        {["Nunca prueba contraseñas", "Nunca busca agujeros por los que colarse", "Nunca toca el servidor de nadie"].map(
          (t) => (
            <li key={t} style={{ display: "flex", alignItems: "flex-start", gap: u(1.4), fontFamily: PALO, fontSize: u(2.73), color: COLOR.tintaTenue }}>
              <Marca tipo="cruz" />
              <span>{t}</span>
            </li>
          )
        )}
      </ul>
    </Aparece>
    <Aparece orden={3}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: u(1.4), fontFamily: PALO, fontSize: u(2.73), color: COLOR.marronHondo, fontWeight: 700 }}>
        <Marca tipo="visto" />
        <span>
          Solo lee lo que tu web ya le enseña
          <br />a cualquier visitante y a Google
        </span>
      </div>
    </Aparece>
    <Aparece orden={4}>
      <Pie>
        Es una decisión legal, no una limitación técnica: sin vulnerar ninguna medida de seguridad,
        no hay delito (art. 197 bis CP). Toda la arquitectura está construida sobre esa línea.
      </Pie>
    </Aparece>
  </Escena>
);

const Revisa: React.FC = () => (
  <Escena>
    <Aparece orden={0}><Rotulo>Qué revisa</Rotulo></Aparece>
    <Aparece orden={1}>
      <Titular>
        Once comprobaciones,
        <br />
        tres preguntas
      </Titular>
    </Aparece>
    <Aparece orden={2}>
      <Rejilla columnas={3}>
        <Tarjeta area="¿Es segura?" colorArea={COLOR.ladrillo} titulo="Seguridad">
          <Lista items={["Certificado y cifrado", "Cabeceras del servidor", "Correo suplantable (SPF, DKIM, DMARC)", "Gestor desactualizado"]} />
        </Tarjeta>
        <Tarjeta area="¿Cumple la ley?" colorArea={COLOR.ambar} titulo="Cumplimiento">
          <Lista items={["Aviso legal y privacidad", "Aviso de cookies real", "Rastreadores de terceros", "Accesibilidad básica"]} />
        </Tarjeta>
        <Tarjeta area="¿Te trae clientes?" colorArea={COLOR.salvia} titulo="Clientes">
          <Lista items={["SEO técnico", "Móvil y velocidad", "Teléfono pulsable", "Formularios sin cifrar"]} />
        </Tarjeta>
      </Rejilla>
    </Aparece>
    <Aparece orden={3}>
      <Pie>
        Las tres familias no son decorativas: deciden el color del semáforo. Un detalle de SEO no
        puede pintar de rojo un informe entero.
      </Pie>
    </Aparece>
  </Escena>
);

const Nota: React.FC = () => {
  const frame = useCurrentFrame();
  // El aro se rellena hasta 87 sobre 100. 339,3 es el perímetro del
  // círculo de radio 54; 44 es lo que queda sin pintar en el 87%.
  const resto = interpolate(frame, [18, 68], [339.3, 44], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const numero = cuenta(frame, 0, 87, 18, 50);
  return (
    <Escena>
      <Aparece orden={0}><Rotulo>La nota</Rotulo></Aparece>
      <Aparece orden={1}>
        <Titular>
          Un número que
          <br />
          no se inventa nadie
        </Titular>
      </Aparece>
      <Aparece orden={2}>
        <div style={{ display: "flex", alignItems: "center", gap: u(5) }}>
          <div style={{ position: "relative", width: u(34), height: u(34), flexShrink: 0 }}>
            <svg viewBox="0 0 120 120" style={{ width: "100%", height: "100%", transform: "rotate(-90deg)" }}>
              <circle cx={60} cy={60} r={54} fill="none" stroke={COLOR.cremaHonda} strokeWidth={11} />
              <circle
                cx={60}
                cy={60}
                r={54}
                fill="none"
                stroke={COLOR.salvia}
                strokeWidth={11}
                strokeLinecap="round"
                strokeDasharray={339.3}
                strokeDashoffset={resto}
              />
            </svg>
            <div style={{ position: "absolute", inset: 0, display: "grid", placeContent: "center", textAlign: "center" }}>
              <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: u(9.62), lineHeight: 1, color: COLOR.marronHondo, fontVariantNumeric: "tabular-nums", fontVariationSettings: '"opsz" 144' }}>
                {numero}
              </div>
              <div style={{ fontFamily: PALO, fontSize: u(1.89), textTransform: "uppercase", letterSpacing: "0.17em", color: COLOR.tintaDebil, marginTop: u(0.5) }}>
                sobre 100
              </div>
            </div>
          </div>
          <Lista
            tam={u(2.73)}
            hueco={u(1.1)}
            items={[
              "La calcula una fórmula fija, siempre la misma",
              "Cada comprobación pesa lo que le toca: un certificado caducado no vale lo mismo que un título largo",
              "La misma web, el mismo día, da la misma nota",
            ]}
          />
        </div>
      </Aparece>
      <Aparece orden={3}>
        <Pie>
          La inteligencia artificial escribe el informe, pero <Fuerte>no pone la nota</Fuerte>. Si la
          pusiera ella, no podría defenderse delante de un cliente.
        </Pie>
      </Aparece>
    </Escena>
  );
};

const Traducido: React.FC = () => (
  <Escena>
    <Aparece orden={0}><Rotulo>El informe</Rotulo></Aparece>
    <Aparece orden={1}>
      <Titular>
        Escrito para ti,
        <br />
        no para tu informático
      </Titular>
    </Aparece>
    <Aparece orden={2}>
      <div style={{ display: "grid", gap: u(2.2), gridTemplateColumns: "1fr 1fr" }}>
        <div style={{ background: COLOR.cremaHonda, border: `1px solid ${COLOR.linea}`, borderRadius: u(2.4), padding: u(3), display: "flex", flexDirection: "column", gap: u(1.2) }}>
          <span style={{ fontFamily: PALO, fontSize: u(1.89), fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.17em", color: COLOR.tintaDebil }}>
            Lo que dice una herramienta
          </span>
          <p style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: u(2.21), lineHeight: 1.7, color: COLOR.tintaDebil, margin: 0 }}>
            Missing HSTS header.
            <br />
            CSP not set.
            <br />
            SPF record absent.
            <br />
            TLS 1.0 enabled.
          </p>
        </div>
        <div style={{ background: "linear-gradient(160deg,rgba(217,164,65,.24),rgba(201,123,90,.12))", border: "1px solid rgba(201,123,90,.4)", borderRadius: u(2.4), padding: u(3), display: "flex", flexDirection: "column", gap: u(1.2) }}>
          <span style={{ fontFamily: PALO, fontSize: u(1.89), fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.17em", color: COLOR.terracota }}>
            Lo que dice Pipo
          </span>
          <p style={{ fontFamily: PALO, fontSize: u(2.67), lineHeight: 1.5, color: COLOR.marronHondo, margin: 0 }}>
            Cualquiera puede mandar correos que parezcan tuyos, con tu propio dominio. Tus clientes
            no notarían la diferencia.
          </p>
        </div>
      </div>
    </Aparece>
    <Aparece orden={3}>
      <Pie>
        Un hallazgo que no se entiende no se arregla. La traducción no es un adorno: es el producto.
      </Pie>
    </Aparece>
  </Escena>
);

const Honestidad: React.FC = () => (
  <Escena lado="derecha" ancho={u(100)}>
    <Aparece orden={0}><Rotulo>La parte difícil</Rotulo></Aparece>
    <Aparece orden={1}>
      <Titular>
        Si Pipo no puede
        <br />
        comprobarlo, lo dice
      </Titular>
    </Aparece>
    <Aparece orden={2}>
      <Entradilla>Acusar en falso cuesta la venta entera y la credibilidad con ella.</Entradilla>
    </Aparece>
    <Aparece orden={3}>
      <Lista
        tam={u(2.73)}
        hueco={u(1.1)}
        items={[
          "Una web hecha con React llega vacía: eso no es «no tienes textos», es «no lo hemos podido ver»",
          "Casi todos los avisos de cookies se cargan después: buscar la palabra «aceptar» acusaba justo a quien sí cumple",
          "Una página de error de 125 bytes no es la web del cliente",
        ]}
      />
    </Aparece>
    <Aparece orden={4}>
      <Pie>
        Ocho de estos fallos salieron de comprobar a mano, con <Fuerte>curl</Fuerte> y{" "}
        <Fuerte>dig</Fuerte>, lo que decía la nota. Ninguno se veía leyendo el código.
      </Pie>
    </Aparece>
  </Escena>
);

const Campo: React.FC = () => {
  const frame = useCurrentFrame();
  const datos: [string, string, number][] = [
    ["69", "de nota media sobre 100", 69],
    ["87%", "con algún fallo grave", 87],
    ["42%", "sin aviso legal ni cookies", 42],
  ];
  return (
    <Escena>
      <Aparece orden={0}><Rotulo>Prueba de campo</Rotulo></Aparece>
      <Aparece orden={1}>
        <Titular>
          Cómo está la web
          <br />
          de la pyme media
        </Titular>
      </Aparece>
      <Aparece orden={2}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: u(2.2) }}>
          {datos.map(([texto, etiqueta, valor], i) => (
            <div key={etiqueta} style={{ background: COLOR.cremaHonda, border: `1px solid ${COLOR.linea}`, borderRadius: u(2.4), padding: u(3), display: "flex", flexDirection: "column", gap: u(0.6) }}>
              <b style={{ fontFamily: SERIF, fontWeight: 600, fontSize: u(7.28), lineHeight: 1, color: COLOR.terracota, fontVariantNumeric: "tabular-nums" }}>
                {cuenta(frame, 0, valor, 22 + i * 8, 45)}
                {texto.endsWith("%") ? "%" : ""}
              </b>
              <span style={{ fontFamily: PALO, fontSize: u(2.34), color: COLOR.tintaTenue, lineHeight: 1.35 }}>
                {etiqueta}
              </span>
            </div>
          ))}
        </div>
      </Aparece>
      <Aparece orden={3}>
        <Pie>
          Muestra de 38 pequeños negocios con web —gestorías, clínicas, talleres—, medida solo con
          lo que esas páginas le enseñan a cualquier visitante.{" "}
          <Fuerte>Cifras agregadas: aquí no se nombra a ningún negocio, ni se hace.</Fuerte> Cada
          hallazgo se verificó a mano antes de darlo por bueno.
        </Pie>
      </Aparece>
    </Escena>
  );
};

const Algodon: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <Escena ancho={u(100)}>
      <Aparece orden={0}><Rotulo>La prueba del algodón</Rotulo></Aparece>
      <Aparece orden={1}>
        <Titular>
          Pipo se escaneó a sí mismo.
          <br />Y suspendió.
        </Titular>
      </Aparece>
      <Aparece orden={2}>
        <div style={{ display: "flex", alignItems: "center", gap: u(3.4) }}>
          <span style={{ fontFamily: SERIF, fontWeight: 600, fontSize: u(14.3), lineHeight: 1, color: COLOR.ladrillo, opacity: 0.55, fontVariantNumeric: "tabular-nums" }}>
            71
          </span>
          <span style={{ fontFamily: PALO, fontSize: u(5.2), color: COLOR.tintaDebil }}>→</span>
          <span style={{ fontFamily: SERIF, fontWeight: 600, fontSize: u(14.3), lineHeight: 1, color: COLOR.salvia, fontVariantNumeric: "tabular-nums" }}>
            {cuenta(frame, 71, 87, 30, 42)}
          </span>
        </div>
      </Aparece>
      <Aparece orden={3}>
        <Pie>
          El zapatero iba descalzo: faltaban las cabeceras de seguridad y las fuentes venían de un
          tercero. Se arregló lo que el propio Pipo señaló. Como la fórmula es fija, se pudo{" "}
          <Fuerte>predecir el 87 exacto antes de tocar una línea</Fuerte>.
        </Pie>
      </Aparece>
    </Escena>
  );
};

const Nivel: React.FC<{ nombre: string; precio: string; que: string; etiqueta?: string }> = ({
  nombre,
  precio,
  que,
  etiqueta,
}) => (
  <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: `${u(0.5)}px ${u(2)}px`, alignItems: "baseline", padding: `${u(2.3)}px 0`, borderBottom: `1px solid ${COLOR.linea}` }}>
    <span style={{ fontFamily: SERIF, fontWeight: 600, fontSize: u(3.51), color: COLOR.marronHondo }}>
      {nombre}
      {etiqueta ? (
        <span style={{ display: "inline-block", fontFamily: PALO, fontSize: u(1.49), fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.13em", color: COLOR.crema, background: COLOR.marron, borderRadius: 999, padding: "0.25em 0.8em", marginLeft: "0.6em", verticalAlign: "middle" }}>
          {etiqueta}
        </span>
      ) : null}
    </span>
    <span style={{ fontFamily: PALO, fontWeight: 800, fontSize: u(2.6), color: COLOR.terracota, whiteSpace: "nowrap" }}>
      {precio}
    </span>
    <span style={{ gridColumn: "1/-1", fontFamily: PALO, fontSize: u(2.34), color: COLOR.tintaTenue, lineHeight: 1.4 }}>
      {que}
    </span>
  </div>
);

const Modelo: React.FC = () => (
  <Escena junta>
    <Aparece orden={0}><Rotulo>Cómo se sostiene</Rotulo></Aparece>
    <Aparece orden={1}>
      <Titular>
        Gratis lo que informa.
        <br />
        Se paga lo que se arregla.
      </Titular>
    </Aparece>
    <Aparece orden={2}>
      <div>
        <Nivel nombre="Revisión" precio="Gratis" que="Semáforo, nota, informe interpretado e informe en PDF." />
        <Nivel
          nombre="Te lo arreglamos"
          precio="89 – 149 €"
          que="Se aplican los cambios y se enseña el antes y el después. Se presupuesta antes; no se cobra nada por adelantado."
        />
        <Nivel
          nombre="Tranquilidad"
          etiqueta="En preparación"
          precio="15 – 25 €/mes"
          que="Revisión mensual, avisos si algo empeora y arreglos pequeños incluidos."
        />
      </div>
    </Aparece>
    <Aparece orden={3}>
      <Pie>
        El diagnóstico cuesta céntimos de generar, así que regalarlo entero es lo que abre la
        conversación.
      </Pie>
    </Aparece>
  </Escena>
);

const Cierre: React.FC = () => (
  <Escena lado="derecha" ancho={u(92)} junta>
    <Aparece orden={0}><Rotulo>Pruébalo con tu propia web</Rotulo></Aparece>
    <Aparece orden={1}>
      <Titular>
        Dale a Pipo el nombre
        <br />
        de tu web
      </Titular>
    </Aparece>
    <Aparece orden={2}>
      <p style={{ fontFamily: SERIF, fontWeight: 600, fontSize: u(7.02), color: COLOR.terracota, letterSpacing: "-0.02em", margin: 0, lineHeight: 1.04 }}>
        www.pipoweb.com
      </p>
    </Aparece>
  </Escena>
);

export const CONTENIDOS: Record<string, React.FC> = {
  portada: Portada,
  problema: Problema,
  idea: Idea,
  regla: Regla,
  revisa: Revisa,
  nota: Nota,
  traducido: Traducido,
  honestidad: Honestidad,
  campo: Campo,
  algodon: Algodon,
  modelo: Modelo,
  cierre: Cierre,
};
