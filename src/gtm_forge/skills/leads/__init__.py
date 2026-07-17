"""Lead intelligence: dossiers and cascade email verification."""

from gtm_forge.skills.leads.dossier import detect_tech, extract_signals
from gtm_forge.skills.leads.enrich import VerifyResult, verify_cascade, verify_syntax

__all__ = ["VerifyResult", "detect_tech", "extract_signals", "verify_cascade", "verify_syntax"]
