"""Utility helpers for lightweight audio pre-processing steps."""

import logging
import os
import subprocess
import tempfile
from typing import Optional, Tuple

from .ffmpeg_utils import check_ffmpeg_installed

logger = logging.getLogger(__name__)

_AFFTDN_PRESETS = {
    "light": "afftdn=nf=-15",
    "medium": "afftdn=nf=-20",
    "strong": "afftdn=nf=-25",
}


def denoise_audio(
    input_path: str,
    *,
    strength: str = "medium",
) -> Tuple[bool, Optional[str], str]:
    """
    Apply a basic spectral noise reduction step using FFmpeg.

    Args:
        input_path: Original audio file.
        strength: One of 'light' | 'medium' | 'strong'. Controls the noise floor.

    Returns:
        Tuple of (success flag, output path if successful, message).
    """
    if not os.path.exists(input_path):
        return False, None, f"Input file not found: {input_path}"

    if not check_ffmpeg_installed():
        return False, None, "FFmpeg is required for noise reduction but is not installed."

    filter_expr = _AFFTDN_PRESETS.get(strength, _AFFTDN_PRESETS["medium"])

    # Write the denoised audio to a temporary WAV file so Whisper has a clean source.
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        output_path = tmp_file.name

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-af",
        filter_expr,
        "-acodec",
        "pcm_s16le",
        output_path,
    ]

    logger.info("Running denoise command: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stderr:
            logger.debug("FFmpeg denoise stderr: %s", result.stderr[:500])
        return True, output_path, "Noise reduction applied."
    except subprocess.CalledProcessError as exc:
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                logger.warning("Failed to delete temporary denoise file: %s", output_path)
        message = exc.stderr.strip() if exc.stderr else str(exc)
        logger.error("FFmpeg denoise failed: %s", message)
        return False, None, message
