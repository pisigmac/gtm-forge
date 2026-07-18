"""Lead dossier heuristics and the verification cascade."""

from gtm_forge.skills.leads.dossier import detect_tech, extract_signals
from gtm_forge.skills.leads.enrich import (
    VerifyResult,
    build_cascade,
    verify_cascade,
    verify_syntax,
)

HTML = """
<html><head>
<title>Acme Corp - We make widgets</title>
<meta name="description" content="Widget platform for teams">
<script src="https://www.googletagmanager.com/gtm.js?id=GTM-1"></script>
<script src="https://widget.intercom.io/widget/abc"></script>
</head><body>
<link href="/wp-content/themes/acme/style.css">
<a href="https://linkedin.com/company/acme">LinkedIn</a>
<p>Contact us at hello@acme.example — we're hiring!</p>
</body></html>
"""


def test_detect_tech():
    tech = detect_tech(HTML, {"server": "nginx"})
    assert "WordPress" in tech
    assert "Google Tag Manager" in tech
    assert "Intercom" in tech
    assert "Nginx" in tech
    assert "Shopify" not in tech


def test_extract_signals():
    signals = extract_signals(HTML)
    assert signals["hiring"] is True
    assert "hello@acme.example" in signals["emails"]
    assert any("linkedin.com" in s for s in signals["socials"])


def test_verify_syntax_invalid():
    assert verify_syntax("not-an-email").status == "invalid"


def test_verify_syntax_disposable():
    assert verify_syntax("foo@mailinator.com").status == "disposable"


def test_verify_syntax_ok_unknown():
    result = verify_syntax("real.person@acme.example")
    assert result.status == "unknown"  # syntax fine, deliverability unverified
    assert not result.conclusive


class _Stub:
    def __init__(self, name, status):
        self.name = name
        self._status = status

    def verify(self, email):
        return VerifyResult(email, self.name, self._status, "stub")


def test_cascade_stops_at_first_conclusive():
    chain = [_Stub("a", "unknown"), _Stub("b", "valid"), _Stub("c", "valid")]
    final, trail = verify_cascade("x@y.example", [], cascade=chain)
    assert final.status == "valid"
    assert final.provider == "b"
    assert len(trail) == 2  # c never ran


def test_cascade_all_unknown():
    chain = [_Stub("a", "unknown"), _Stub("b", "unknown")]
    final, trail = verify_cascade("x@y.example", [], cascade=chain)
    assert final.status == "unknown"
    assert len(trail) == 2


def test_build_cascade_regex_only():
    chain = build_cascade(["regex"])
    assert chain[0].name == "regex"
