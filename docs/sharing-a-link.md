# Giving people a link to try StudyMate

The development setup (`docker compose up`) runs on `localhost`, which means
"this computer" — nobody else can open it. This describes how to get a URL
you can send to someone, and the constraints that come with each option.

## Read this first: the quota problem

Concept extraction, question generation and short-answer marking all call
the Gemini API. On a free-tier key the app already hits rate limits with a
single user; several people uploading at once will hit them constantly.

The app handles this as gracefully as it can — failures now say *"The AI
service has hit its usage limit for now. Nothing is lost — wait a minute and
try again"* with a **Try again** button, rather than showing a raw API error.
But a participant who spends their session retrying has not tested your
interface.

If the sessions matter, enabling pay-as-you-go billing on the Google AI
Studio key removes this for a handful of testers at trivial cost. That is a
judgement call about the project's constraints, not a technical requirement.

Either way: **log every rate-limit failure during a session as an
infrastructure event, not a usability defect.** They are not the same finding.

---

## Option 1 (recommended for scheduled sessions): tunnel your own machine

A tunnel publishes a public HTTPS URL that forwards to the app running on
your laptop. Nothing is deployed, nothing is copied to a third party, and
all data stays on your machine — which also keeps your ethics position
simple.

**Trade-off:** your machine has to be on and running the app while people
are using it. For scheduled sessions that is not a real constraint.

### 1. Prepare the environment

```bash
cp .env.example .env
```

Edit `.env`:

- `GEMINI_API_KEY` — your key.
- `ENVIRONMENT=production`
- `JWT_SECRET` — a real secret. Generate one with:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```
  The app **refuses to start** in production on the example value, because
  anyone who knows it could mint a login token for any account.
- `VITE_API_BASE_URL=` — leave empty. In this mode the API serves the
  frontend, so it calls its own origin.

### 2. Run the production stack

```bash
docker compose -f docker-compose.prod.yml up --build
```

This differs from the development stack in three ways: the frontend is a
built static bundle served by the API rather than a Vite dev server, so the
whole app lives on **one** origin and needs no CORS; uploads live on a named
volume that survives restarts; and services restart automatically.

Check it: http://localhost:9000 should load the app itself, not just the API.

### 3. Open the tunnel

Install [`cloudflared`](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/),
then:

```bash
cloudflared tunnel --url http://localhost:9000
```

It prints a `https://something-random.trycloudflare.com` URL. That is the
link to send. No Cloudflare account is needed for a quick tunnel.

**The URL changes every time you restart the tunnel.** Start it once and
leave it running for the whole study, or use a named tunnel (which needs a
free Cloudflare account) if you want a stable address.

### 4. Before sending it to anyone

- Open the URL on your **phone**, on mobile data rather than your wi-fi.
  That is the only way to be sure it works from outside your network.
- Register a throwaway account through the tunnel and run one upload end to
  end. Cold-start slowness and a misconfigured API base URL both show up
  here and nowhere else.
- Remember that anyone with the link can register. Do not leave a tunnel
  running unattended for days.

---

## Option 2: host it properly

Do this if you need the app reachable when your machine is off — for
instance if participants will use it in their own time over a week.

**Render's free tier will not work for this app.** Worth stating plainly,
because it is the obvious choice and it fails in ways that would ruin a
study mid-flight:

| Free-tier limit | Consequence here |
|---|---|
| Postgres expires 30 days after creation, then is deleted | Your study data disappears mid-study |
| No persistent disks | Uploaded files vanish on restart, and the worker reads files from disk, so processing fails |
| Services sleep after 15 min, ~1 min cold start | A participant opens your link, waits a minute, assumes it is broken |
| Redis has no persistence | Queued extraction jobs are lost on restart |

Four of the five things this app needs, that tier does not provide.

A workable paid setup is a small web service, a small worker, a managed
Postgres and a managed Redis — roughly the price of a couple of coffees per
month, and you can delete it after the study. If you go this route:

1. Put uploads on object storage (Cloudflare R2 or Supabase Storage both
   have usable free tiers) rather than a local volume, so the backend and
   worker can be separate machines. This needs a change to
   `_store_document` in `app/api/routers/documents.py` and to the
   extractors, which currently take a filesystem path.
2. Set `ENVIRONMENT=production` and a real `JWT_SECRET`.
3. Run `alembic upgrade head` on deploy — the compose file does this, a
   host will need it configured.
4. Set `GEMINI_API_KEY` as a secret, never in the repository.

## What is not ready for public exposure

Honest limitations, relevant if real students will use this with real
coursework:

- **Uploads are not encrypted at rest** and there is no retention policy.
  Fine for volunteered or synthetic material; not adequate for real student
  data at scale.
- **Free-tier Gemini may use submitted content** to improve Google's models.
  Anyone uploading their own coursework should be told this.
- **No rate limiting or abuse protection** on registration or uploads. A
  public link left running is an open door.
- **No password reset.** A participant who forgets their password needs a
  new account.
- **The interface has no automated browser tests.** The usability sessions
  are its first real exercise.
