# PostgREST Data Extraction (read-only reports)

Use when the request is "ambil datanya" / "pull me the rows" against a Supabase
project, not "fix the RLS". Read via the service-role key straight over HTTP with
`curl` or a short Python script — no SDK, no Node, no browser login.

## 1. Load the service key without printing it

```bash
cd <repo>
export $(grep -E '^SUPABASE_URL=|^SUPABASE_SERVICE_ROLE_KEY=' .env | xargs)
K="apikey: $SUPABASE_SERVICE_ROLE_KEY"
A="Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"
```

Prefer a real script over long `curl` one-liners once more than one table is
involved — quoting breaks first, and a joined report needs Python anyway.

## 2. Discover the schema before guessing table names

```bash
curl -s "$SUPABASE_URL/rest/v1/" -H "$K" -H "$A" \
  | tr ',' '\n' | grep -o '"/[a-z_]*"' | sort -u
```

That prints every exposed table/view path. Then sample one row per interesting
table (`?select=*&limit=1`) to learn the real column names — column names in
PostgREST are the DB's, and a guessed column in a filter returns a `42703
column ... does not exist` error rather than empty rows.

## 3. Filters, counts, ordering

| Need | Parameter |
|---|---|
| Case-insensitive name match | `?full_name=ilike.*yudha*` |
| OR across columns | `?or=(nim.eq.X,username.eq.X)` |
| Exact row count | header `Prefer: count=exact` + `Range: 0-0`, read `Content-Range: 0-322/323` |
| Sorted | `?order=full_name` / `order=nim.desc` |
| One row | `?limit=1` |

Always fetch the exact count header before telling the user "tidak ada" — it
turns a vague empty result into "0 of 323 accounts match", which is what makes
the negative answer credible.

## 4. Joined report pattern (groups, rosters, contacts)

Pull each table whole into Python and join on ids — PostgREST's embedded selects
(`?select=*,users(...)`) depend on FK names being configured and fail or silently
drop rows when they are not.

```python
import json, urllib.request

def get(path, key, url):
    req = urllib.request.Request(url + "/rest/v1/" + path, headers={
        "apikey": key, "Authorization": "Bearer " + key,
        "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

users  = get("users?select=id,full_name,nim,role,class_code,phone_number&limit=2000", KEY, URL)
scheds = get("schedules?select=*&limit=2000", KEY, URL)
gmem   = get("group_members?select=schedule_id,student_id,assistant_id&limit=5000", KEY, URL)
gast   = get("group_assistants?select=schedule_id,assistant_id&limit=5000", KEY, URL)
```

Then group by `schedule_id` → assistant bucket, map ids through a `{id: row}`
dict, and emit a markdown table per schedule with the assistant's phone number
next to the member list. Write the result to a `.md` file outside the repo and
hand the user a `MEDIA:` path — a 9-table dump is unreadable in chat.

## 5. Searching for one student by name

1. Try the literal string, then progressively looser: `*surname*`, then the
   distinctive fragment only (`yudh`, `widaya`, `noer`).
2. Try the NIM both as `nim.eq` and `username.eq` — many imports store the NIM
   in both, some only in `username`.
3. If the NIM misses, print the prefix distribution before concluding:

```bash
curl -s "$SUPABASE_URL/rest/v1/users?select=nim&nim=not.is.null&limit=2000" -H "$K" -H "$A" \
  | grep -o '"2[0-9]\{8\}"' | cut -c2-6 | sort | uniq -c
```

That shows which cohorts exist (e.g. 272 rows `20261`, 23 rows `20267`) and
whether the requested NIM is even inside a real range — stronger evidence than
an empty result.
4. When nothing matches, say what you checked (row count, which columns, which
   fuzzy variants) and ask for the exact full name or the SIAKAD export. Do not
   offer the nearest-sounding student as if it were the answer.

## Pitfalls

- **Never `cat` an env file.** Print key NAMES only. A real env file can hold a
  multi-line JSON value (service-account blobs) that spills an entire private key
  into the transcript when you dump values.
- **A sibling app's `.env` key belongs to that app's project.** Loading
  `ELEARNING_SUPABASE_SERVICE_ROLE_KEY` and pointing it at a different project
  ref returns `Invalid API key` — the key is honest, the URL is wrong (or the key
  is stale). Probe `/rest/v1/users?limit=1` first; if it errors, stop and ask
  which project, do not try more URLs.
- **Empty table ≠ nothing to report.** `practical_groups` was empty while the
  real grouping lived in `group_members` + `group_assistants` keyed by
  `schedule_id`. Sample the related tables before declaring a feature unused.
- **Rows can be duplicated assistants.** The same person may exist twice (one
  row with a proper NIM, one with a lowercase username as NIM). Dedupe on
  `(full_name.lower(), nim)` when building contact lists.
- **Missing contact fields are normal.** `phone_number` may be NULL for active
  assistants; render `— belum diisi` instead of dropping the person from the table.
