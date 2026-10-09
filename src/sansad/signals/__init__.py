"""Maintainer alerting and last-known-good handling.

Kept separate from visitor-facing behaviour because FR-010 and FR-011 pull in
opposite directions: quiet degradation for visitors, loud signals for the
maintainer.
"""
