# RBAC / SSO Role Debugging ("works for some accounts, not others")

Symptom class: a role-gated action (SSO redirect, page, menu, RPC) succeeds for
some accounts and silently fails for others. Do NOT theorise from source first —
run the probes below; they localise the gate in minutes.

## 0. First: which gate, on which side?

An SSO handoff has a **sender** (the app the user is in) and a **receiver** (the
target app). Determine which side rejects:

- Fetch the receiver bundle and look for a role normaliser and a rejection
  branch. If the receiver maps every role to a known value and accepts all,
  the gate is on the **sender**.
- Fetch the sender bundle and read the exact handler for the button/flow.

Bundles are minified; search them (`search_files`) for distinctive strings: the
redirect URL constant, `window.open(`, `?token=`, the RPC names
(`get_*_handshake_secure`), and role literals (`"mahasiswa"`, `"koordinator"`, …).
Reconstruct the call chain from the surrounding minified text.

## 1. The chain to trace (typical SSO)

```
click -> rpc(handshake)  -> POST /api/generate-jwt (or similar) -> window.open(RECEIVER + "?token=" + jwt)
```

A failure anywhere before `window.open` means **no redirect at all** — the user
sees "gagal membuka" / an error toast, not a receiver-side denial. That asymmetry
("can't even reach it" vs "rejected there") tells you which side to inspect.

Critical detail: many apps wrap the Supabase client in a Proxy that routes
**every** `.rpc(name, params)` through their own `/api/rpc?fn=name` proxy, which
then enforces RBAC before forwarding with the service key. So the *first* RPC of
the SSO flow is itself RBAC-gated.

## 2. Mint a per-role JWT and probe

The app's RBAC reads `role` from the JWT it issued. If you have the app's
`JWT_SECRET`, mint a short-lived HS256 token per role (stdlib only):

```python
import hmac, hashlib, base64, json, time
def b64(b): return base64.urlsafe_b64encode(b).rstrip(b"=")
def mint(secret, role, uid):
    hdr = b64(json.dumps({"alg":"HS256","typ":"JWT"}, separators=(",",":")).encode())
    pl  = b64(json.dumps({"id":uid,"role":role,"jti":"probe","iat":int(time.time()),
                          "exp":int(time.time())+600}, separators=(",",":")).encode())
    sig = b64(hmac.new(secret.encode(), hdr+b"."+pl, hashlib.sha256).digest())
    return (hdr+b"."+pl+b"."+sig).decode()
```

Then POST to the app's own proxy with each role and record the status:

```python
# POST https://SENDER/api/rpc?fn=<gated_fn>
#   Authorization: Bearer <minted token>
#   body: {"p_viewer_id": <uid>}
```

### Reading the responses

| Status | Body | Meaning |
|---|---|---|
| 200 | result | role admitted by RBAC |
| 403 | `Peran pengguna tidak valid` | **role string not in the whitelist at all** (unknown role) |
| 403 | `Peran Anda (<role>) tidak diizinkan...` | role known, but this RPC not granted to it |
| 401 | `Missing/Invalid token` | token/auth layer, not RBAC |

Distinguishing the two 403 messages is the whole game: "unknown role" means a
**vocabulary mismatch** (see below); "not allowed for this role" means a
permission-list gap.

Also probe the supporting endpoints (`/api/auth/verify`, and any
`/api/sync-*` the target page calls) — they often have *different* gates than the
one you're chasing.

### Probe hygiene: when EVERY role fails, suspect your probe

- **A failure that hits every role — including the most privileged one — is your
  test's bug, not a permission gate.** A real gate fails the low roles and admits
  the top one; if `koordinator` also gets the error, you sent a wrong parameter or
  wrong arity. Stop investigating permissions and fix the probe.
- **Look up the real signature before calling.** Read the function's `CREATE OR
  REPLACE FUNCTION` in `supabase/migrations/` for its exact parameter names and
  arity — do not guess (`p_limit` on a function that takes `p_date_filter` returns
  `Could not find the function ... in the schema cache`, which reads like a
  permission error but is a contract mismatch).
- **The proxy may overwrite identity params from the token.** Many `/api/rpc`
  proxies replace `p_viewer_id` / `p_caller_id` with the JWT's user id to block
  spoofing, so your probe body's value is ignored and the call is evaluated as the
  token's owner. That is the honest test — but do not conclude "the parameter
  changed the result" when the server never read it.

### Find *everything* that differs: enumerate the RPCs, diff the values

Don't guess which RPCs matter. Enumerate them from the served bundle, then call
each with account A's token and account B's token and compare **status AND JSON
payload** — status alone hides value-level differences that explain "the page
looks different for my account":

```python
rpc_names = sorted(set(re.findall(r'\.rpc\("([a-z0-9_]+)"', bundle_js)))
# for each name: POST /api/rpc?fn=<name> with A's token, then with B's token.
# flag rows where status differs, OR both are 200 but the payload differs
# (e.g. a stats RPC echoing user_role: 'kordas' vs 'koordinator').
```

To prove the frontend is NOT the cause, extract the menu array from the bundle
and run its own filter function locally for both roles — if the menu sets are
identical, the divergence is server-side, so stop looking at the UI.

## 3. The role-vocabulary mismatch (highest-yield bug)

Compare three sources side by side:

1. **DB ground truth:** `GET /rest/v1/users?select=role` (service key) → the
distinct values actually stored.
2. **The API whitelist:** search `api/` (`search_files`) for the role→permission
   map keyed by role string.
3. **The frontend whitelist:** search the sidebar/route code for `roles: [...]`
   arrays and route guards.

If (1) says `mahasiswa`/`admin`/`kordas` but (2)/(3) say
`praktikan`/`koordinator`, the majority of users are rejected at the first
gated call. Fix by adding a **single alias map** at the boundary, not by editing
role strings in the DB:

```ts
// Only list roles that ACTUALLY EXIST as distinct values in the users table.
const ROLE_ALIASES = { mahasiswa:'praktikan', mhs:'praktikan', peminjam:'penyewa',
                       kordas:'koordinator', korda:'koordinator', coordinator:'koordinator' };
const canonRole = r => ROLE_ALIASES[r.toLowerCase().trim()] ?? r.toLowerCase().trim();
// apply once, where role is read from the token, before the whitelist check
```

Apply the same map in the frontend (sidebar filter + route guard) so menu and
route decisions agree with the API. Keep the user's chosen canonical names —
never silently merge a distinct role (e.g. `admin` != `koordinator`) unless the
user confirms it.

- **Alias only roles that exist; a phantom alias is a privilege-escalation path.**
  Before adding `X → Y`, confirm `X` appears in `select distinct role from users`.
  A mapping for a role nobody holds is dead code at best; if a token ever carries
  it, it silently grants `Y`. A name like `superadmin` in these apps is usually a
  *username* (whose account has an ordinary role), not a role — verify, don't assume.
- **A role name can mean different things in two apps sharing one DB.** `admin`
  in an e-learning app may be an `asisten` in the siakad app. Before mapping it to
  a more senior role, cross-check the account's other attributes — an
  `assistant_code`, membership in a staff/assistant table, a grant row — and ask
  the user which canonical role each DB value should resolve to. Mapping
  `admin → koordinator` handed ordinary staff coordinator powers.
- **An unrecognised role value is probably the SIBLING app's vocabulary, not a
  typo.** When a `select distinct role` value appears in no whitelist of the repo
  you are in, grep the *other* app in the workspace for that string before calling
  it dead data: a shared DB is where two apps' role vocabularies mix, and the
  sibling app's own admin UI can write its native role into the shared `users`
  table (e.g. an e-learning app storing `kordas`, which the siakad repo never
  defines). This reframes the fix — the value is legitimate to its author app, so
  either normalise it at the boundary or align the stored value, and never "clean
  up" the string without confirming which app owns it.

## 4. Two-gate traps to check

- **Client menu gate + API gate can disagree.** A sidebar may hide a menu a user
  is allowed to call, or a route may demand a per-division menu key that the API
  never checks. Check both.
- **Simulate the FULL filter chain, not just the first `roles:[...]` check.** A
  sidebar filter is often layered: a `roles` array admits the role, then a second
  allowlist (a list of `menu_key`s that require a per-division grant, e.g.
  `CW = ["/e-learning", "/audit-log", ...]`) hides the item unless the user's
  division holds that key. Reading only layer 1 makes you report "menu is visible
  but the API denies it" — a false alarm when layer 2 hides the menu from exactly
  the roles the API also denies. Extract and run **every** predicate in the
  `.filter(...)` chain for both roles before declaring a UI/API inconsistency;
  menu-visibility that equals API-permission is not a bug. (Corollary: this is
  the third thing that hides a menu — after `roles:[]` and `requiredMenuKey` — so
  check the guard chain before concluding a division "can't be managed".)
- **Per-division access tables** (`division_access(division, menu_key)`): a route
  guarded by `requiredMenuKey` fails for roles whose division lacks that key.
  Query the grants per division and compare to the user's `division` value.
- **A per-division grant may be consulted for only ONE role.** In one pattern the
  guard tests `requiredMenuKey` only when `role === 'asisten'`; every other role
  bypasses the grant table entirely. Adding a grant row then fixes asisten of that
  division and *nothing else* — never offer it as the fix for a role that is
  failing earlier in the chain. Read the guard to see which roles it actually tests.
- **A grant-management UI may hide divisions.** A dropdown built from
  `users.filter(u => u.role === 'asisten' && u.division)` omits any division with
  no asisten (e.g. one staffed only by admins). Read the `divisi` / grant table
  directly; don't conclude a division "can't be managed" from the UI alone.
- **Case-duplicated values** (`K3`/`k3`) break the division↔grant equality join.
  Normalise with `lower(trim(...))` on both sides, or clean the data.
- **`auth_role()`-style helpers drift into DEAD branches; a policy on a dead
  branch is silently permissive or silently closed.** A helper that returns
  `kordas`/`praktikan` while the stored column holds `koordinator`/`mahasiswa`
  never matches the rows that exist: any policy written as `auth_role() =
  'koordinator'` admits nobody, and any policy written as `auth_role() =
  'kordas'` admits everybody the helper maps there. Compare the helper's RETURN
  vocabulary against `select distinct role from users` (and against the literals
  the app's JWT carries) — three vocabularies, not two. A helper that returns
  `'admin'` when `request.jwt.claims` is empty also treats *every* credential-less
  connection (psql, a pooler, a migration runner) as the top role; flag the
  fallback, don't just check the role map.
- **A function can be broken in a way that only the CALL SITE reveals.** plpgsql
  parses lazily, so `CREATE OR REPLACE FUNCTION` succeeds even when the body has
  `INSERT INTO t (nim, ..., nim, ...)` — `42701 column "nim" specified more than
  once` fires only when the function is actually invoked. Read the body in
  `pg_get_functiondef`, and check its column lists against the table's real
  columns; prefer fixing the body to match the table's canonical/alias column
  pairs (both sides written) rather than the one column the error names — a helper
  that writes only half of each mirrored pair (`nama` without `full_name`,
  `divisi` without `division`) produces blank rows in whichever app reads the
  other half.
- **A view's owner is a privilege grant.** `pg_get_userbyid(relowner)` returning
  `postgres` for a view over a locked table IS the leak: the view executes with the
  owner's rights, so base-table RLS never applies. Check the owner before you go
  looking for a policy — there may be none, and none is needed for the leak to be
  live.
- **DB helper functions** (`is_admin`, `is_staff`) may list the *wrong* strings
  (e.g. a division name where a role belongs, or omit a real role). Read the
  live definition, not just migrations, and confirm with a call per account.
- **Sweep EVERY function, not just the helper you happened to find.** One alias
  role (`kordas`) can be omitted by a dozen unrelated functions that each compare
  `role = 'koordinator'` inline. Enumerate the LATEST definition of every
  `CREATE OR REPLACE FUNCTION` across `supabase/migrations/` and list those whose
  body contains a role literal but never the alias — that set is the real fix
  list, and it is usually 10–15 functions, not one:

  ```python
  # keep the LAST definition per function name (later migrations win)
  latest = {}
  for f in sorted(os.listdir(mig_dir)):
      t = open(os.path.join(mig_dir, f), encoding='utf-8', errors='replace').read()
      for m in re.finditer(r"CREATE OR REPLACE FUNCTION\s+(?:public\.)?(\w+)\s*\([\s\S]*?\n\$[^$]*\$\s*;", t):
          latest[m.group(1)] = (f, m.group(0))
  # functions that gate on a role literal but never mention the alias role
  for fn, (f, seg) in sorted(latest.items()):
      if re.search(r"role\s*(?:=|IN)\s*'", seg, re.I) and 'kordas' not in seg.lower():
          print(fn, f)
  ```

  Migrations are the best static proxy for the live definitions; when a function
  looks decisive, also confirm the live body by calling it (or reading its
  behaviour) rather than trusting the file alone.
- **The API whitelist and the DB helpers are two separate gates.** Passing RBAC
  only gets the request as far as Postgres; a helper that omits the role then
  raises, and the proxy surfaces it as **400** with the helper's own message — not
  403. After fixing the whitelist, re-probe per role: `admin`/`kordas` moving from
  403 to 400 is *progress*, not failure; the remaining fix is `CREATE OR REPLACE`
  on the helper. Fix both layers or the symptom persists.

## 4b. The role you wrote is not the role that got stored — check the triggers

A `BEFORE INSERT OR UPDATE OF role` trigger can rewrite the role on its way in, so
`select distinct role` is the only truth about what is stored. Two consequences
that decide the fix:

- **A trigger that NORMALISES a role into a more privileged one is an escalation
  path, not a cleanup.** A map like `CASE lower(trim(NEW.role)) WHEN 'admin' THEN
  'koordinator' ... END` means any writer that sends the app-native role `admin`
  stores `koordinator` — and the sibling app's `is_admin()` check then passes for
  an ordinary staff account. It stays dormant only while every writer happens to
  use a shadow column instead; one writer that targets `role` reactivates it.
- **Distinguish a dormant trigger from a harmless one by the row counts, not the
  code.** Group both columns: `select role, elearning_role, count(*) from users
  group by 1,2`. A result like `asisten`+`admin` (n×) with **zero** rows whose
  `role` is `admin` proves the app-native value is being kept in the shadow column
  and the canonical column is clean — i.e. the intended two-app shape, with the
  trigger as a live trap for the next writer. That query is also the cheapest way
  to prove a role fixes landed at all.

```sql
-- live triggers on the shared table, with the function each one calls
SELECT t.tgname, p.proname, t.tgenabled, pg_get_triggerdef(t.oid)
FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
JOIN pg_proc p ON p.oid = t.tgfoid
WHERE c.relname = 'users' AND NOT t.tgisinternal;
```

Read every function named there before concluding the column's contents are what
any single writer intended — then `pg_get_functiondef(p.oid)` for the body.

## 5. Fix pattern

Normalise at every boundary, from one shared map:

1. **API proxy:** alias the role before the RBAC whitelist check.
2. **Frontend:** same alias map in sidebar filter and route guard.
3. **DB — put the map in one SQL function and call it everywhere.** Do NOT
   hand-edit each swept function's literal; the alias set then lives in one place
   and is case/whitespace tolerant:

   ```sql
   CREATE OR REPLACE FUNCTION public.canon_role(p_role TEXT)
   RETURNS TEXT LANGUAGE sql IMMUTABLE AS $$
     SELECT CASE lower(trim(coalesce(p_role,'')))
       WHEN 'kordas' THEN 'koordinator' WHEN 'korda' THEN 'koordinator'
       WHEN 'mahasiswa' THEN 'praktikan' WHEN 'admin' THEN 'asisten'
       ELSE lower(trim(coalesce(p_role,''))) END; $$;
   ```

   Then `CREATE OR REPLACE` each swept function with `public.canon_role(role) =
   'koordinator'` in place of `role = 'koordinator'`.
4. **Singleton alias ⇒ offer the data fix first.** If exactly one account carries
   the odd role and no code depends on that spelling, one line makes every legacy
   function correct at once:
   `UPDATE public.users SET role = '<canonical>' WHERE id = <id>;`
   Reserve the multi-function rewrite for when the alias role is genuinely
   widespread. Present both and let the user choose.
5. **Result rows need normalising too.** Normalising the *token* role fixes the
   gates, but role strings the DB *returns* — `user_role` in a stats RPC, a `role`
   column in a user-list RPC — still surface raw and get rendered as a badge
   ("KORDAS"). Either fix the stored value (step 4) or normalise on display.
6. Leave stored data alone unless the user asks; the alias map is the low-risk fix.

## 6. Prove the whole chain, per role, end to end

A first-gate 200 does not prove the user reaches the receiver. After a fix, run
the **entire** handoff for one account of each role and record the status at every
hop, then decode the final token to see the role the receiver actually resolved:

```
handshake RPC -> POST /api/generate-jwt {"handshake_code": <code>}
             -> POST RECEIVER/api/receive-token {"token": <jwt>}
             -> base64-decode the returned token's payload -> final appRole
```

Report a table of `role -> handshake / genjwt / receive / final appRole`. Two
traps: the JWT-generation endpoint reads a *specific* body key
(`handshake_code`, not `code`/`token`) — read its handler for the exact name; and
the handshake RPC may return a bare string (the code) rather than an object, so
trim quotes before reusing it. Mapping of role→final-appRole is done by the
receiver's own `normalizeRole`, which can differ per app (e.g. sender
`koordinator` arrives as receiver `kordas`) — read the receiver's map, don't assume
it passes the role through unchanged.
