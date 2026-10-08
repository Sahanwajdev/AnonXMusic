# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import os
import shutil
from pathlib import Path

from anony import logger


def ensure_dirs():
    """
    Ensure that the necessary directories exist and tools are available.
    """
    winget_paths = [
        r"C:\Users\SHNWAZ\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin",
        r"C:\Users\SHNWAZ\AppData\Local\Microsoft\WinGet\Packages\DenoLand.Deno_Microsoft.Winget.Source_8wekyb3d8bbwe",
    ]
    for p in winget_paths:
        if os.path.isdir(p) and p not in os.environ.get("PATH", ""):
            os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")

    if not shutil.which("deno") or not shutil.which("ffmpeg"):
        raise RuntimeError("Deno and FFmpeg must be installed and accessible in the system PATH.")

    for d in ["cache", "downloads"]:
        Path(d).mkdir(parents=True, exist_ok=True)
    logger.info("Cache directories updated.")

