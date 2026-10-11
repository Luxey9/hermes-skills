# column_grant_sweep.py — per-column PostgREST privilege matrix for one role.
#
# WHY: `42501 permission denied for table X` with hint `GRANT SELECT/UPDATE ON
# public.X` can mean a SINGLE COLUMN lacks its grant, and PostgREST rejects the
# whole statement rather than just that column. Postgres privileges are
# per-column, and the OpenAPI spec does NOT expose them, so the only measurement
# is one request per column. A ranged or multi-column probe lies: a ranged filter
# (`?id=gte.0`) answers 403 for every column and reads as "no grant at all".
#
# USAGE (stdlib only, no deps):
#   python column_grant_sweep.py --env .env --table users
#   python column_grant_sweep.py --env .env --tables users,student_progress \
#          --token "$JWT" --role authenticated
#
#   --env     key=value file with VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY,
#             SUPABASE_SERVICE_ROLE_KEY (service role reads the OpenAPI spec).
#   --token   JWT to test as. Default: the anon key (tests the `anon` role).
#             Pass a token minted by the app's own /api/... route to test
#             `authenticated` — a locally-signed token may fail PGRST301
#             ("None of the keys was able to decode the JWT") and prove nothing.
#   --role    label used in the suggested GRANT statements (default: authenticated)
#
# READ-ONLY for SELECT. Each UPDATE probe writes ONE typed neutral value to rows
# matching a placeholder filter built to match nothing real; there is no
# --execute, and the suggested GRANT statements are printed, never run.
#
# PostgREST accepts the project's anon key as the `apikey` header for ANY caller
# JWT — send `apikey: <anon>` + `Authorization: Bearer <token>`. Sending the
# service_role key as BOTH makes every call run as service_role and the sweep
# reports that (fully privileged) role instead of the one under test.
import argparse, json, os, re, sys, urllib.error, urllib.request, uuid


def read_env(path):
    env = {}
    if not path or not os.path.exists(path):
        return env
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'^\s*(?:export\s+)?([A-Z0-9_]+)\s*=\s*(.*)$', line.rstrip('\n'))
        if m:
            env.setdefault(m.group(1), m.group(2).strip().strip('"').strip("'"))
    return env


def request(url, method='GET', token=None, anon=None, body=None, prefer='return=minimal'):
    req = urllib.request.Request(
        url, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'apikey': anon or '', 'Authorization': 'Bearer ' + (token or ''),
                 'Content-Type': 'application/json', 'Prefer': prefer})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read(400).decode('utf-8', 'replace')).get('code')
        except Exception:
            return e.code


def neutral(prop):
    """Typed placeholder. An untyped sentinel on an integer column returns 22P02
    BEFORE privileges are checked, which a sweep then misreads as 'denied'."""
    t, f = prop.get('type'), prop.get('format')
    if f == 'uuid':
        return str(uuid.uuid4())
    if t == 'boolean':
        return False
    if t in ('integer', 'number') or f in ('int2', 'int4', 'int8', 'numeric', 'float4', 'float8'):
        return 0
    if t == 'array':
        return []
    if t == 'object' or f in ('json', 'jsonb'):
        return {}
    return '__hermes_probe__'


def filter_for(props):
    """A filter typed from the column's own format, matching no real row."""
    for col in ('id', 'nim', 'lesson_id'):
        if col in props:
            if props[col].get('format') == 'uuid':
                return '%s=eq.%s' % (col, uuid.uuid4())
            if props[col].get('type') in ('integer', 'number'):
                return '%s=eq.-999999' % col
            return '%s=eq.__hermes_probe__' % col
    return 'id=eq.__hermes_probe__'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--env', default='.env')
    ap.add_argument('--table', action='append', default=[])
    ap.add_argument('--tables', default='')
    ap.add_argument('--token', default='')
    ap.add_argument('--role', default='authenticated')
    a = ap.parse_args()

    env = read_env(a.env)
    env.update({k: os.environ[k] for k in (
        'VITE_SUPABASE_URL', 'VITE_SUPABASE_ANON_KEY', 'SUPABASE_SERVICE_ROLE_KEY')
        if k in os.environ})
    url = (env.get('VITE_SUPABASE_URL') or env.get('SUPABASE_URL') or '').rstrip('/')
    anon = env.get('VITE_SUPABASE_ANON_KEY') or env.get('SUPABASE_ANON_KEY') or ''
    svc = env.get('SUPABASE_SERVICE_ROLE_KEY') or ''
    if not url or not svc:
        sys.exit('need VITE_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (env vars or --env file)')
    token = a.token or anon
    print('project : %s' % url)
    print('tested  : %s' % ('caller-supplied JWT' if a.token else 'anon key'))

    spec = json.load(urllib.request.urlopen(urllib.request.Request(
        url + '/rest/v1/',
        headers={'apikey': svc, 'Authorization': 'Bearer ' + svc,
                 'Accept': 'application/openapi+json'})))['definitions']
    tables = a.table + [t for t in a.tables.split(',') if t] or sorted(spec)

    for t in tables:
        props = (spec.get(t) or {}).get('properties')
        if not props:
            print('\n== %s -- not present in the spec' % t)
            continue
        flt, cols = filter_for(props), list(props)
        sel_ok, upd_ok = [], []
        for c in cols:
            if request('%s/rest/v1/%s?select=%s&limit=1' % (url, t, c),
                       token=token, anon=anon) == 200:
                sel_ok.append(c)
            if request('%s/rest/v1/%s?%s' % (url, t, flt), method='PATCH',
                       token=token, anon=anon, body={c: neutral(props[c])}) == 204:
                upd_ok.append(c)
        print('\n== %s  (filter: %s)' % (t, flt))
        print('   SELECT %2d/%-2d   UPDATE %2d/%-2d' % (
            len(sel_ok), len(cols), len(upd_ok), len(cols)))
        for op, granted in (('SELECT', sel_ok), ('UPDATE', upd_ok)):
            denied = [c for c in cols if c not in granted]
            if denied:
                print('   %s DENIED %d/%d: %s' % (op, len(denied), len(cols), ', '.join(denied)))
                print('   -> GRANT %s (%s) ON public.%s TO %s;' % (op, ', '.join(denied), t, a.role))
        print('   DELETE probe: %s  | INSERT probe: %s   (22P02/23502 = malformed probe, proves nothing)' % (
            request('%s/rest/v1/%s?%s' % (url, t, flt), method='DELETE', token=token, anon=anon),
            request('%s/rest/v1/%s' % (url, t), method='POST', token=token, anon=anon, body={})))


if __name__ == '__main__':
    main()
