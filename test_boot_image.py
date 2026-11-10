import shutil
import tempfile
import unittest
from pathlib import Path

from build_bios import (
    BOOT_IMAGE_NAME,
    EL_TORITO_CATALOG_LBA,
    FLOPPY_IMAGE_LBA,
    FLOPPY_SIZE,
    ISO_SECTOR_SIZE,
    ROOT_DIRECTORY_LBA,
    SECTOR_SIZE,
    build_image,
    build_iso,
)


class BootImageTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("nasm"), "NASM is needed to assemble the kernel")
    def test_builds_bios_bootable_floppy_image(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = build_image(Path(temp_dir) / "jadevos.img")
            image = image_path.read_bytes()

        self.assertEqual(len(image), FLOPPY_SIZE)
        self.assertEqual(image[510:512], b"\x55\xaa")
        self.assertIn(b"JadevOS Computers", image[SECTOR_SIZE:])
        self.assertIn(b"REBOOT", image[SECTOR_SIZE:])

    def test_builds_iso_with_bootable_floppy_emulation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            floppy_path = directory / "jadevos.img"
            floppy = bytearray(FLOPPY_SIZE)
            floppy[510:512] = b"\x55\xaa"
            floppy[SECTOR_SIZE : SECTOR_SIZE + 6] = b"kernel"
            floppy_path.write_bytes(floppy)

            iso_path = build_iso(floppy_path, directory / "jadevos.iso")
            iso = iso_path.read_bytes()

        self.assertEqual(len(iso) % ISO_SECTOR_SIZE, 0)
        self.assertEqual(
            iso[16 * ISO_SECTOR_SIZE + 1 : 16 * ISO_SECTOR_SIZE + 6], b"CD001"
        )
        self.assertEqual(
            iso[17 * ISO_SECTOR_SIZE + 7 : 17 * ISO_SECTOR_SIZE + 30],
            b"EL TORITO SPECIFICATION",
        )

        catalog = iso[
            EL_TORITO_CATALOG_LBA * ISO_SECTOR_SIZE :
            (EL_TORITO_CATALOG_LBA + 1) * ISO_SECTOR_SIZE
        ]
        self.assertEqual(catalog[30:32], b"\x55\xaa")
        self.assertEqual(catalog[1], 0)
        self.assertEqual(catalog[32], 0x88)
        self.assertEqual(catalog[33], 2)
        self.assertEqual(
            sum(
                int.from_bytes(catalog[index : index + 2], "little")
                for index in range(0, 32, 2)
            )
            & 0xFFFF,
            0,
        )
        self.assertEqual(
            int.from_bytes(catalog[40:44], "little"), FLOPPY_IMAGE_LBA
        )
        self.assertEqual(
            iso[
                FLOPPY_IMAGE_LBA * ISO_SECTOR_SIZE + SECTOR_SIZE :
                FLOPPY_IMAGE_LBA * ISO_SECTOR_SIZE + SECTOR_SIZE + 6
            ],
            b"kernel",
        )
        self.assertEqual(
            iso[
                FLOPPY_IMAGE_LBA * ISO_SECTOR_SIZE + 510 :
                FLOPPY_IMAGE_LBA * ISO_SECTOR_SIZE + 512
            ],
            b"\x55\xaa",
        )
        root_start = ROOT_DIRECTORY_LBA * ISO_SECTOR_SIZE
        self.assertIn(BOOT_IMAGE_NAME, iso[root_start : root_start + 128])


if __name__ == "__main__":
    unittest.main()
