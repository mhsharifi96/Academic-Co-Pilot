import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import { LangProvider } from "./i18n.js";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {/* Owns the en/fa choice and keeps <html lang/dir> in sync with it. */}
    <LangProvider>
      <App />
    </LangProvider>
  </React.StrictMode>
);
