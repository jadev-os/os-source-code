"""Build the legacy BIOS-demo images; this is not the full JadevOS operating system."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FLOPPY_SIZE = 1_474_560
SECTOR_SIZE = 512
KERNEL_SECTORS = 17
ISO_SECTOR_SIZE = 2048
EL_TORITO_CATALOG_LBA = 22
FLOPPY_IMAGE_LBA = 23
ROOT_DIRECTORY_LBA = 21
LITTLE_ENDIAN_PATH_TABLE_LBA = 19
BIG_ENDIAN_PATH_TABLE_LBA = 20
ISO_VOLUME_ID = b"JADEVOS"
BOOT_IMAGE_NAME = b"JADEVOS.IMG;1"


def build_image(output: Path) -> Path:
    nasm = shutil.which("nasm")
    if nasm is None:
        raise RuntimeError("No se encontro NASM. Instala NASM y vuelve a intentarlo.")

    with tempfile.TemporaryDirectory(prefix="jadevos-build-") as temp_dir:
        temp = Path(temp_dir)
        boot_path = temp / "boot.bin"
        kernel_path = temp / "kernel.bin"
        subprocess.run(
            [nasm, "-f", "bin", "-o", str(boot_path), str(ROOT / "boot.asm")],
            check=True,
        )
        subprocess.run(
            [nasm, "-f", "bin", "-o", str(kernel_path), str(ROOT / "kernel.asm")],
            check=True,
        )
        boot = boot_path.read_bytes()
        kernel = kernel_path.read_bytes()

    if len(boot) != SECTOR_SIZE or boot[510:512] != b"\x55\xaa":
        raise ValueError("El sector de arranque debe medir 512 bytes y terminar en 55 AA.")
    if len(kernel) > KERNEL_SECTORS * SECTOR_SIZE:
        raise ValueError("El kernel supera el espacio reservado en la imagen.")

    image = bytearray(FLOPPY_SIZE)
    image[:SECTOR_SIZE] = boot
    image[SECTOR_SIZE : SECTOR_SIZE + len(kernel)] = kernel
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(image)
    return output


def _both_endian(value: int, size: int) -> bytes:
    return value.to_bytes(size, "little") + value.to_bytes(size, "big")


def _directory_record(
    name: bytes, extent: int, size: int, is_directory: bool = False
) -> bytes:
    record_length = 33 + len(name) + (1 if len(name) % 2 == 0 else 0)
    record = bytearray(record_length)
    record[0] = record_length
    record[2:10] = _both_endian(extent, 4)
    record[10:18] = _both_endian(size, 4)
    record[18:25] = bytes((126, 1, 1, 0, 0, 0, 0))
    record[25] = 2 if is_directory else 0
    record[28:32] = _both_endian(1, 2)
    record[32] = len(name)
    record[33 : 33 + len(name)] = name
    return bytes(record)


def build_iso(floppy_image: Path, output: Path) -> Path:
    floppy = floppy_image.read_bytes()
    if len(floppy) != FLOPPY_SIZE or floppy[510:512] != b"\x55\xaa":
        raise ValueError("La imagen de disquete debe ser arrancable y medir 1.44 MB.")

    total_sectors = FLOPPY_IMAGE_LBA + len(floppy) // ISO_SECTOR_SIZE
    iso = bytearray(total_sectors * ISO_SECTOR_SIZE)

    primary = bytearray(ISO_SECTOR_SIZE)
    primary[0:7] = b"\x01CD001\x01"
    primary[8:40] = b"JADEVOS".ljust(32)
    primary[40:72] = ISO_VOLUME_ID.ljust(32)
    primary[80:88] = _both_endian(total_sectors, 4)
    primary[120:124] = _both_endian(1, 2)
    primary[124:128] = _both_endian(1, 2)
    primary[128:132] = _both_endian(ISO_SECTOR_SIZE, 2)
    primary[132:140] = _both_endian(10, 4)
    primary[140:144] = LITTLE_ENDIAN_PATH_TABLE_LBA.to_bytes(4, "little")
    primary[148:152] = BIG_ENDIAN_PATH_TABLE_LBA.to_bytes(4, "big")
    primary[156:190] = _directory_record(
        b"\x00", ROOT_DIRECTORY_LBA, 2048, is_directory=True
    )
    primary[881] = 1
    iso[16 * ISO_SECTOR_SIZE : 17 * ISO_SECTOR_SIZE] = primary

    boot_descriptor = bytearray(ISO_SECTOR_SIZE)
    boot_descriptor[0:7] = b"\x00CD001\x01"
    boot_descriptor[7:39] = b"EL TORITO SPECIFICATION".ljust(32, b"\x00")
    boot_descriptor[71:75] = EL_TORITO_CATALOG_LBA.to_bytes(4, "little")
    iso[17 * ISO_SECTOR_SIZE : 18 * ISO_SECTOR_SIZE] = boot_descriptor

    terminator = bytearray(ISO_SECTOR_SIZE)
    terminator[0:7] = b"\xffCD001\x01"
    iso[18 * ISO_SECTOR_SIZE : 19 * ISO_SECTOR_SIZE] = terminator

    path_table = bytes((1, 0)) + ROOT_DIRECTORY_LBA.to_bytes(4, "little")
    path_table += (1).to_bytes(2, "little") + b"\x00\x00"
    start = LITTLE_ENDIAN_PATH_TABLE_LBA * ISO_SECTOR_SIZE
    iso[start : start + len(path_table)] = path_table
    big_path_table = bytes((1, 0)) + ROOT_DIRECTORY_LBA.to_bytes(4, "big")
    big_path_table += (1).to_bytes(2, "big") + b"\x00\x00"
    start = BIG_ENDIAN_PATH_TABLE_LBA * ISO_SECTOR_SIZE
    iso[start : start + len(big_path_table)] = big_path_table

    root_directory = _directory_record(
        b"\x00", ROOT_DIRECTORY_LBA, 2048, is_directory=True
    )
    root_directory += _directory_record(
        b"\x01", ROOT_DIRECTORY_LBA, 2048, is_directory=True
    )
    root_directory += _directory_record(
        BOOT_IMAGE_NAME, FLOPPY_IMAGE_LBA, FLOPPY_SIZE
    )
    iso[
        ROOT_DIRECTORY_LBA * ISO_SECTOR_SIZE :
        ROOT_DIRECTORY_LBA * ISO_SECTOR_SIZE + len(root_directory)
    ] = root_directory

    catalog = bytearray(ISO_SECTOR_SIZE)
    catalog[0] = 1
    catalog[1] = 0
    catalog[4:28] = b"JADEVOS".ljust(24)
    catalog[30:32] = b"\x55\xaa"
    checksum = (-sum(
        int.from_bytes(catalog[index : index + 2], "little")
        for index in range(0, 32, 2)
        if index != 28
    )) & 0xFFFF
    catalog[28:30] = checksum.to_bytes(2, "little")
    catalog[32] = 0x88
    catalog[33] = 2
    catalog[38:40] = (1).to_bytes(2, "little")
    catalog[40:44] = FLOPPY_IMAGE_LBA.to_bytes(4, "little")
    start = EL_TORITO_CATALOG_LBA * ISO_SECTOR_SIZE
    iso[start : start + ISO_SECTOR_SIZE] = catalog

    start = FLOPPY_IMAGE_LBA * ISO_SECTOR_SIZE
    iso[start : start + FLOPPY_SIZE] = floppy

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(iso)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist" / "jadevos-bios-legacy.img",
        help="ruta para la imagen de disquete de demostracion",
    )
    parser.add_argument(
        "--iso-output",
        type=Path,
        default=ROOT / "dist" / "jadevos-bios-legacy.iso",
        help="ruta para la ISO de demostracion BIOS",
    )
    args = parser.parse_args()
    try:
        image = build_image(args.output)
        iso = build_iso(image, args.iso_output)
    except (OSError, subprocess.CalledProcessError, RuntimeError, ValueError) as error:
        parser.exit(1, f"Error al crear las imagenes: {error}\n")
    print(f"Imagen arrancable creada: {image}")
    print(f"ISO arrancable creada: {iso}")


if __name__ == "__main__":
    main()
