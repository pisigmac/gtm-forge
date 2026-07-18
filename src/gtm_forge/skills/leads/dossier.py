"""Company dossier: fetch the public site, detect the stack, extract buying signals,
then let the LLM turn facts into a ranked brief. No paid data providers required —
the free tier of truth is the company's own website."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TypedDict

import httpx

from gtm_forge.llm.base import Provider

_UA = {"User-Agent": "gtm-forge/0.1 (+https://github.com/pisigmac/gtm-forge)"}

#: (tech name, regex against html, regex against headers) — cheap BuiltWith-style
#: heuristics that need no API key.
_TECH_FINGERPRINTS: list[tuple[str, str | None, str | None]] = [
    ("WordPress", r"wp-content|wp-includes", None),
    ("Shopify", r"cdn\.shopify\.com|Shopify\.theme", None),
    ("Next.js", r"/_next/|__NEXT_DATA__", r"^next"),
    ("Gatsby", r"___gatsby|gatsby-", None),
    ("Webflow", r"webflow\.js|data-wf-", None),
    ("HubSpot", r"js\.hs-scripts\.com|hs-forms", None),
    ("Google Tag Manager", r"googletagmanager\.com/gtm\.js", None),
    ("Google Analytics", r"google-analytics\.com/(ga|analytics)\.js|gtag\(", None),
    ("Intercom", r"widget\.intercom\.io|intercomcdn", None),
    ("Drift", r"js\.driftt\.com", None),
    ("Stripe", r"js\.stripe\.com", None),
    ("Cloudflare", r"cdn-cgi/", r"cloudflare"),
    ("Vercel", None, r"^vercel"),
    ("Nginx", None, r"nginx"),
]

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_SOCIAL = re.compile(
    r"https?://(?:www\.)?(twitter\.com|x\.com|linkedin\.com|facebook\.com|instagram\.com|youtube\.com)/[^\s\"'<>]+"
)


@dataclass(slots=True)
class SiteFacts:
    url: str
    title: str = ""
    description: str = ""
    tech: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    socials: list[str] = field(default_factory=list)
    hiring: bool = False
    status_code: int = 0


class Signals(TypedDict):
    emails: list[str]
    socials: list[str]
    hiring: bool


def fetch_url(url: str, *, timeout_s: float = 10.0) -> tuple[str, dict[str, str], int]:
    resp = httpx.get(url, headers=_UA, timeout=timeout_s, follow_redirects=True)
    resp.raise_for_status()
    return resp.text, {k.lower(): v for k, v in resp.headers.items()}, resp.status_code


def detect_tech(html: str, headers: dict[str, str]) -> list[str]:
    """Heuristic tech-stack detection from HTML and response headers."""
    server = headers.get("server", "").lower()
    powered = headers.get("x-powered-by", "").lower()
    haystack_headers = f"{server} {powered}"
    found: list[str] = []
    for name, html_pattern, header_pattern in _TECH_FINGERPRINTS:
        html_hit = bool(html_pattern and re.search(html_pattern, html, re.IGNORECASE))
        header_hit = bool(header_pattern and re.search(header_pattern, haystack_headers))
        if html_hit or header_hit:
            found.append(name)
    return sorted(set(found))


def extract_signals(html: str) -> Signals:
    """Buying signals visible on the public site: hiring, contacts, socials."""
    emails = sorted(set(_EMAIL.findall(html)))
    socials = sorted({m.group(0) for m in _SOCIAL.finditer(html)})
    hiring = bool(re.search(r"careers|we'?re hiring|join our team|open roles", html, re.IGNORECASE))
    return {"emails": emails[:10], "socials": socials[:10], "hiring": hiring}


def _extract_meta(html: str) -> tuple[str, str]:
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    desc_m = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.IGNORECASE
    )
    title = re.sub(r"\s+", " ", title_m.group(1)).strip() if title_m else ""
    desc = desc_m.group(1).strip() if desc_m else ""
    return title, desc


def collect_facts(url: str, *, timeout_s: float = 10.0) -> SiteFacts:
    html, headers, status = fetch_url(url, timeout_s=timeout_s)
    title, desc = _extract_meta(html)
    signals = extract_signals(html)
    return SiteFacts(
        url=url,
        title=title,
        description=desc,
        tech=detect_tech(html, headers),
        emails=signals["emails"],
        socials=signals["socials"],
        hiring=signals["hiring"],
        status_code=status,
    )


_DOSSIER_SYSTEM = (
    "You are a B2B account researcher. Given raw facts about a company, write a concise "
    "account brief in markdown: ## Snapshot, ## Tech stack (and what it implies), "
    "## Buying signals (ranked, with reasoning), ## Suggested angle, ## Watch-outs. "
    "Only use the provided facts. If evidence is thin, say so."
)


def build_dossier(
    provider: Provider,
    *,
    company: str,
    facts: SiteFacts,
    model: str,
    max_tokens: int = 1500,
    temperature: float = 0.2,
) -> str:
    prompt = (
        f"Company: {company}\nURL: {facts.url}\nHTTP status: {facts.status_code}\n"
        f"Title: {facts.title}\nDescription: {facts.description}\n"
        f"Detected tech: {', '.join(facts.tech) or 'none detected'}\n"
        f"Hiring signals: {'yes' if facts.hiring else 'no'}\n"
        f"Public emails: {', '.join(facts.emails) or 'none'}\n"
        f"Social profiles: {', '.join(facts.socials) or 'none'}\n"
    )
    return provider.complete(
        system=_DOSSIER_SYSTEM,
        prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    ).text
