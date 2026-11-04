"""Apply StudyMate's sign-in settings to the Supabase project.

Run from the StudyMate folder after changing any of the keys below in .env:

    backend\\.venv\\Scripts\\python scripts\\configure_auth.py

Always sets:
- passwords of at least 8 characters, so the server enforces what the app asks;
- the app's address as an allowed place to return to after Google sign-in,
  email confirmation and password reset.
Turns on, when their keys are in .env:
- Google sign-in: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET;
- CAPTCHA on sign-up and sign-in: TURNSTILE_SECRET_KEY (the site key goes in
  VITE_TURNSTILE_SITE_KEY, which the next release passes to the page).

Uses SUPABASE_ACCESS_TOKEN (a personal access token from Supabase, Account,
Access Tokens) and SUPABASE_URL. Prints setting names, never their values.
"""

import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
APP_URL = "https://studymate-alpha-fawn.vercel.app"
MIN_PASSWORD = 8


def main() -> None:
    env = dotenv_values(ROOT / ".env")
    token, supabase_url = env.get("SUPABASE_ACCESS_TOKEN"), env.get("SUPABASE_URL")
    if not (token and supabase_url):
        sys.exit("SUPABASE_ACCESS_TOKEN and SUPABASE_URL must be in .env")
    ref = urlparse(supabase_url).hostname.split(".")[0]

    api = httpx.Client(base_url="https://api.supabase.com", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    current = api.get(f"/v1/projects/{ref}/config/auth")
    if current.status_code != 200:
        sys.exit(f"Could not read the sign-in settings ({current.status_code}). Check SUPABASE_ACCESS_TOKEN.")
    config = current.json()

    allowed = [entry for entry in (config.get("uri_allow_list") or "").split(",") if entry]
    for entry in (f"{APP_URL}/**", "http://localhost:5173/**"):
        if entry not in allowed:
            allowed.append(entry)

    changes: dict = {
        "password_min_length": max(MIN_PASSWORD, config.get("password_min_length") or 0),
        "site_url": config.get("site_url") or APP_URL,
        "uri_allow_list": ",".join(allowed),
    }
    turned_on = []
    if env.get("GOOGLE_CLIENT_ID") and env.get("GOOGLE_CLIENT_SECRET"):
        changes.update(
            external_google_enabled=True,
            external_google_client_id=env["GOOGLE_CLIENT_ID"],
            external_google_secret=env["GOOGLE_CLIENT_SECRET"],
        )
        turned_on.append("Google sign-in")
    if env.get("TURNSTILE_SECRET_KEY"):
        if not env.get("VITE_TURNSTILE_SITE_KEY"):
            sys.exit("TURNSTILE_SECRET_KEY is set but VITE_TURNSTILE_SITE_KEY is not; set both, or neither.")
        changes.update(
            security_captcha_enabled=True,
            security_captcha_provider="turnstile",
            security_captcha_secret=env["TURNSTILE_SECRET_KEY"],
        )
        turned_on.append("CAPTCHA (release next, so the page shows the check)")

    updated = api.patch(f"/v1/projects/{ref}/config/auth", json=changes)
    if updated.status_code >= 400:
        sys.exit(f"Supabase refused the settings ({updated.status_code}): {updated.text[:300]}")
    print(f"Passwords: at least {changes['password_min_length']} characters.")
    print("Allowed return addresses:", ", ".join(allowed))
    print("Turned on:", ", ".join(turned_on) if turned_on else "nothing new (no Google or Turnstile keys in .env)")


if __name__ == "__main__":
    main()
