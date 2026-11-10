"""JadevOS Computers: a small, DOS-inspired command-line environment."""

from __future__ import annotations

import json
import os
import shlex
import sys
from datetime import datetime
from pathlib import Path


def new_directory() -> dict:
    return {"type": "dir", "children": {}}


class JadevOS:
    def __init__(self, data_file: Path | None = None) -> None:
        self.data_file = data_file or Path(__file__).with_name("jadevos_data.json")
        self.root = new_directory()
        self.cwd: list[str] = []
        self.prompt_format = "$P$G"
        self._load()

    def _load(self) -> None:
        if not self.data_file.exists():
            return
        data = json.loads(self.data_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("type") != "dir":
            raise ValueError(f"El sistema de archivos no es válido: {self.data_file}")
        self.root = data

    def _save(self) -> None:
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        temporary_file = self.data_file.with_suffix(self.data_file.suffix + ".tmp")
        temporary_file.write_text(
            json.dumps(self.root, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary_file.replace(self.data_file)

    def _parts(self, path: str) -> list[str]:
        path = path.strip().strip('"').replace("/", "\\")
        if len(path) >= 2 and path[1] == ":":
            if path[:2].upper() != "C:":
                raise ValueError("JadevOS solo dispone de la unidad C:.")
            path = path[2:]
        parts = [] if path.startswith("\\") else self.cwd.copy()
        for part in path.split("\\"):
            if not part or part == ".":
                continue
            if part == "..":
                if parts:
                    parts.pop()
                continue
            if part in (".", "..") or any(char in part for char in '<>:"|?*'):
                raise ValueError(f"Nombre de ruta no válido: {part}")
            parts.append(part)
        return parts

    def _get_node(self, parts: list[str]) -> dict:
        node = self.root
        for part in parts:
            if node.get("type") != "dir":
                raise ValueError(f"No es un directorio: {part}")
            child = node["children"].get(part)
            if child is None:
                child = next(
                    (value for key, value in node["children"].items()
                     if key.casefold() == part.casefold()),
                    None,
                )
            if child is None:
                location = "\\".join(parts)
                raise FileNotFoundError(f"No se encuentra: {location}")
            node = child
        return node

    def _parent_and_name(self, path: str) -> tuple[dict, str]:
        parts = self._parts(path)
        if not parts:
            raise ValueError("No se puede modificar la raíz de la unidad.")
        return self._get_node(parts[:-1]), parts[-1]

    def _find_name(self, directory: dict, name: str) -> str | None:
        return next(
            (key for key in directory["children"] if key.casefold() == name.casefold()),
            None,
        )

    @staticmethod
    def _arguments(text: str) -> list[str]:
        return [item.strip('"') for item in shlex.split(text, posix=False)]

    @property
    def prompt(self) -> str:
        location = "C:\\" + "\\".join(self.cwd)
        return self.prompt_format.replace("$P", location).replace("$G", ">")

    def execute(self, line: str) -> str:
        command, _, rest = line.strip().partition(" ")
        command = command.upper()
        if not command:
            return ""
        try:
            args = self._arguments(rest)
            if command in ("HELP", "?"):
                return (
                    "Comandos disponibles:\n"
                    "  HELP             Muestra esta ayuda\n"
                    "  DIR [ruta]       Lista archivos y directorios\n"
                    "  CD [ruta]        Muestra o cambia el directorio\n"
                    "  MD nombre        Crea un directorio\n"
                    "  RD nombre        Elimina un directorio vacío\n"
                    "  TYPE archivo     Muestra el contenido de un archivo\n"
                    "  ECHO texto       Muestra texto en pantalla\n"
                    "  COPY origen destino  Copia un archivo\n"
                    "  REN origen nuevo  Cambia el nombre de un archivo\n"
                    "  DEL archivo      Elimina un archivo\n"
                    "  CLS              Limpia la pantalla\n"
                    "  VER              Muestra la versión de JadevOS\n"
                    "  DATE / TIME      Muestra la fecha y la hora\n"
                    "  PROMPT formato   Cambia el indicador (por ejemplo, $P$G)\n"
                    "  EXIT             Cierra JadevOS"
                )
            if command == "CLS":
                return ""
            if command == "VER":
                return "JadevOS Computers [Version 1.0.0]"
            if command == "ECHO":
                if ">" in rest:
                    value, destination = rest.split(">", 1)
                    append = destination.startswith(">")
                    if append:
                        destination = destination[1:]
                    destination = destination.strip().strip('"')
                    parent, name = self._parent_and_name(destination)
                    if parent.get("type") != "dir":
                        return "La ruta destino no es un directorio."
                    existing_name = self._find_name(parent, name)
                    if existing_name is not None and parent["children"][existing_name]["type"] != "file":
                        return "El destino es un directorio."
                    if append and existing_name is not None:
                        value = parent["children"][existing_name]["content"] + value
                    parent["children"][existing_name or name] = {
                        "type": "file",
                        "content": value.strip().strip('"') + "\n",
                    }
                    self._save()
                    return ""
                return rest
            if command == "DATE":
                return datetime.now().strftime("%d/%m/%Y")
            if command == "TIME":
                return datetime.now().strftime("%H:%M:%S")
            if command == "PROMPT":
                self.prompt_format = rest or "$P$G"
                return ""
            if command == "CD":
                if not args:
                    return "C:\\" + "\\".join(self.cwd)
                destination = self._parts(args[0])
                if self._get_node(destination).get("type") != "dir":
                    return "El directorio especificado no existe."
                self.cwd = destination
                return ""
            if command == "DIR":
                directory = self._get_node(self._parts(args[0])) if args else self._get_node(self.cwd)
                if directory.get("type") != "dir":
                    return "La ruta especificada no es un directorio."
                entries = sorted(directory["children"].items(), key=lambda item: item[0].casefold())
                if not entries:
                    return "No hay archivos."
                lines = []
                for name, item in entries:
                    label = "<DIR>" if item["type"] == "dir" else "      "
                    lines.append(f"{label:6}  {name}")
                return "\n".join(lines)
            if command in ("MD", "MKDIR"):
                if len(args) != 1:
                    return "Uso: MD nombre"
                parent, name = self._parent_and_name(args[0])
                if parent.get("type") != "dir":
                    return "La ruta padre no es un directorio."
                if self._find_name(parent, name) is not None:
                    return "Ya existe un archivo o directorio con ese nombre."
                parent["children"][name] = new_directory()
                self._save()
                return ""
            if command in ("RD", "RMDIR"):
                if len(args) != 1:
                    return "Uso: RD nombre"
                parent, name = self._parent_and_name(args[0])
                actual_name = self._find_name(parent, name)
                if actual_name is None or parent["children"][actual_name]["type"] != "dir":
                    return "El directorio especificado no existe."
                if parent["children"][actual_name]["children"]:
                    return "El directorio no está vacío."
                del parent["children"][actual_name]
                self._save()
                return ""
            if command == "TYPE":
                if len(args) != 1:
                    return "Uso: TYPE archivo"
                node = self._get_node(self._parts(args[0]))
                return node["content"] if node.get("type") == "file" else "No es un archivo."
            if command in ("DEL", "ERASE"):
                if len(args) != 1:
                    return "Uso: DEL archivo"
                parent, name = self._parent_and_name(args[0])
                actual_name = self._find_name(parent, name)
                if actual_name is None or parent["children"][actual_name]["type"] != "file":
                    return "El archivo especificado no existe."
                del parent["children"][actual_name]
                self._save()
                return ""
            if command == "COPY":
                if len(args) != 2:
                    return "Uso: COPY origen destino"
                source = self._get_node(self._parts(args[0]))
                if source.get("type") != "file":
                    return "El origen no es un archivo."
                parent, name = self._parent_and_name(args[1])
                if parent.get("type") != "dir":
                    return "La ruta destino no es un directorio."
                if self._find_name(parent, name) is not None:
                    return "El destino ya existe."
                parent["children"][name] = {"type": "file", "content": source["content"]}
                self._save()
                return "        1 archivo(s) copiado(s)."
            if command in ("REN", "RENAME"):
                if len(args) != 2:
                    return "Uso: REN origen nuevo_nombre"
                parent, old_name = self._parent_and_name(args[0])
                actual_name = self._find_name(parent, old_name)
                if actual_name is None:
                    return "No se encuentra el archivo o directorio."
                if self._find_name(parent, args[1]) is not None:
                    return "Ya existe un archivo o directorio con ese nombre."
                parent["children"][args[1]] = parent["children"].pop(actual_name)
                self._save()
                return ""
            return f"'{command}' no se reconoce como un comando interno. Escribe HELP."
        except (ValueError, FileNotFoundError, json.JSONDecodeError) as error:
            return str(error)


def main() -> None:
    try:
        system = JadevOS()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"No se pudo iniciar JadevOS: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    print("JadevOS Computers [Version 1.0.0]")
    print("(c) JadevOS Computers. Escribe HELP para ver los comandos.\n")
    while True:
        try:
            line = input(system.prompt + " ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.strip().upper() == "EXIT":
            break
        if line.strip().upper() == "CLS":
            os.system("cls" if os.name == "nt" else "clear")
            continue
        output = system.execute(line)
        if output:
            print(output)


if __name__ == "__main__":
    main()
