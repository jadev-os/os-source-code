import tempfile
import unittest
from pathlib import Path

from jadevos import JadevOS


class JadevOSTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.system = JadevOS(Path(self.temp_dir.name) / "filesystem.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_directories_are_created_and_persisted(self):
        self.assertEqual(self.system.execute("MD docs"), "")
        self.assertEqual(self.system.execute("CD docs"), "")
        self.assertEqual(self.system.prompt, "C:\\docs>")
        self.assertEqual(JadevOS(self.system.data_file).execute("CD docs"), "")

    def test_paths_cannot_escape_virtual_root(self):
        self.system.execute("MD docs")
        self.system.execute("CD docs")
        self.assertEqual(self.system.execute("CD .."), "")
        self.assertEqual(self.system.execute("CD .."), "")
        self.assertEqual(self.system.execute("DIR"), "<DIR>   docs")

    def test_unknown_commands_and_invalid_paths_report_errors(self):
        self.assertIn("no se reconoce", self.system.execute("FORMAT C:"))
        self.assertIn("unidad C:", self.system.execute("CD D:\\"))

    def test_empty_directory_removal(self):
        self.system.execute("MD docs")
        self.assertEqual(self.system.execute("RD docs"), "")
        self.assertEqual(self.system.execute("DIR"), "No hay archivos.")

    def test_echo_creates_files_and_copy_duplicates_them(self):
        self.assertEqual(self.system.execute("ECHO Hola mundo > saludo.txt"), "")
        self.assertEqual(self.system.execute("TYPE saludo.txt"), "Hola mundo\n")
        self.assertEqual(
            self.system.execute("COPY saludo.txt copia.txt"),
            "        1 archivo(s) copiado(s).",
        )
        self.assertEqual(self.system.execute("TYPE copia.txt"), "Hola mundo\n")

    def test_redirection_cannot_write_outside_virtual_filesystem(self):
        self.system.execute("ECHO no > ..\\archivo.txt")
        self.assertFalse((Path(self.temp_dir.name) / "archivo.txt").exists())
        self.assertEqual(self.system.execute("TYPE archivo.txt"), "no\n")


if __name__ == "__main__":
    unittest.main()
