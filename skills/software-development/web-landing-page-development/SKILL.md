---
name: web-landing-page-development
description: Use when editing single-file HTML sites.
version: 1.0.0
author: hermes-curator
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [html, landing-page, single-file, whatsapp, inline-js, intersection-observer]
    related_skills: [single-file-landing-pages]
---

# Web Landing Page Development

## When to Use

Use when editing, extending, or troubleshooting single-file HTML landing pages (inline CSS/JS), especially when managing interactive forms, WhatsApp messaging builders, and scroll-triggered UI animations.

## Procedure & Rules

1. **Verify Inline JS Syntax Immediately:**
   - Single-file landing pages execute all scripts in global scope without modular isolation.
   - Any syntax error (such as an unescaped literal newline inside a string literal) halts script execution immediately at parse time.
   - Always run a syntax check (`node -c` on extracted script tags) after modifying inline JavaScript.

2. **WhatsApp Multi-line Messaging & URL Encoding:**
   - Prefer `https://api.whatsapp.com/send?phone=...&text=...` over `wa.me` for reliable cross-platform handling of UTF-8 and emoji in mobile and desktop clients.
   - When constructing multi-line WhatsApp message templates in JavaScript, join array items using `\r\n` or `String.fromCharCode(10)` rather than unescaped literal line breaks in file string replacements.

3. **Prevent Cascading UI Failures:**
   - Interactive components (e.g. chip selectors, booking estimators, floating WhatsApp bars) and scroll animations (`IntersectionObserver` reveal targets) often share a single inline script.
   - If an interactive element becomes unresponsive or animations fail, check for script parser crashes before modifying CSS or DOM selectors.

4. **Rebranding Checklist for Single-Page Sites:**
   - Update meta tags (`<meta name="description">`, `<title>`).
   - Update navbar, footer branding, and hero lead text.
   - Update dynamic message templates in JavaScript (e.g. `lines = [...]` for WhatsApp consultation or booking).
   - Re-check with case-insensitive search across the file to ensure no residual brand mentions remain.
