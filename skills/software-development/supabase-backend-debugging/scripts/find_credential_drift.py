#!/usr/bin/env python3
"""Find rows whose auth flag disagrees with their credential columns.

Run this instead of hand-typing the probes when a user reports "cannot log in"
and the row exists, AND before claiming the data is clean after any credential-gate
change. It answers two questions at once:

  1. which rows are LOCKED OUT (flag says registered, no credential to verify)
  2. which rows are INVERSE-DRIFTED (flag says unregistered while a credential
     EXISTS) - an account-takeover path, because the status endpoint invites a
     "create password" that overwrites the hash the account logs in with

The normal roster state (no flag, no credential) is reported as a count only, so
the real anomalies stand out against a scope.

Fix the GATE (derive it from the credential columns, one shared helper used by
status/login/claim) before or together with the rows: a data fix alone leaves the
ORM read-modify-write free to recreate the drift on the next admin save.

Usage:
    python find_credential_drift.py --url https://<ref>.supabase.co --key <service_role>

Never hardcode or print a key: pass it via --key or the env var SUPABASE_SERVICE_KEY.
Adjust TABLE / FLAG / CREDENTIALS below to the schema you are probing.
"""
import argparse
import json
import os
import urllib.error
import urllib.request

TABLE = "users"
ID_COLS = "id,nim,nama"
FLAG = "is_registered"
# every column that can make a login possible; adding one here is the fix for a
# gate that refuses a row which clearly has a usable credential
CREDENTIALS = ["password_hash", "fb_password_hash", "fb_password_salt", "supabase_user_id"]
IDENTITY = "nim"


def get(base, key, table, query):
    req = urllib.request.Request(
        f"{base}/rest/v1/{table}?{query}",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    try:
        return json.loads(urllib.request.urlopen(req, timeout=60).read())
    except urllib.error.HTTPError as e:
        return {"HTTPError": e.code, "body": e.read().decode()[:300]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="https://<ref>.supabase.co")
    ap.add_argument("--key", default=os.environ.get("SUPABASE_SERVICE_KEY"))
    ap.add_argument("--table", default=TABLE)
    ap.add_argument("--flag", default=FLAG)
    ap.add_argument("--credentials", default=",".join(CREDENTIALS))
    ap.add_argument("--identity", default=IDENTITY)
    args = ap.parse_args()
    if not args.key:
        raise SystemExit("no key: pass --key or set SUPABASE_SERVICE_KEY (never commit it)")

    creds = [c.strip() for c in args.credentials.split(",") if c.strip()]
    select = ",".join([ID_COLS, args.flag, *creds])

    # A row is LOCKED when the flag is true but every credential column is NULL:
    # the status endpoint says "already registered", the claim branch answers
    # "conflict", and login has nothing to verify.
    null_all = "&".join(f"{c}=is.null" for c in creds)
    locked = get(args.url, args.key, args.table,
                 f"select={select}&{args.flag}=is.true&{null_all}&order=id.desc&limit=50")

    # The mirror image: a credential EXISTS but the flag is false. Login may work
    # while the UI reports "not registered" - also a drift, opposite direction.
    any_cred = "or=(" + ",".join(f"{c}.not.is.null" for c in creds) + ")"
    unclaimed = get(args.url, args.key, args.table,
                    f"select={select}&{args.flag}=is.false&{any_cred}&order=id.desc&limit=50")

    # Baseline so the anomalies are read against a scope, not in isolation.
    total = get(args.url, args.key, args.table, f"select={ID_COLS}&limit=1")

    print(f"table={args.table} flag={args.flag} credentials={creds}")
    if isinstance(total, dict):
        print("probe failed:", json.dumps(total)[:300])
        print("check the key belongs to THIS url (decode the JWT payload 'ref' claim).")
        return

    print(f"\n== LOCKED OUT: {args.flag}=true and ALL credentials NULL "
          f"({len(locked) if isinstance(locked, list) else '?'} shown) ==")
    for r in locked if isinstance(locked, list) else []:
        print("  ", r)
    if not locked:
        print("   none - no row is locked out by drift")

    print(f"\n== INVERSE DRIFT: {args.flag}=false but a credential EXISTS "
          f"({len(unclaimed) if isinstance(unclaimed, list) else '?'} shown) ==")
    for r in unclaimed if isinstance(unclaimed, list) else []:
        print("  ", r)
    if not unclaimed:
        print("   none")

    print("\nFix the gate first (derive it from the credential columns, one shared")
    print("helper used by status/login/claim), THEN normalise the old rows - a data")
    print("fix alone leaves the ORM read-modify-write free to recreate the drift.")


if __name__ == "__main__":
    main()
