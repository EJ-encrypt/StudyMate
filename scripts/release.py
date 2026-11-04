"""Put the committed code live: update the database, deploy to Vercel, check it answers.

Once the Vercel project is linked to GitHub, every push to main deploys by
itself, but without the database step. So day-to-day work is pushed to a
feature branch, and main is only pushed here, after the database is updated.
Before the link exists, the committed files are uploaded to Vercel directly.

Run from the StudyMate folder:

    backend\\.venv\\Scripts\\python scripts\\release.py

Reads DATABASE_URL (the Supabase session pooler string) and VERCEL_TOKEN from
.env. Deploys exactly what is committed (HEAD), not unsaved edits in the
folder, so what goes live is what is in git. Prints no secret values.
"""

import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "studymate"
APP_URL = "https://studymate-alpha-fawn.vercel.app"

# Optional settings copied from .env to Vercel on each release when present,
# so turning one on is: add it to .env, release. VITE_ ones are baked into
# the page at build time, so they must be in place before the build starts.
SYNCED_SETTINGS = ("SENTRY_DSN", "VITE_SENTRY_DSN", "VITE_TURNSTILE_SITE_KEY")


def step(text: str) -> None:
    print(f"\n== {text}")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def upload_deployment(api: httpx.Client, project_id: str) -> str:
    """Send the committed files straight to Vercel; used when no GitHub link exists."""
    files = []
    for path in git("ls-files").splitlines():
        data = subprocess.run(["git", "cat-file", "blob", f"HEAD:{path}"], cwd=ROOT, capture_output=True, check=True).stdout
        sha = hashlib.sha1(data).hexdigest()
        upload = api.post("/v2/files", content=data, headers={"x-vercel-digest": sha, "Content-Type": "application/octet-stream"})
        if upload.status_code >= 400:
            sys.exit(f"Upload of {path} failed ({upload.status_code})")
        files.append({"file": path, "sha": sha, "size": len(data)})
    print(f"   {len(files)} files uploaded.")
    deployment = api.post(
        "/v13/deployments",
        params={"forceNew": "1", "skipAutoDetectionConfirmation": "1"},
        json={
            "name": PROJECT,
            "project": project_id,
            "target": "production",
            "files": files,
            "projectSettings": {"framework": "vite"},
        },
    )
    deployment.raise_for_status()
    return deployment.json()["id"]


def github_deployment(api: httpx.Client, project_id: str) -> str | None:
    """Push HEAD to main and find the production build Vercel starts for it."""
    commit = git("rev-parse", "HEAD").strip()
    pushed = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, capture_output=True, text=True)
    if pushed.returncode != 0:
        sys.exit(f"Could not push to main:\n{pushed.stderr.strip()}")
    print("   Pushed to main; waiting for Vercel to start the build.")
    for _ in range(18):
        listing = api.get("/v6/deployments", params={"projectId": project_id, "target": "production", "limit": 10})
        for deployment in listing.json().get("deployments", []):
            if (deployment.get("meta") or {}).get("githubCommitSha") == commit:
                return deployment["uid"]
        time.sleep(10)
    # main was already at this commit, so GitHub sent nothing to build.
    return None


def main() -> None:
    env = dotenv_values(ROOT / ".env")
    for key in ("DATABASE_URL", "VERCEL_TOKEN"):
        if not env.get(key):
            sys.exit(f"{key} is missing from .env")

    if git("status", "--porcelain", "--untracked-files=no").strip():
        print("Note: there are uncommitted changes. Only committed code is deployed.")
    print("Deploying commit:", git("log", "--oneline", "-1").strip())

    step("1/3 Updating the database")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT / "backend",
        env={**os.environ, "DATABASE_URL": env["DATABASE_URL"]},
        capture_output=True,
        text=True,
    )
    for line in (result.stdout + result.stderr).splitlines():
        if "Running upgrade" in line or "Error" in line or "error" in line:
            print("  ", line.split("]")[-1].strip())
    if result.returncode != 0:
        sys.exit("Database update failed; nothing was deployed.")
    print("   Database is up to date.")

    step("2/3 Deploying to Vercel")
    api = httpx.Client(
        base_url="https://api.vercel.com",
        headers={"Authorization": f"Bearer {env['VERCEL_TOKEN']}"},
        timeout=120,
    )
    project = api.get(f"/v9/projects/{PROJECT}")
    project.raise_for_status()
    synced = [key for key in SYNCED_SETTINGS if env.get(key)]
    for key in synced:
        response = api.post(
            f"/v10/projects/{project.json()['id']}/env",
            params={"upsert": "true"},
            json={"key": key, "value": env[key], "type": "encrypted", "target": ["production", "preview"]},
        )
        if response.status_code >= 400:
            sys.exit(f"Could not set {key} on Vercel ({response.status_code})")
    if synced:
        print("   Settings updated on Vercel:", ", ".join(synced))
    project_id = project.json()["id"]
    deployment_id = None
    if project.json().get("link"):
        deployment_id = github_deployment(api, project_id)
    if deployment_id is None:
        deployment_id = upload_deployment(api, project_id)

    step("3/3 Building (2 to 4 minutes)")
    state = ""
    for _ in range(60):
        state = api.get(f"/v13/deployments/{deployment_id}").json().get("readyState", "")
        if state in ("READY", "ERROR", "CANCELED"):
            break
        time.sleep(10)
        print("   ...", state.lower() or "queued")
    if state != "READY":
        sys.exit(f"Build ended as {state}. See Vercel -> Deployments for the log.")

    health = httpx.get(f"{APP_URL}/api/health", timeout=30)
    print(f"   Site check: {health.status_code} {health.text.strip()}")
    print(f"\nLive at {APP_URL}")


if __name__ == "__main__":
    main()
