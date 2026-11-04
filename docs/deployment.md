# Putting StudyMate online (Vercel + Supabase)

This gets StudyMate onto a public link like `https://studymate-xyz.vercel.app`
that anyone can open on their phone or laptop. Nothing runs on your PC:

| Piece | Where it runs | Cost |
|---|---|---|
| Web app (React) | Vercel | Free (Hobby plan) |
| API (FastAPI, `/api/*`) | Vercel Python function | Free |
| Database | Supabase Postgres | Free |
| Sign-in, sign-up, password reset | Supabase Auth | Free |
| Uploaded lecture files | Supabase Storage | Free (1GB) |
| Every-minute scheduler (reminders) | Supabase `pg_cron` | Free |
| Reminder emails | Your Gmail account | Free (≈500/day) |
| AI | Google AI Studio (Gemini), with Mistral as backup | Free tiers |

Allow about an hour the first time. Do the steps in order. Wherever it says
**copy**, paste the value into a private note; you will need it later.
Never share the values marked **secret**.

---

## 1. Create the Supabase project

1. Go to [supabase.com](https://supabase.com) → **Start your project** → sign in with GitHub.
2. **New project**. Name: `studymate`. Set a strong **database password** and
   **copy** it (secret). Region: the closest to Ghana that is offered (e.g.
   *West EU (London)* or *Central EU (Frankfurt)*). Create.
3. When it is ready, open **Project Settings → API Keys** (or **Data API**) and copy:
   - **Project URL**, e.g. `https://abcd1234.supabase.co`
   - **anon / publishable** key (safe to expose; it ends up in the browser)
   - **service_role / secret** key (**secret**: it bypasses all security)
4. **Project Settings → JWT Keys**: if you see a **Legacy JWT secret**, copy it
   (secret). If the page shows only signing keys, skip this; the app reads
   those automatically.
5. Click **Connect** (top of the dashboard) and copy two connection strings,
   replacing `[YOUR-PASSWORD]` with the database password from step 2:
   - **Transaction pooler** (port **6543**): this is what Vercel uses.
   - **Session pooler** (port **5432**): this is what you use from your PC in step 3.

## 2. Create the storage bucket

Supabase → **SQL Editor → New query**. Open `supabase/setup.sql` from this
repository, copy **only part 1** (the `insert into storage.buckets ...`
statement), paste it and press **Run**. You should see *Success*.

(Part 2 needs your Vercel address, so it waits until step 8.)

## 3. Create the database tables

This runs the migrations from your PC once. It is light; it does not run the app.

In the `StudyMate` folder, open `.env` (copy `.env.example` to `.env` if you
have not got one) and set:

```
DATABASE_URL=<the Session pooler string from step 1.5, port 5432>
```

Then in a terminal:

```bash
cd backend
.venv\Scripts\activate            # Windows
pip install -r requirements-dev.txt
alembic upgrade head
```

The last line should end with `Running upgrade 0010 -> 0011`. In Supabase →
**Table Editor** you should now see tables such as `users`, `courses` and
`lecture_slots`.

> Migration `0011` also switches on row-level security for every table.
> Supabase publishes your tables through a public API that the anon key can
> reach. With RLS on and no policies, that API returns nothing, while the
> StudyMate API (which connects as the table owner) works normally. Do not
> switch it off.

## 4. Generate the remaining secrets

Still in `backend` with the virtual environment active:

```bash
python -m app.scripts.vapid
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

The first prints `VAPID_PUBLIC_KEY` and `VAPID_PRIVATE_KEY` (for push
notifications). The second is your `CRON_SECRET`. Copy all three. Generate the
VAPID pair **once**: changing it later means every student has to turn
notifications on again.

## 5. Set up email (Gmail)

1. On the Google account that will send reminders, turn on
   **2-Step Verification** (myaccount.google.com → Security).
2. Visit [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords),
   create an app password called `StudyMate`, and copy the 16 characters (secret).

Use the same Gmail for Supabase's own emails (confirmation and password
reset). Supabase's built-in sender only delivers to your own team's
addresses, so without this nobody else can confirm their account:

Supabase → **Authentication → Emails → SMTP Settings** → enable custom SMTP:

| Field | Value |
|---|---|
| Sender email | your Gmail address |
| Sender name | StudyMate |
| Host | `smtp.gmail.com` |
| Port | `587` |
| Username | your Gmail address |
| Password | the app password |

> **Running usability sessions?** You can skip email confirmation entirely:
> Supabase → **Authentication → Sign In / Providers → Email** → turn off
> **Confirm email**. Participants are then signed in straight after
> registering.

## 5b. Get a Mistral key (the AI backup)

When Gemini is overloaded or out of quota, StudyMate switches to Mistral.
Its free plan is large enough for whole lecture documents.

1. Go to [console.mistral.ai](https://console.mistral.ai) and sign up.
2. Verify your phone number when asked. The free plan requires it; no card is needed.
3. Choose the free **Experiment** plan if you are asked to pick one.
4. **Admin Console → Privacy**: turn **off** "Anonymous improvement data",
   so students' material is not used to train Mistral's models.
5. **API Keys → Create new key**. Name it `StudyMate` and copy it straight
   away (secret). Mistral shows it only once.
6. Paste it into the `.env` in the `StudyMate` folder, after
   `MISTRAL_API_KEY=` (no quotes, no spaces), and save. Check it works:

   ```bash
   cd backend
   .venv\Scripts\python -m app.scripts.check_ai
   ```

   You want an `OK` line for both `gemini` and `mistral`. The script never prints the key.

## 6. Put the code on GitHub

Vercel deploys from GitHub. From the `StudyMate` folder:

```bash
git push -u origin feature/vercel-supabase-games
```

then merge it into `main` on GitHub (or ask Claude to do this part).

## 7. Deploy on Vercel

1. [vercel.com](https://vercel.com) → sign up with GitHub (Hobby plan).
2. **Add New → Project** → import your StudyMate repository.
3. Leave **Root Directory** as the repository root. `vercel.json` already
   sets the build, the output folder and the API function.
4. Open **Environment Variables** and add every line below (Production,
   Preview and Development):

| Name | Value |
|---|---|
| `ENVIRONMENT` | `production` |
| `APP_URL` | leave for now, set in step 8 |
| `DATABASE_URL` | Transaction pooler string (port **6543**) |
| `SUPABASE_URL` | Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | service_role key |
| `SUPABASE_JWT_SECRET` | legacy JWT secret, if you had one |
| `STORAGE_BUCKET` | `lecture-files` |
| `CRON_SECRET` | from step 4 |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` | from step 4 |
| `VAPID_SUBJECT` | `mailto:` + your email |
| `SMTP_HOST` / `SMTP_PORT` | `smtp.gmail.com` / `587` |
| `SMTP_USERNAME` | your Gmail address |
| `SMTP_PASSWORD` | the app password |
| `EMAIL_FROM` | `StudyMate <you@gmail.com>` |
| `AI_PROVIDERS` | `gemini,mistral` |
| `GEMINI_API_KEY` | your Google AI Studio key |
| `GEMINI_MODELS` | `gemini-3.5-flash-lite,gemini-3.1-flash-lite` |
| `MISTRAL_API_KEY` | your Mistral key from step 5b |
| `MISTRAL_MODELS` | `mistral-small-latest,mistral-medium-latest` |
| `VITE_SUPABASE_URL` | Project URL (again) |
| `VITE_SUPABASE_ANON_KEY` | anon / publishable key |
| `VITE_SUPABASE_STORAGE_BUCKET` | `lecture-files` |

5. **Deploy**. When it finishes, copy your address, e.g. `https://studymate-xyz.vercel.app`.

## 8. Connect the pieces to your address

1. **Vercel → Settings → Environment Variables**: set `APP_URL` to your
   address, then **Deployments → ⋯ → Redeploy**.
2. **Supabase → Authentication → URL Configuration**:
   - **Site URL**: your address
   - **Redirect URLs**: add `https://studymate-xyz.vercel.app/**`
3. **Supabase → SQL Editor**: open `supabase/setup.sql` again, replace
   `YOUR-APP.vercel.app` and `YOUR-CRON-SECRET` in **part 2**, and run it.
   After two minutes, run the check query at the bottom of the file. You
   should see `200` in `status_code`.

## 9. Check it works

Open your address on your phone and go through this list:

- [ ] Create an account. Confirm the email if you left confirmation on.
- [ ] Fill in the welcome form. Add a course. Upload a PDF. Within about two
      minutes it should say **Ready**.
- [ ] **Study Engine**: generate a Multiple choice set and take it.
- [ ] **Arcade**: play Beat the Clock and Concept Match.
- [ ] **Timetable**: upload a screenshot of your timetable, check the rows, save.
- [ ] **Timetable → Reminders**: turn on notifications, then **Send a test**.
      On an iPhone, first tap **Share → Add to Home Screen** and open
      StudyMate from the home screen.
- [ ] Add a lecture starting in about 65 minutes and wait for the
      "starts in 1 hour" reminder.

---

## When something goes wrong

**Where are the logs?** Vercel → your project → **Logs**. Every job writes
lines such as `Job … (process_document) done in 85.3s`, plus a warning when
an AI model falls back or fails.

| Symptom | Likely cause |
|---|---|
| Login page says "not connected to Supabase" | `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` missing; add them and **redeploy** (they are baked in at build time). |
| Every page says "Could not load…" after login | `SUPABASE_URL` or `DATABASE_URL` wrong on Vercel; check the Logs. |
| Confirmation emails never arrive | Custom SMTP not set in Supabase (step 5), or turn off **Confirm email**. |
| Uploads stuck on **Queued** for more than a minute | The scheduler is not running: re-check step 8.3 and its `status_code`. A `401` means `CRON_SECRET` does not match. |
| A file **Failed** with "usage limit" | Both Gemini's and Mistral's free limits were hit at once. Wait a minute and press **Try again**. In a usability session, record this as an infrastructure event, not a usability defect. |
| Logs say `AI provider 'mistral' is listed but has no API key` | `MISTRAL_API_KEY` is missing on Vercel; add it and redeploy. Until then only Gemini is used. |
| No push on iPhone | Push only works from the home-screen app on iOS 16.4+. Email reminders still arrive. |

**Free-tier limits worth knowing.** Vercel stops any single request after 5
minutes. A typical lecture takes 1 to 3 minutes to read, and the course
overview is written in a separate step so no run carries both. Supabase
pauses a free project after a week with no activity. Opening the dashboard
wakes it. Gemini's free quota is the real ceiling with several testers at
once. Mistral takes over when it runs out; Mistral's own free plan allows
about one request per second, which is enough for a handful of testers at a
time.

## Updating the live app

After code changes are committed, one command updates the database and
redeploys. From the `StudyMate` folder:

```bash
backend\.venv\Scripts\python scripts\release.py
```

It applies any new database migrations to Supabase first, then uploads the
committed code to Vercel, waits for the build, and checks the site answers.
It needs `DATABASE_URL` (session pooler) and `VERCEL_TOKEN` in `.env`, and
deploys only what is committed. If the database step fails, nothing is
deployed. It also copies `SENTRY_DSN`, `VITE_SENTRY_DSN` and
`VITE_TURNSTILE_SITE_KEY` from `.env` to Vercel when they are set.

## Sign-in settings, Google sign-in and CAPTCHA

`scripts/configure_auth.py` applies the sign-in settings to Supabase:
passwords of at least 8 characters, and the app's address as an allowed
return address. It needs `SUPABASE_ACCESS_TOKEN` in `.env`.

```bash
backend\.venv\Scripts\python scripts\configure_auth.py
```

**Google sign-in** (free):

1. In [Google Cloud Console](https://console.cloud.google.com), create a
   project, then **APIs & Services → OAuth consent screen**: External, app
   name StudyMate, your email as support and developer contact. Publish it.
2. **Credentials → Create credentials → OAuth client ID → Web application**.
   - Authorised JavaScript origins: `https://studymate-alpha-fawn.vercel.app`
   - Authorised redirect URIs: `https://<project-ref>.supabase.co/auth/v1/callback`
3. Put the client ID and secret in `.env` as `GOOGLE_CLIENT_ID` and
   `GOOGLE_CLIENT_SECRET`, then run `configure_auth.py`. The "Continue with
   Google" button appears by itself once Google is on in Supabase.

**CAPTCHA** (Cloudflare Turnstile, free): create a widget at
dash.cloudflare.com → Turnstile for the app's domain. Put the site key in
`.env` as `VITE_TURNSTILE_SITE_KEY` and the secret as `TURNSTILE_SECRET_KEY`,
run `configure_auth.py`, then release. Do the two together: with CAPTCHA on
in Supabase but no site key in the page, nobody can sign in.

## Error reports (Sentry)

Create a free project at sentry.io (platform: React for the page, FastAPI for
the API; one project can take both). Put its DSN in `.env` as both
`SENTRY_DSN` and `VITE_SENTRY_DSN`, then release. Reports carry no email
addresses or uploaded content.

## Backups

Supabase's free plan keeps no backups you can restore yourself. Save one to
this computer every week or so, and before any big change:

```bash
backend\.venv\Scripts\python scripts\backup.py           # the database
backend\.venv\Scripts\python scripts\backup.py --files   # and the lecture files
```

Backups go to `backups/` (never committed: it holds everyone's data).
`scripts/restore.py` loads one into a new, empty database; its first lines
say how.

## Keeping the project awake

Supabase pauses a free project after about a week with no activity. The
**Keep alive** workflow in `.github/workflows` asks the API to touch the
database every morning. It runs on GitHub by itself once the repository is
pushed; check it under the repository's **Actions** tab. The **Tests**
workflow there runs every test on each push.

## Running locally (optional)

Only needed to develop, not to use the app. It needs about 2GB of free memory.

```bash
# Terminal 1, from the StudyMate folder: the API, through the same entry point Vercel uses
backend\.venv\Scripts\python -m uvicorn api.index:app --reload --port 8000

# Terminal 2: the web app on http://localhost:5173
cd frontend
npm install
npm run dev
```

Both read the `.env` in the `StudyMate` folder. Without `SUPABASE_URL` and
`SUPABASE_SERVICE_ROLE_KEY`, uploads are stored in `backend/storage` instead
of Supabase. Sign-in always needs a Supabase project.
