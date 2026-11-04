import { useEffect, useRef } from "react";

/**
 * Cloudflare Turnstile, the check that keeps bots from creating accounts.
 * Off until the build has a site key and Supabase Auth has CAPTCHA protection
 * turned on with the matching secret; both are needed together.
 */
const SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY as string | undefined;
export const captchaEnabled = !!SITE_KEY;

interface Turnstile {
  render: (element: HTMLElement, options: Record<string, unknown>) => string;
  remove: (widgetId: string) => void;
}

declare global {
  interface Window {
    turnstile?: Turnstile;
  }
}

let scriptLoad: Promise<Turnstile> | null = null;

function loadTurnstile(): Promise<Turnstile> {
  scriptLoad ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
    script.async = true;
    script.onload = () => (window.turnstile ? resolve(window.turnstile) : reject(new Error("Turnstile did not load")));
    script.onerror = () => {
      scriptLoad = null;
      reject(new Error("Turnstile did not load"));
    };
    document.head.appendChild(script);
  });
  return scriptLoad;
}

/**
 * The check box. A token works once, so remount it (change its `key`) after
 * every attempt; until it reports a token the form should not be sent.
 */
export function Captcha({ onToken }: { onToken: (token: string | null) => void }) {
  const box = useRef<HTMLDivElement>(null);
  const callback = useRef(onToken);
  callback.current = onToken;

  useEffect(() => {
    if (!SITE_KEY) return;
    let widgetId: string | null = null;
    let isMounted = true;
    callback.current(null);
    loadTurnstile()
      .then((turnstile) => {
        if (!isMounted || !box.current) return;
        widgetId = turnstile.render(box.current, {
          sitekey: SITE_KEY,
          theme: document.documentElement.classList.contains("dark") ? "dark" : "light",
          callback: (token: string) => callback.current(token),
          "expired-callback": () => callback.current(null),
          "error-callback": () => callback.current(null),
        });
      })
      .catch(() => callback.current(null));
    return () => {
      isMounted = false;
      if (widgetId) window.turnstile?.remove(widgetId);
    };
  }, []);

  if (!SITE_KEY) return null;
  return <div ref={box} className="min-h-[65px]" />;
}
