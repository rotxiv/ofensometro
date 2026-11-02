// Las fuentes viajan dentro de la aplicación y el navegador solo descarga los subconjuntos que usa,
// sin pedir nada a internet. IBM Plex Sans: solo latino (cubre el español).
import "@fontsource/ibm-plex-sans/latin-400.css";
import "@fontsource/ibm-plex-sans/latin-500.css";
import "@fontsource/ibm-plex-sans/latin-600.css";
import "@fontsource-variable/source-serif-4/wght.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
