---
name: llm-provider-failover
description: "Use when wiring a new LLM provider or fallback route."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
---

# LLM Provider Failover

Configure Hermes primary + fallback model routing with pooled credentials, then verify every link live before claiming done.

## Procedure

1. **Inspect current routing first.** Run `hermes -p <profile> fallback list` and check `model.default` / `model.provider` at the top of the profile `config.yaml`. Never assume the primary from memory.
2. **Add keys to the credential pool, not just `.env`.** Use `hermes -p <profile> auth add <provider> --type api-key --api-key '<KEY>' --label '<label>'` once per key. `.env` values alone do not create pool entries.
3. **Order the pool so a known-good key is tried first.** Pool entries carry `priority` (0 = tried first). Reorder via config edit or CLI priority command; verify order by reading `auth.json` `credential_pool.<provider>` labels only.
4. **Keep fallback distinct from primary.** Setting a fallback entry identical to the primary wastes one retry round-trip on a guaranteed repeat failure. Chain shape: primary X -> fallback Y -> fallback Z, all different routes.
5. **Register optional models as aliases, not fallbacks.** `hermes -p <profile> config set model.aliases.<alias> <provider>/<model>` for models the user invokes manually (`/model <alias>`). Unreliable or quota-limited models stay out of the automatic chain.
6. **Verify each link with a live probe.** Send a minimal `chat/completions` request (`max_tokens: 5`) per provider/model/key and report only OK/FAIL + status code. Do a second probe with a browser `User-Agent` before declaring a Cloudflare-gated endpoint dead.
7. **Mirror to each profile explicitly.** Profiles are clones, not links: `default` and `hero` (or any `-p` profile) each need their own `fallback_providers` and aliases. Verify per profile with `hermes -p <profile> fallback list`.

## Wiring a provider that has no Hermes plugin

Vendors outside the shipped catalog (Meta/Muse, a reseller gateway, a local router) still work when they speak OpenAI Chat Completions. Full worked sequence: `references/custom-provider-alias.md`.

1. Read the vendor's own docs for three values — base URL, model id, auth header format — and confirm the wire protocol you will set: `chat_completions`, `codex_responses`, or `anthropic_messages`.
2. Before touching config, prove the endpoint answers: a `POST` to `<base_url>/chat/completions` with a dummy bearer returning `401 invalid_api_key` (not a 404/HTML page) means the route and path are right and only the key is missing.
3. Create the key on the vendor dashboard, then put it in `.env` under a name you will reference: `HERMES_CUSTOM_<NAME>_API_KEY`. Settings go in `config.yaml`, secrets go in `.env` — never merge the two.
4. Register it as an alias, not as the active model, so the user's current route survives: `hermes config set model.aliases.<alias>.{model,provider,base_url,api_mode,key_env}`. Nested dotted keys are supported; `hermes config get model.aliases` prints the resulting block and is the confirmation step.
5. Hand over `/model <alias>` plus a concrete `curl` the user can run, and offer to run the real round-trip yourself once the key exists. A 401 probe plus a written config is not "working" — only a 200 is.

Report in Indonesian when the user writes Indonesian, and lead with a path-vs-cost table when several access routes exist (official API / aggregator / self-host): the user picks by price and friction, not by prose.

## Pitfalls

- Probe credentials without ever printing them: check presence by key length and prefix only, send the value straight into the request headers, and report only the result. Full keys must never appear in output, logs, or screenshots.
- A single gateway key can front many upstream accounts: one `sk-...` talking to a local router (9router) may rotate across several OAuth connections internally, so one key in `.env` alongside five connections in the router dashboard is the expected shape, not a missing-key bug.
- Distinguish gateway errors from upstream errors: HTTP 429/503 naming the upstream (e.g. conduit free-premium-limit, temporary interruption) means the key and routing are correct and the upstream is throttling or down; fix by waiting, raising quota, or switching routes, never by re-adding the same key.
- Use `hermes -p <profile>` consistently for auth/fallback commands; overriding `HERMES_HOME` by hand can show an empty pool and mislead into re-adding credentials that already exist.
- After changing `model.provider`, re-check `model.base_url` and `key_env`: Hermes clears route fields that belonged to the old provider, and a stale base_url silently points the new provider at the old endpoint.
- A flat monthly plan credential is almost never a general API key. Vendors bind subscription keys to their own CLI/surface (Muse Code subscription key works only inside `muse`; extra dashboard keys bill pay-as-you-go), so never present "buy the $5 plan" as a way to get API access. Confirm in the vendor's billing/help page, not the marketing page, before quoting a price.
- One brand can be several products with separate meters on one account (consumer app quota, CLI plan quota, per-token API billing). Say which product the alias will bill against, or the user buys the wrong thing and the key still 401s at the quota layer.
- When a vendor doc site blocks the HTML extractor (403/JS shell), fetch the markdown export instead: `<docs-host>/docs/<page>.md` and the full-doc index often resolve where the rendered page does not. Grep the raw HTML for `\$` to confirm plan prices straight from the pricing page.
