# Quota & Usage Audit — a cached block teardown against the Supabase meters

Symptom it answers: the dashboard shows a red meter (`Cached Egress 6.6 / 5 GB`,
`Log Ingest 2.11 / 1 GB`, `Egress 3.1 / 5 GB`) and the user asks *what does this
mean / why is it over / is my app broken*. The deliverable is a ranking of the
app's own code paths by bytes written to a meter, with a per-path estimate — not
a generic "optimise your queries" lecture.

## 0. The meters (Supabase Free plan, verify against docs before quoting)

| Meter | Free quota | Over-usage | Driven by | Can RLS/grants block the probe? |
|---|---|---|---|---|
| Egress (uncached) | 5 GB | not billed on Free | PostgREST/Auth/Storage/Realtime responses, pooler | yes — RLS/grants filter or `401` |
| Cached Egress | 5 GB | not billed on Free | Storage served from the Smart CDN (cache hits) | no for public buckets |
| Log Ingest | 1 GB | not billed until ~2027 | log lines from Postgres/gateway/Auth/Storage/Realtime | no |
| Log Query | 100 GB | — | Logs Explorer only | no |
| Realtime Messages | 2 million | — | 1 per DB change **per listening client**, +1 send/+1 per receiver for Broadcast | no |
| Realtime Peak Connections | 200 | — | concurrent sockets | no |

Limit errors surface as: `too_many_channels`, `too_many_connections`,
`too_many_joins`, `tenant_events` (project generating too many messages/sec — the
client is disconnected and `supabase-js` auto-reconnects when throughput drops).
Egress/logs overage instead reaches the billing email as a **grace period**; when
it ends the Fair Use Policy applies — pause, read-only DB, or `402` on every API
request, to *every* project in the organization.

**Cached Egress is Storage-only.** A `Cached Egress` overage with `Egress` (uncached)
under quota means the DB/REST side is fine and CDN-served assets are the problem —
check `storageService` / bucket public URLs / `cacheControl` before touching queries.

## 1. Mobile one meter before leaping to quotas: the Realtime count is DERIVED

**`Realtime Messages` is not reported by the Realtime service — it is Inferno's
cost model over the project's own log events, so it inherits every log gap.** A
rising Realtime meter with a *flat* Log Ingest meter is contradictory and means the
events were not logged, not that they were not counted. Of the ~8 log event types the
counter consumes (`realtime.subscription.*`, `realtime.broadcast.*`, presence
`*.add/remove`), the two known to sit in log ingestion are the join/leave families —
so presence traffic also inflates Log Ingest. State the model to the user when those
two meters move together, and never present the number as a server-side count.

## 2. A page that reports "no data" is not a missing lock — diff the meter you have

Before assuming the app is leaking: **query performance and Daily API Requests
dies at cycle boundaries** because the logs those dashboards aggregate are deleted
per billing cycle (the same reason a log drain gets an empty first run). An empty
chart is not "the app is quiet".

**And an over-quota project is not always restricted — a restricted project is
not always down.** Read the restriction string, not the meter. The live source is
`org.restriction_data`; the UI template is in the Supabase repo at
`apps/studio/components/interfaces/Organization/BillingSettings/Restriction.tsx` and
renders `Your organization went over its quota in the previous billing cycle
<violationLabels>. You can continue with your projects until your grace period ends
on <grace_period_end>. After that, the Fair Use Policy will apply... requests to your
projects will return a 402`.

Free-plan facts worth stating plainly when asked:
- The grace period is granted on the **first** time over. Once it ends, exceeding
the quota again restricts the project **with no new grace period**. The dashboard
keeps showing the "previously exceeded" notice while usage stays under, and it
only clears after **multiple** clean cycles.
- Restrictions lift **at the start of the next cycle** when the quota refills
  (up to a short delay), or immediately on upgrading to Pro.
- **Data is not deleted** by a restriction.
- Both counts are usually available: ask for the **project** ref *and* the
  **organization** id. Egress and Log Ingest are billed per *organization* and
  shared across all its projects, so the org-level numbers are the ones the cap is
  measured against; the project split is only a heuristic for who is loudest.

## 3. Order of interrogation (cheapest first, and it survives a key you cannot use)

1. **What actually broke first — the API or the websocket?** In a React SPA the
   Realtime socket is opened when the client is constructed, so if every DB query
   already `402`s the page still mounts and the websocket still connects (and its
   heartbeat still burns messages). A "the app renders but every action fails"
   report is the REST side; a "nothing loads" report is usually build/CDN.
2. **Read the client that was actually served**, not the repo: fetch the deployed
   HTML, extract the built asset URL (`vite.config.ts` carries `base`), grep the
   bundle for `supabase.co` refs, for any literal REST path, and for the app's own
   key names (`active_sessions`, `weekly_standings`). Constants are inlined there.
3. **Enumerate every tick and every payload-shape at the source**, with line
   numbers: `search_files` for `setInterval|setTimeout`, then for each timer read
   what it writes. Sort the result by (bytes × frequency).
4. **Probe the API** — if you hold a usable credential.

## 4. Live probes (and the RLS chicken-and-egg)

An HTTP probe is the only measurement; a meter you cannot reach is not a meter you
can reason about. But with the **anon** key on a hardened project every table
answers `401 {"code":"42501", "message":"permission denied for table X"}` — a
**missing table-level GRANT**, i.e. the question "how many rows/writes am I doing"
is unanswerable from PostgREST. Do **not** report that as "RLS blocks me":
`42501` proves the grant is absent and proves nothing about RLS. Say what you
measured and name the unmeasured part.

```bash
# row count without pulling rows (service_role; anon gets 42501 on these apps)
curl -sI "$URL/rest/v1/$TABLE?select=*" -H "apikey: $KEY" -H "Prefer: count=exact" -H "Range: 0-0"
# -> Content-Range: 0-0/1234
```

When there is no service key, the **creditless estimates below use line numbers
and payload shapes only** — say so, and hand the user the SQL/Logs-Explorer query
that settles it instead of asserting a number.

## 5. The estimate that actually lands

Work per **page/mechanism**, not per request. For a page that only renders ~30
rows, the interesting number is bytes × poll frequency.

```
cost(KB/cycle) = Σ over ticks ( (columns_i.E[bytes] × row_multiplier_i) / 1024 )
                 × (seconds in the user's active day / interval_seconds)
```

Worked numbers from one audited leaderboard (line numbers as found in that repo):
- `getWeeklyLeaderboard` run twice per load and its replay run **twice per authored
  event** while another staff page is open: `weekly_lesson_xp × 2` estimated at
  **5–15 KB per replay**, each replay issuing **4 query legs** (users, then two
  chained `Promise.all` legs per chunk of 100) → ~50 KB + ~10 requests per load.
- A hidden `getWeeklyLeaderboard(0)` that exists only to `.find(nim === me)` fetches
  the **whole student body** for a one-row answer.
- A 1 s tick that writes a row only when the day changes still accumulates.
- A 30 s heartbeat whose every write is also a **copy of the row in `activity_logs`**
  is the Log Ingest driver: `(2 writes × 2,880 ticks/day) ≈ 5.8k rows/day`.

## 6. Diagnosing which path in *their* app uses the most

Present, don't accuse:
- **Logs Explorer → Top Paths** = the raw API path names.
- **Advisors → Query Performance** = the same data shaped as "most requested
  queries", which is what "what is eating bandwidth" actually means here.
- **Storage Egress Requests** template = Storage objects by request count and
  cache-hit flag (`cf-cache-status: HIT|MISS`) — the Cached-Egress split.
- Which log settings to raise first (`log_statement = none`, `log_min_duration_statement`)
  is in the Logs Ingest docs; a chatty `RAISE NOTICE` in a frequently-called plpgsql
  function is a named, non-obvious contributor.

## 7. Fix order that moves the meters (free plan, no migration)

1. **Kill repeated full replays.** Cache the aggregate per page load / session
   (module scope + single-flight promise), or move the projection server-side.
   This is the whole first order-of-magnitude.
2. **Project only the columns a screen uses** in the select list.
3. **Serialize the queries** — the read-cheap fix for a cost model whose hot path
   is *request count*, and the thing that took one audited page from 10+ calls to 2.
4. **Pause polling on a hidden tab** (`visibilitychange`), and put realtime
   subscriptions on the same rule.
5. **Stop writing on purpose** — heartbeat/study-time ticks should check the last
   sync and write only when nothing changed (study time only advances on lesson
   screens tonight; `last_active` writes twice per minute per session).
6. **Throttle realtime fan-out**: server-side triggers `pg_notify` on every possible
   UPDATE, so a 30 s-per-user heartbeat that writes `active_sessions` fans out to
   **every staff page** watching that table. Batch or narrow the filter.
7. Verification is always the same shape: make the change → re-run the estimate →
   probe the count again, and re-check the meters on the next cycle.

## 8. Anti-patterns this audit keeps finding

- **A subscription filtered by name, not by row.** `postgres_changes` with a
  `filter` of `nim=eq.X`; a channel with **no** filter (or a filter the server
  cannot push down, e.g. a join) must still be assumed to fan out to every
  subscriber on the table.
- **`getX(0)` as "fetch all"**: `limitCount > 0 ? slice : all` param that one screen
  passes `0` to. Search for the literal `(0,` call sites.
- **A refetch handler marked `event: '*'`** — INSERT and DELETE both cost the same
  and both re-fire the full query. `event: 'UPDATE'` plus a narrow `filter` is the
  cheap half.
- **Timers with no visibility gate** — a 30 s and a 1 s interval per open tab,
  multiplied by every tab.
- **A hidden precompute** left in place after the feature it fed shipped.
- **A view/table whose only consumer is a poll** — a materialized `*_standings`
  table written on publish that nothing on the live page reads.
- **A route whose own comment already names the smell** (`// not used on the
  current leaderboard; kept for future use`).

## 9. Deliverable shape the user asked for

Lead with the conclusion line, a table of `path → cost → frequency`, then the
3–5 fixes ranked by how much they move the meter. Then ask before patching.
`references/postgrest-data-extraction.md` covers the count probe used in step 4.
