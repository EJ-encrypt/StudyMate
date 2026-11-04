import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { registerServiceWorker } from "./lib/push";
import { applyTheme, watchSystemTheme } from "./lib/theme";
import "katex/dist/katex.min.css";
import "./index.css";

applyTheme();
watchSystemTheme();

// Registered on every load so a reminder tapped on the lock screen can open
// the app, and so push keeps working after the browser updates the worker.
void registerServiceWorker();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
