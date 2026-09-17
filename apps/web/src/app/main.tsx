import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import { AppProviders } from "./providers";
import "./styles/globals.css";

const container = document.getElementById("root");
if (!container) {
  throw new Error("Elemento #root não encontrado");
}

createRoot(container).render(
  <StrictMode>
    <AppProviders>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </AppProviders>
  </StrictMode>,
);
