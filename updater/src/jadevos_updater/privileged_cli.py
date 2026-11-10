"""Restricted command-line entry point for PolicyKit-authorized operations."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .core import UpdateError
from .install_bundle import install_bundle, reboot_system


def main(arguments: list[str] | None = None) -> int:
    args = sys.argv[1:] if arguments is None else arguments
    try:
        if len(args) == 3 and args[0] == "install":
            version, reboot_required = install_bundle(Path(args[1]), Path(args[2]))
            print(f"Installed JadevOS update {version}.", flush=True)
            print(
                f"reboot-required:{'true' if reboot_required else 'false'}",
                flush=True,
            )
            return 0
        if len(args) == 1 and args[0] == "reboot":
            reboot_system()
            return 0
        raise UpdateError("Invalid privileged command.")
    except (UpdateError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"JadevOS Updater: {error}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
