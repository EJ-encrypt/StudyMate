import { useEffect, useState } from "react";

import { useAuth } from "../context/AuthContext";
import { Alert } from "./ui";

let providerCheck: Promise<boolean> | null = null;

/**
 * Whether Google sign-in is switched on in Supabase. Asked once per visit, so
 * the button only appears after the provider has been set up in the dashboard.
 */
function googleEnabled(): Promise<boolean> {
  const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
  const key = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;
  if (!url || !key) return Promise.resolve(false);
  providerCheck ??= fetch(`${url}/auth/v1/settings`, { headers: { apikey: key } })
    .then((response) => (response.ok ? response.json() : null))
    .then((settings) => !!settings?.external?.google)
    .catch(() => {
      providerCheck = null;
      return false;
    });
  return providerCheck;
}

function GoogleMark() {
  return (
    <svg viewBox="0 0 48 48" className="h-[18px] w-[18px]" aria-hidden>
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}

/** "Continue with Google", for signing in and signing up alike, with an "or" rule under it. */
export default function GoogleSignIn() {
  const { signInWithGoogle } = useAuth();
  const [isEnabled, setIsEnabled] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    void googleEnabled().then((enabled) => isMounted && setIsEnabled(enabled));
    return () => {
      isMounted = false;
    };
  }, []);

  if (!isEnabled) return null;

  async function start() {
    setError(null);
    setIsLeaving(true);
    try {
      await signInWithGoogle();
    } catch (err) {
      setError((err as Error).message || "Could not reach Google. Please try again.");
      setIsLeaving(false);
    }
  }

  return (
    <div className="mb-5">
      <button type="button" onClick={() => void start()} disabled={isLeaving} className="btn-secondary w-full py-2.5">
        <GoogleMark />
        {isLeaving ? "Opening Google..." : "Continue with Google"}
      </button>
      {error && (
        <div className="mt-2">
          <Alert>{error}</Alert>
        </div>
      )}
      <div className="mt-5 flex items-center gap-3 text-xs font-semibold uppercase tracking-wide text-ink/40">
        <span className="h-px flex-1 bg-ink/10" />
        or with email
        <span className="h-px flex-1 bg-ink/10" />
      </div>
    </div>
  );
}
