"""Sweep a Supabase-backed app for role-vocabulary gates.

Three independent probes, all read-only:

  1. rpc-matrix   Enumerate every `.rpc("name")` in a served JS bundle, call each
                  through the app's own /api/rpc proxy with two different
                  per-role tokens, and report where STATUS or PAYLOAD differs.
                  Status-only comparison misses value-level divergence (a stats
                  RPC echoing user_role) that explains "looks different for my
                  account".
  2. db-sweep     Enumerate the LATEST definition of every CREATE OR REPLACE
                  FUNCTION in supabase/migrations/ and list those that compare a
                  role literal but never mention the alias role -> the real fix
                  list (usually 10-15 functions, not one).
  3. live-helpers Call is_admin/is_staff/canon-style helpers per account to
                  confirm the live definition, not just the migration file.

Usage:
  python sweep_role_gates.py --bundle live.js --rpc-base https://app.example.com \
      --jwt-secret-env .env --roles kordas:14 koordinator:1
  python sweep_role_gates.py --migrations path/to/supabase/migrations --alias kordas

Probes 1 and 3 are OPT-IN because they touch a live host: pass --bundle/--rpc-base
and --supabase-url respectively. Probe 2 is offline. Never point a mutating RPC at
production: this script only calls RPCs listed as read-only via --readonly-only
(default on) and skips anything matching upsert_/create_/delete_/save_/update_.
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

MUTATING = re.compile(r"(upsert_|_create_|create_|delete_|_delete|save_|update_|_update|approve_|insert_)", re.I)


def b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=")


def mint(secret, role, uid, ttl=900):
    """Mint a short-lived HS256 JWT carrying the role, for the app's own RBAC path."""
    hdr = b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    pl = b64(json.dumps(
        {"id": uid, "username": "probe%d" % uid, "role": role, "jti": "probe",
         "iat": int(time.time()), "exp": int(time.time()) + ttl},
        separators=(",", ":")).encode())
    sig = b64(hmac.new(secret.encode(), hdr + b"." + pl, hashlib.sha256).digest())
    return (hdr + b"." + pl + b"." + sig).decode()


def post(url, body, token, timeout=25):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as f:
            return f.status, f.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:  # network / timeout -> report, never crash the sweep
        return "ERR", str(e)[:120]


def probe_rpc_matrix(bundle, rpc_base, secret, roles, readonly_only=True):
    js = open(bundle, encoding="utf-8", errors="replace").read()
    names = sorted(set(re.findall(r'\.rpc\("([a-z0-9_]+)"', js)))
    if readonly_only:
        names = [n for n in names if not MUTATING.search(n)]
    print("RPCs to probe: %d (read-only filter=%s)" % (len(names), readonly_only))

    # a few common param shapes; the proxy usually injects/overwrites p_viewer_id
    shapes = [lambda uid: {"p_viewer_id": uid},
              lambda uid: {"p_viewer_id": uid, "p_limit": 5, "p_offset": 0}]

    def call(fn, role, uid):
        last = None
        for shape in shapes:
            st, body = post("%s/api/rpc?fn=%s" % (rpc_base.rstrip("/"), fn), shape(uid), mint(secret, role, uid))
            last = (st, body)
            # a param-shape error is not a gate result; try the next shape
            if st not in (400, 422) or "p_viewer_id" not in body:
                break
        return last

    (r1, u1), (r2, u2) = roles[0], roles[1]
    diffs = []
    for fn in names:
        s1, b1 = call(fn, r1, u1)
        s2, b2 = call(fn, r2, u2)
        if s1 != s2:
            diffs.append((fn, "STATUS", s1, s2, b1[:90]))
        elif s1 == 200:
            try:
                if json.loads(b1) != json.loads(b2):
                    diffs.append((fn, "PAYLOAD", s1, s2, "payload differs for %s vs %s" % (r1, r2)))
            except Exception:
                pass
    print("\n%-40s %-8s %-8s %-8s %s" % ("RPC", "kind", r1, r2, "note"))
    for fn, kind, s1, s2, note in diffs:
        print("%-40s %-8s %-8s %-8s %s" % (fn, kind, s1, s2, note.replace("\n", " ")))
    print("\ntotal divergences: %d" % len(diffs))
    return diffs


def probe_db_sweep(mig_dir, alias):
    latest = {}
    for f in sorted(os.listdir(mig_dir)):
        if not f.endswith(".sql"):
            continue
        t = open(os.path.join(mig_dir, f), encoding="utf-8", errors="replace").read()
        for m in re.finditer(
                r"CREATE OR REPLACE FUNCTION\s+(?:public\.)?(\w+)\s*\([\s\S]*?\n\$[^$]*\$\s*;", t):
            latest[m.group(1)] = (f, m.group(0))

    print("functions found (latest definition each): %d" % len(latest))
    print("\n### gate on a role literal but never mention %r ###\n" % alias)
    hits = []
    for fn, (f, seg) in sorted(latest.items()):
        body = seg.split("AS $$", 1)[-1] if "AS $$" in seg else seg
        if re.search(r"role\s*(?:=|IN)\s*'", body, re.I) and alias not in body.lower():
            lines = [" ".join(l.strip().split())[:110]
                     for l in body.split("\n") if re.search(r"role\s*(?:=|IN)\s*'", l, re.I)]
            hits.append((fn, f, lines[:3]))
            print("%-38s (%s)" % (fn, f))
            for l in lines[:3]:
                print("      %s" % l)
    print("\ntotal alias-blind functions: %d" % len(hits))
    return hits


def probe_live_helpers(url, svc, helpers, accounts):
    hdr = {"apikey": svc, "Authorization": "Bearer " + svc,
           "Accept": "application/json", "Content-Type": "application/json"}
    print("\n### live helper outcomes ###")
    for fn in helpers:
        row = []
        for uid, role in accounts:
            req = urllib.request.Request(
                url.rstrip("/") + "/rest/v1/rpc/" + fn,
                data=json.dumps({"p_user_id": uid, "p_viewer_id": uid}).encode(),
                headers=hdr, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=20, context=CTX) as f:
                    row.append("%s=%s" % (role, f.read().decode()[:12]))
            except urllib.error.HTTPError as e:
                row.append("%s=HTTP%d" % (role, e.code))
            except Exception:
                row.append("%s=ERR" % role)
        print("  %-18s %s" % (fn, "  ".join(row)))


def read_env_var(path, key):
    if not path or not os.path.exists(path):
        return None
    m = re.search(r'^\s*%s\s*=\s*"?([^"\r\n]+)"?' % re.escape(key),
                  open(path, encoding="utf-8", errors="replace").read(), re.M)
    return m.group(1).strip() if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", help="served/minified JS file to enumerate RPCs from")
    ap.add_argument("--rpc-base", help="app origin, e.g. https://app.example.com")
    ap.add_argument("--jwt-secret-env", help="env file containing JWT_SECRET")
    ap.add_argument("--roles", nargs=2, metavar=("ROLE:ID", "ROLE:ID"),
                    help="two role:uid pairs to compare")
    ap.add_argument("--migrations", help="path to supabase/migrations")
    ap.add_argument("--alias", default="kordas", help="alias role to sweep for (default: kordas)")
    ap.add_argument("--supabase-url", help="https://<ref>.supabase.co for live helper probe")
    ap.add_argument("--service-env", help="env file containing SUPABASE_SERVICE_ROLE_KEY")
    ap.add_argument("--helpers", nargs="*", default=["is_admin", "is_staff"])
    ap.add_argument("--allow-writes", action="store_true",
                    help="include mutating RPCs (do NOT use against production)")
    a = ap.parse_args()

    if a.migrations:
        probe_db_sweep(a.migrations, a.alias)

    if a.bundle and a.rpc_base and a.roles:
        secret = read_env_var(a.jwt_secret_env, "JWT_SECRET")
        if not secret:
            print("!! JWT_SECRET not found; skipping rpc-matrix", file=sys.stderr)
        else:
            roles = []
            for spec in a.roles:
                role, _, uid = spec.partition(":")
                roles.append((role, int(uid)))
            probe_rpc_matrix(a.bundle, a.rpc_base, secret, roles,
                             readonly_only=not a.allow_writes)

    if a.supabase_url:
        svc = read_env_var(a.service_env, "SUPABASE_SERVICE_ROLE_KEY")
        if not svc:
            print("!! service key not found; skipping live helper probe", file=sys.stderr)
        else:
            accounts = []
            for spec in (a.roles or []):
                role, _, uid = spec.partition(":")
                accounts.append((int(uid), role))
            probe_live_helpers(a.supabase_url, svc, a.helpers, accounts)


if __name__ == "__main__":
    main()
