"""
fallback_identity_resolver — Strictly Isolated Fallback System
==============================================================

Triggers ONLY when: website == null AND phone == null
Does NOT import, modify, or interact with any existing pipeline module.

Entry point: resolve_missing_identity(business_name, city, country)
"""
from fallback_identity_resolver.resolver import resolve_missing_identity

__all__ = ["resolve_missing_identity"]
