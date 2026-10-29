# Wiring a third-party data API into a cloned scope

Cloning a panel that shows vendor data (PVGIS irradiance, weather, tariff,
pricing) means calling a public API from the browser. Two separate failure
modes look identical from the UI, so diagnose them apart.

## 1. Browser-only failure: CORS

Symptom: the UI shows `Failed to fetch` in a headless browser, while
`curl <same-url>` from the terminal returns 200 with a full body.

Cause: the endpoint serves no `Access-Control-Allow-Origin`. Node/curl never
enforce CORS; a browser does. Nothing about your code is wrong.

Fix: proxy it. For Vite (dev + preview, separate keys):

```ts
const proxy = {
  '/pvgis': {
    target: 'https://re.jrc.ec.europa.eu',
    changeOrigin: true,
    secure: true,
    rewrite: (p: string) => p.replace(/^\/pvgis/, ''),   // strip prefix only
  },
};
export default defineConfig({ plugins: [react()], server: { proxy }, preview: { proxy } });
```

Pitfalls that cost real cycles:

- **`rewrite` must not add a path segment.** If the client already builds
  `<base>/api/v5_2/<fn>`, a rewrite that injects `/api` produces
  `/api/api/v5_2/...` and the upstream answers 404 `"Not found. Please, revise
  the function call."` — a 404 from the API, not from the proxy.
- **Test the proxy with curl before touching the app:**
  `curl -s -o /dev/null -w '%{http_code}' http://localhost:<p>/pvgis/api/v5_2/PVcalc?...`
  A 200 there means the proxy is right and any remaining failure is client-side.
- `preview.proxy` is separate from `server.proxy`; setting only `server` leaves
  the production preview broken and the verification step lies.

## 2. Node/test failure: relative URL

A base of `/pvgis` works in the browser and breaks under `fetch()` in Node —
`Failed to parse URL from /pvgis/...`, which kills any test that does a real
network call.

Fix: resolve the base at call time, not module load:

```ts
function resolveBase(): string {
  const override = import.meta.env?.VITE_PVGIS_BASE;
  if (override) return override;
  return typeof window === 'undefined' ? 'https://re.jrc.ec.europa.eu' : '/pvgis';
}
```

So the browser takes the proxy, tests take the absolute host, and a deployed
static build can point `VITE_PVGIS_BASE` at its own proxy. Keep the constant
exported — existing tests assert the absolute URL of the API.

## Verification shape

1. curl through the proxy -> 200.
2. headless puppeteer: click the panel's fetch button, poll for the rendered
   result (N bars / total row) up to ~20 s, and read the error box if it never
   appears. A real network call plus a real render is the only proof.
3. Scale and sanity-check the number: API returns per-kW values, so multiply by
   the local capacity (`totalWp / 1000`). A plausible magnitude
   (~1100 kWh/kWp/yr for tropical sites, 14% losses) proves the mapping, not
   just that something rendered.
