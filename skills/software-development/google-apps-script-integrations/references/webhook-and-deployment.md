# Webhook vs Trigger, and Deployment Versions

Both paths run the same sync function; the difference is latency, cadence, and how
much of the daily runtime quota you spend.

## Choosing

| | Time trigger | Webhook |
|---|---|---|
| Latency to the sheet | up to the interval | seconds (plus your throttle) |
| Runs per day | fixed by the interval | only when data changes |
| Quota cost | ~runs × duration (measure it) | usually lower |
| Failure mode | none, it retries itself | a dropped call is never retried |

Use **both**: the webhook as the fast path, a slow trigger (30 minutes is plenty)
as the safety net that also catches manual edits and data changes made outside the
app. Size the interval against the quota in the skill body — a 10-minute trigger
running a 10-second sync spends ~24 of the 90 trigger-minutes per day.

## Web app deployment

1. *Deploy → New deployment → Web app*.
2. **Execute as: Me** (needs the script's own access to files/properties).
3. **Who has access: Anyone** — an external service cannot present a Google
   login, so this is mandatory for a webhook. The shared secret is therefore the
   only authentication: refuse when the secret property is unset, and compare with
   `!==` on the query parameter.
4. Copy the `/exec` URL. It stays stable across versions.
5. Register the caller (e.g. a database webhook / trigger) against
   `.../exec?secret=<SECRET>`. If the platform has to enable an extension for
   outbound HTTP first (Supabase: `pg_net`, Dashboard → Database → Extensions),
   do that before debugging the endpoint.

## Hardening a public endpoint

- Check the secret **first**, before any work; return a small JSON body
  (`{ok:false,error:'unauthorized'}`) rather than throwing — the caller logs it.
- `LockService.getScriptLock().tryLock(5000)` and return `{ok:false,error:'busy'}`
  when the lock is held, so overlapping bursts cannot interleave writes.
- Throttle with a last-run timestamp property (15-30 s) because one user action
  produces many row events; answer `{ok:true,skipped:'throttled'}` so the caller
  sees success and stops retrying.
- A leaked URL can only trigger work, not read data — but it can burn the quota.
  Rotating the secret is the fix; mention this to the user when handing it over.

## Changes that require action

| Change | What is needed |
|---|---|
| Edit `Code.gs` | Deploy → Manage deployments → Edit → **New version** → Deploy (menu/triggers pick up the save automatically; a web app does **not**) |
| Script Properties (secret, credentials) | nothing — read at run time |
| Trigger interval | re-run the install function; delete the old trigger first so they don't stack |
| New OAuth scope | re-authorise (the next run prompts) |

The web app always runs the **deployed** version as the deploying account, so
"it works when I press Run but not over HTTP" is a version/permission question,
not a code question.
