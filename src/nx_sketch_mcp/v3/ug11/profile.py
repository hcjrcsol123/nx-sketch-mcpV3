"""Observed T06 runtime identity; no broad NX11 compatibility is implied."""
from dataclasses import dataclass


class UnsupportedRuntime(ValueError):
    """Runtime evidence is absent or differs from the T06 native run."""


@dataclass(frozen=True)
class RuntimeIdentity:
    release: str
    assembly_version: str
    file_version: str
    product_version: str
    journal_language: str
    ui_language_environment: str


OBSERVED = RuntimeIdentity("NX V11.0", "11.0.0.33", "11.0.0.33", "11.0.0.33", "C#", "simpl_chinese")


def require_profile(identity):
    """Validate a supplied native observation; host Python is never an NX runtime."""
    if not isinstance(identity, RuntimeIdentity) or identity != OBSERVED:
        raise UnsupportedRuntime("expected the T06 NX V11.0 / 11.0.0.33 C# profile")
    return identity
