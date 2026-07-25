"""Load the supported interface locales and language-specific input aliases."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict, Iterable, Mapping, Tuple

from .resource_files import read_resource_text


SUPPORTED_LOCALES: Tuple[str, ...] = ("en-US", "zh-CN")
DEFAULT_LOCALE = "en-US"


def require_locale(value: Any) -> str:
    """Return a supported locale or raise a clear configuration error."""

    locale = str(value or DEFAULT_LOCALE)
    if locale not in SUPPORTED_LOCALES:
        raise ValueError(
            "Unsupported locale {!r}; choose one of: {}".format(
                locale, ", ".join(SUPPORTED_LOCALES)
            )
        )
    return locale


@lru_cache(maxsize=len(SUPPORTED_LOCALES))
def load_catalog(locale: str) -> Dict[str, Any]:
    """Load one immutable locale catalog from the packaged resources."""

    selected = require_locale(locale)
    payload = json.loads(read_resource_text("locales", "{}.json".format(selected)))
    if payload.get("locale") != selected:
        raise ValueError("Locale catalog identity does not match {!r}.".format(selected))
    return payload


def catalog_value(catalog: Mapping[str, Any], *path: str) -> Any:
    """Read a nested catalog value and fail when a required message is missing."""

    value: Any = catalog
    for part in path:
        if not isinstance(value, Mapping) or part not in value:
            raise KeyError("Missing locale message: {}".format(".".join(path)))
        value = value[part]
    return value


def merged_input_aliases() -> Dict[str, Tuple[str, ...]]:
    """Merge input-field aliases from every supported locale in stable order."""

    merged: Dict[str, list] = {}
    for locale in SUPPORTED_LOCALES:
        aliases = catalog_value(load_catalog(locale), "input_aliases")
        for role, values in aliases.items():
            output = merged.setdefault(str(role), [])
            for value in values:
                text = str(value)
                if text not in output:
                    output.append(text)
    return {role: tuple(values) for role, values in merged.items()}


__all__ = [
    "DEFAULT_LOCALE",
    "SUPPORTED_LOCALES",
    "catalog_value",
    "load_catalog",
    "merged_input_aliases",
    "require_locale",
]
