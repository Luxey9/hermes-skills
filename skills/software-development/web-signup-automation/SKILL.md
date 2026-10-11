---
name: web-signup-automation
version: 1.0.0
author: ratman4080
license: MIT
description: Use when mass-creating accounts on a website for tokens.
metadata:
  hermes:
    tags: [automation, signup, bookmarklet, anti-bot]
    related_skills: [web-app-runtime-verification, blocked-page-recovery]
---

# Web Signup Automation

## When to Use

- User asks to mass-create accounts on a web service for free tokens, trial credits, or signup-flow testing.
- User mentions "hack web", "banyak akun", "free token", farming trial registrations.

Class: creating multiple accounts on a web service (free tokens, trial credits, testing signup flow). User's goal is usually bulk accounts for API credits on AI provider sites.

## Procedure

1. **Recon the auth stack first** — never blind-register:
   - `curl -s <site>/sign-up` (also try `/login`, `/signin`, `/signup`, `/register`) and save the HTML.
   - Grep the HTML for: `supabase|firebase|clerk|workos|auth0|turnstile|hcaptcha|recaptcha`, `<form action=...>`, and JS chunk paths (`/_next/static/chunks/*.js`).
   - Download the JS chunks and grep for `sitekey`, `/auth/...` endpoints, `signup` schema names. The signup POST endpoint and captcha provider are always findable here.
2. **Pick the automation route based on protection found:**
   - No captcha, simple form POST → pure curl/requests script.
   - Cloudflare Turnstile / WorkOS Radar / device fingerprinting → do NOT fight it headless; use the semi-manual bookmarklet route (step 3). Radar scores device signals, so a real browser with human clicks passes; scripted requests usually fail.
   - OAuth-only signup (Google/GitHub buttons, `<form action="/auth/start/google" method="post">`) → just POST those forms per identity.
3. **Semi-manual bookmarklet route** (the proven pattern for anti-bot-protected sites):
   - Generate emails + passwords offline first. Use the generator at `C:/Users/MyBook Hype AMD/Documents/File Faqod/Program/email-gen/email_gen.py` (modes: `random N`, `gmail base N` dot-trick, `custom domain N`). Random human-looking names beat dot-trick on sites with fingerprint scoring.
   - Build a bookmarklet JS (one file, `javascript:(function(){...})()`) embedding the accounts array. Key mechanics:
     - Fill inputs via the native value setter + dispatch `input`/`change` events (React/Next.js ignores plain `.value =` assignment).
     - Track progress with a counter in `localStorage` (e.g. `localStorage.getItem('autofill_idx')`) so repeated clicks walk the list in order and survive page navigations.
     - After filling, find and click the submit button by regex on its text; alert the account index so the user knows which one was used.
   - Build the bookmarklet as a plain string constant + `json.dumps(entries)` for the data — do NOT construct it with an f-string. A single unescaped `{`/`}` in an f-string wrapping JS raises `SyntaxError: f-string: single '}' is not allowed`; the string-concatenation builder avoids the whole class.
   - Validate the bookmarklet JS with a tiny node script that strips the `javascript:` prefix and calls `new Function(body)` — `node -e "..."` with nested quotes is fragile, write `scripts/verify_bookmarklet.js`-style file instead.
   - Write credentials to `<site>_accounts.txt` as `email:password` lines — that file is what the user plugs into other providers later.
   - User flow to give them: add bookmark (paste file as URL) → open signup page → click bookmarklet per account → verify email if the site demands it.
4. **If email verification is required**, prefer disposable-inbox APIs (e.g. mail.tm) or catch-all domain over random big-provider emails — random @gmail/@outlook emails are useless if the user cannot open the inbox. BUT see the disposable-domain pitfall first: temp-mail domains are often blocklisted, so they only work on sites that don't screen domains.
   - mail.tm flow: POST `https://api.mail.tm/accounts` `{address,password}` → POST `/token` for a bearer token → GET `/messages` (header `Authorization: Bearer <token>`) → GET `/messages/{id}` returns `text`/`html` body; regex the body for `https?://...` links and `\b\d{4,8}\b` codes.
   - mail.tm rate-limits account creation with 429 — sleep ~1.2s between creates and back off (15s/30s/45s) on 429; a 20-account batch otherwise dies halfway (6/20 succeeded on the first na\u00efve run).
   - `/domains` returns a bare JSON list, not a hydra wrapper; handle both shapes.
   - Reserve the mailbox password separately from the target-site password — store target credentials as `email:site_password` in the accounts file, keep mail.tm password/token in a JSON sidecar.
5. **Confirm the reward actually lands before farming** — a marketing "free tier" is not a credit grant:
   - Open the account dashboard / billing / rewards page after one real signup and read the balance and the credit-program panel. If balance is 0, find how credits are actually granted (referral, social bundle, plan) and whether the state is `granted` / `not_eligible` / `review_required`.
   - Fire one authenticated API call with the new key before scaling: providers return a billing error (HTTP 402 `insufficient_credits`, 401) instead of credits when the account has none. Do not build a 20-account batch on the assumption that signup grants credits.
   - If signup grants nothing and only a paid plan does, say so plainly and offer real alternatives (existing account, another provider, self-host) rather than farming accounts that all end up at 0.
6. **If the browser backend is dead** (browser_exec timing out twice on the same page), do not keep retrying — the kit is still deliverable: generate accounts + validated bookmarklet + verification reader, then hand the user the manual click flow. Say the automated run is blocked rather than faking success.

## Pitfalls

- Disposable domains get blocklisted. mail.tm's `maxxspace.com` is scored 97/100 by check-mail/emailverifier and is refused outright by WorkOS Radar ("This sign-in attempt was blocked"). Before building a mail.tm batch for a protected site, check the domain against a disposable-domain list or just ask the user to try one signup with their real address — a successful real-address signup proves the block is domain-based. Preferred fallback: the user's own Gmail with plus/dot aliases (gmail.com is clean).
- Gmail plus-alias (`user+tag@gmail.com`) all lands in one inbox; set a Gmail filter on `from:<site>` or `to:` the alias so verification mails are findable across 20 signups. Only offer Gmail API OAuth for auto-reading verification links when the user wants full automation.
- Grep JS chunks for `sitekey`/`turnstile`/`radar` BEFORE promising a fully-automated bot — promising curl automation on a Turnstile+Radar site wastes a session; fall back to the bookmarklet early.
- Browser automation tools can hang on heavy challenge pages (Cloudflare interstitials, Radar collectors). If a browser call times out twice on the same page, switch strategy (bookmarklet or curl) instead of retrying the same route.
- Gmail plus/dot aliases are collapsed by Gmail but many sites normalize them too before the duplicate check, so a handful may be rejected as "already used" — mix plus-aliases with dot-variants if the site rejects some.
- Before committing a disposable-inbox provider, check the domain against a live disposable-domain list (e.g. `check-mail.org/domain/<domain>`, `emailverifier.dev/domains/<domain>`): a domain scoring high risk is very likely already refused by the site's anti-fraud. mail.tm rotates its active domain, so re-check rather than trusting a domain from a previous session.
- When the signup form is backed by Clerk.io, expect two hard gates even if the site's own policy sounds permissive: disposable addresses are refused at the form (`Disposable email addresses are not permitted`) and breached or common passwords are refused via a haveibeenpwned-style check. Generate a fresh high-entropy password per account and stick to permanent-domain aliases (Gmail plus/dot) on Clerk-backed sites — a reused or human-chosen password burns the attempt.

## Notes

- Recon intel for known providers (endpoints, auth stack, how credits are granted) goes in `references/provider-auth-notes.md` — check it before re-reconning a known site.
- When the user's actual goal is API access rather than accounts, switch skills: `free-llm-api-sourcing` covers probing providers and verifying a free tier is real (this skill only gets the account created).
- Reusable modules sit next to the generator in `C:/Users/MyBook Hype AMD/Documents/File Faqod/Program/email-gen/`: `abl_from_mailtm.py` exports `build_js(entries)` and `gen_password()` (import these, do not rewrite the bookmarklet builder), `abl_from_gmail.py` wraps it for Gmail plus-aliases, and `mailtm_gen.py` / `mailtm_check.py` create and read disposable inboxes.
