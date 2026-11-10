"""Build the full Debian-based JadevOS live/installer ISO."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD_SCRIPT = ROOT / "scripts" / "build-live.sh"
DEFAULT_OUTPUT_DIR = ROOT / "dist"


def run(output: Path | None = None) -> Path:
    if not BUILD_SCRIPT.is_file():
        raise FileNotFoundError(f"Falta el script de compilacion: {BUILD_SCRIPT}")

    if output is None:
        output = DEFAULT_OUTPUT_DIR / "jadevos-tahoe.iso"
    elif not output.is_absolute():
        output = ROOT / output

    if os.name == "nt":
        wsl = shutil.which("wsl.exe")
        if wsl is None:
            raise RuntimeError(
                "No se encontro WSL. Instala WSL con Ubuntu 24.04 para compilar JadevOS."
            )
        distro = os.environ.get("JADEVOS_WSL_DISTRO", "Ubuntu")
        linux_root = subprocess.run(
            [wsl, "-d", distro, "--", "wslpath", "-u", str(ROOT)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        linux_output = subprocess.run(
            [wsl, "-d", distro, "--", "wslpath", "-u", str(output)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        command = [
            wsl,
            "-d",
            distro,
            "-u",
            "root",
            "--",
            "bash",
            f"{linux_root}/scripts/build-live.sh",
            linux_root,
            linux_output,
        ]
    else:
        command = ["bash", str(BUILD_SCRIPT), str(ROOT), str(output)]

    subprocess.run(command, check=True)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="ruta del ISO (por defecto, crea un nombre nuevo con fecha y hora)",
    )
    try:
        run(parser.parse_args().output)
    except (OSError, subprocess.CalledProcessError, RuntimeError) as error:
        print(f"Error al construir JadevOS: {error}", file=sys.stderr)
        raise SystemExit(1) from error
