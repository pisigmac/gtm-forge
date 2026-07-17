---
name: gtm-seo-ops
description: Generate SEO attack briefs for a target keyword and detect keyword cannibalization across a site's pages. Use when planning content to win a keyword or auditing overlapping pages.
---

# SEO Ops

## When to use
Planning a piece to win a specific keyword, or checking whether existing pages compete with each other.

## Commands
```bash
gtm seo brief --keyword "KEYWORD" --audience "WHO" [--serp-notes notes.md] [--out brief.md]
gtm seo cannibalize --csv pages.csv [--threshold 0.6]   # CSV columns: url,title,keywords (semicolon-separated)
```

## Rules
- Cannibalization conflicts above the threshold mean: consolidate, differentiate, or 301.
- Briefs are only as good as the SERP notes — paste real observations when you have them.
