-- StudyMate: one-time Supabase setup.
-- Run in the Supabase dashboard: SQL Editor -> New query -> paste -> Run.
-- Safe to run again; every statement is idempotent.

-- 1. A private bucket for lecture files.
--    Private: files are only reachable through the API's service-role key or
--    a short-lived signed upload URL it hands out. 20MB matches the app limit.
insert into storage.buckets (id, name, public, file_size_limit)
values ('lecture-files', 'lecture-files', false, 20971520)
on conflict (id) do update
  set public = false,
      file_size_limit = 20971520;


-- 2. The scheduler: calls the app every minute to send lecture reminders and
--    finish any uploads whose processing was interrupted.
--
--    BEFORE RUNNING THIS PART, replace the two placeholders:
--      YOUR-APP.vercel.app  -> your Vercel address, e.g. studymate-abc.vercel.app
--      YOUR-CRON-SECRET     -> the CRON_SECRET you set in Vercel
--
--    Vercel's free plan only allows a scheduled job once a day, which is too
--    coarse for "an hour before your lecture", so Supabase does the timing.

create extension if not exists pg_cron;
create extension if not exists pg_net;

-- Remove an older copy first, so re-running this updates rather than duplicates.
select cron.unschedule(jobid) from cron.job where jobname = 'studymate-tick';

select cron.schedule(
  'studymate-tick',
  '* * * * *',
  $$
  select net.http_post(
    url := 'https://YOUR-APP.vercel.app/api/cron/tick',
    headers := jsonb_build_object(
      'Authorization', 'Bearer YOUR-CRON-SECRET',
      'Content-Type', 'application/json'
    ),
    body := '{}'::jsonb,
    timeout_milliseconds := 60000
  );
  $$
);

-- To check it is running (after a couple of minutes):
--   select status_code, timed_out, error_msg, created from net._http_response order by created desc limit 5;
-- status_code 200 means the app answered. 401 means the secret does not match.
