import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Providers } from "./app/Providers";
import { routes } from "./app/routes";
import "./styles/globals.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Providers>{routes}</Providers>
  </StrictMode>,
);
