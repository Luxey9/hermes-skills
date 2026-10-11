# Credential Claims and Target Verification

"Invalid API key" (401) is never a code bug — the credential does not belong to
the project the URL names. Do not ask the user to paste the key to find out which
of the causes it is; decode it.

## The four causes, in the order they actually happen

1. **Key from a sibling project.** One repo is often deployed twice (legacy +
   current domain, admin + student app), each against its own project. The key is
   valid — just not here.
2. **Public key used where a privileged one is required.** `anon` /
   `sb_publishable_...` is stopped by RLS on every table of a locked-down project;
   the error text may even hint the wrong key type.
3. **Pasted wrong** — truncated, embedded newline, or a leading `Bearer ` kept
   from a header example.
4. **Project URL wrong** while the key is right (the mirror of cause 1).

## Decode the JWT payload (no secret leaves the machine)

Structural facts only: role, project ref, expiry, plus the key's length and first
three characters. That is enough to name the fault while never printing the key.

```js
// Apps Script (Utilities); Node: Buffer.from(b64, 'base64')
var seg = key.indexOf('eyJ') === 0 ? key.split('.')[1] : null;
if (seg) {
  var b64 = seg.replace(/-/g, '+').replace(/_/g, '/');
  while (b64.length % 4) b64 += '=';
  var claims = JSON.parse(Utilities.newBlob(Utilities.base64Decode(b64)).getDataAsString());
  // claims.role → service_role | anon | authenticated
  // claims.ref  → project ref: compare with the host in SUPABASE_URL
  // claims.exp  → expiry
}
```

Report the comparison explicitly (`ref di URL: <a> ✓ cocok` / `✗ BEDA PROJECT`),
because that single line ends the debugging round.

Newer key formats have no claims to read: detect by prefix instead
(`sb_secret_` = service role, `sb_publishable_` = public). Sending the key in both
`apikey` and `Authorization: Bearer` headers covers both styles in one code path.

## Probe credentials read-only

The publishable/anon key embedded in a live client bundle is public by design and
is the right tool for shape checks. Distinguish the failure codes:

| Response | Meaning |
|---|---|
| `404` / `PGRST205` | table not in the API's schema cache |
| `PGRST202` + "Perhaps you meant ..." | RPC signature mismatch — the error lists the *current* argument list, which is a free schema diff |
| `42703` | column does not exist — PostgREST resolved the table first |
| `42501` | column/table exists, the role lacks the grant (RLS or missing GRANT) |
| `P0001` + app message | the function ran and rejected you on application rules — the function exists with the arguments you sent |

`PGRST202` and `P0001` are the cheap way to verify that a migration was actually
applied: call the RPC with the new parameter and a payload the function will
refuse anyway (nonexistent caller id). A signature error means not deployed; an
application-level rejection means deployed. Never confirm a migration with a
write.

## Same class, several deployments

Local `.env` describes local builds only. To learn what a domain actually serves,
fetch its HTML, take the `/assets/*.js` bundle it references, and grep the bundle
for `https://[a-z0-9]+\.supabase\.co`. Two domains returning different hosts =
two databases, and only one holds the rows the user is looking at.
