import logging
from functools import lru_cache
from typing import Optional

import opencc


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_converter() -> opencc.OpenCC:
    """Lazily create and cache the OpenCC converter."""
    return opencc.OpenCC("s2t")


def convert_to_traditional_chinese(text: Optional[str]) -> str:
    """Convert simplified Chinese text to traditional Chinese.

    When conversion fails the original text is returned.
    """

    if not text:
        # Preserve empty string/None semantics for callers.
        return text or ""

    try:
        converter = _get_converter()
        return converter.convert(text)
    except Exception as exc:
        logger.warning("Failed to convert to traditional Chinese: %s", exc)
        return text
