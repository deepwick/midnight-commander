import configparser
import gzip
import os
import shutil
import struct
import subprocess
import zlib
from pathlib import Path

import pytest

from deepwick_spec.ansi import runs
from deepwick_spec.check_port import check_port
from deepwick_spec.palette import load_palette
from deepwick_spec.tui import capture, tmux_available

REPO = Path(__file__).resolve().parents[1]
PALETTE = load_palette()
C = PALETTE.colors
MC = Path("/usr/bin/mc")
NAMES = {"black", "red", "green", "brown", "blue", "magenta", "cyan", "lightgray", "gray", "brightred",
         "brightgreen", "yellow", "brightblue", "brightmagenta", "brightcyan", "white", "default", ""}
ATTRS = {"bold", "underline", "italic", "reverse", "blink"}
COLOR_SECTIONS = {"core", "dialog", "error", "filehighlight", "menu", "popupmenu", "buttonbar", "statusbar",
                  "help", "editor", "viewer", "diffviewer"}
TRUECOLOR_FILES = {
    "directory": ("dw_blue", "bold"), "executable": ("dw_green", "bold"), "symlink": ("dw_cyan", ""),
    "hardlink": ("dw_cyan", ""), "stalelink": ("dw_red", ""), "device": ("dw_gold", ""),
    "special": ("dw_gold", ""), "archive": ("dw_rose", ""), "media": ("dw_magenta", ""),
    "graph": ("dw_magenta", ""), "doc": ("dw_orange", ""), "source": ("dw_yellow", ""),
    "temp": ("dw_muted", ""), "core": ("dw_muted", ""), "database": ("dw_teal", ""),
}
SCREEN = {"src": "directory", "run.sh": "executable", "broken": "brokenSymlink", "pipe": "special",
          "bundle.tar.gz": "archive", "photo.png": "media", "notes.pdf": "document", "app.py": "source", "old.bak": "temp"}


def isolated_env(tmp_path, **extra):
    dirs = {"HOME": tmp_path / "home"}
    for kind in ("CONFIG", "DATA", "STATE", "CACHE"):
        dirs[f"XDG_{kind}_HOME"] = tmp_path / kind.lower()
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    env = {key: str(path) for key, path in dirs.items()}
    env.update({key: str(value) for key, value in extra.items()})
    return env


def style_containing(text, needle):
    for chunk, style in runs(text):
        if needle in chunk:
            return style
    raise AssertionError(f"no run contains {needle!r}")


def has_bg(text, name):
    return any(style["bg"] == C[name].lower() for _, style in runs(text))


def has_fg(text, name):
    return any(style["fg"] == C[name].lower() for _, style in runs(text))


TREE_ROLES = {
    "src": "directory", "run.sh": "executable", "link": "symlink", "broken": "brokenSymlink",
    "pipe": "special", "bundle.tar.gz": "archive", "photo.png": "media", "notes.pdf": "document",
    "app.py": "source", "old.bak": "temp",
}


def tiny_png() -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))
    header = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(b"\x00\x00")) + chunk(b"IEND", b"")


def make_tree(root):
    root.mkdir(parents=True, exist_ok=True)
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("def main():\n    return 0\n")
    (root / "run.sh").write_text("#!/bin/sh\necho run\n")
    (root / "run.sh").chmod(0o755)
    (root / "app.py").write_text("print('hi')\n")
    (root / "link").symlink_to("app.py")
    (root / "broken").symlink_to("missing")
    os.mkfifo(root / "pipe")
    (root / "bundle.tar.gz").write_bytes(gzip.compress(b"deepwick"))
    (root / "photo.png").write_bytes(tiny_png())
    (root / "notes.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    (root / "old.bak").write_text("old\n")
    return root


def skin(name):
    path = REPO / name
    assert path.is_file(), f"{name} missing"
    parser = configparser.ConfigParser(interpolation=None, delimiters=("=",))
    parser.optionxform = str
    parser.read_string(path.read_text(encoding="utf-8"))
    return parser


def values(parser):
    for section in COLOR_SECTIONS & set(parser.sections()):
        for key, value in parser[section].items():
            parts = [p.strip() for p in value.split(";")] + ["", ""]
            yield section, key, parts[0], parts[1], parts[2]


def test_truecolor_skin_uses_palette_aliases():
    p = skin("deepwick.ini")
    assert p["skin"]["truecolors"] == "true"
    aliases = dict(p["aliases"])
    allowed = {v.lower() for v in C.values()}
    assert all(v.lower() in allowed for v in aliases.values())
    for section, key, fg, bg, attrs in values(p):
        assert fg in aliases or fg == "", (section, key, fg)
        assert bg in aliases or bg == "", (section, key, bg)
        assert set(filter(None, attrs.split("+"))) <= ATTRS, (section, key, attrs)


def test_truecolor_filehighlight_follows_file_roles():
    fh = skin("deepwick.ini")["filehighlight"]
    for key, (fg, attrs) in TRUECOLOR_FILES.items():
        parts = [s.strip() for s in fh[key].split(";")] + ["", ""]
        assert (parts[0], parts[2]) == (fg, attrs), key


def test_16_color_skin_uses_ansi_names_only():
    p = skin("deepwick16.ini")
    assert "truecolors" not in p["skin"]
    for section, key, fg, bg, attrs in values(p):
        assert fg in NAMES and bg in NAMES, (section, key, fg, bg)
        assert set(filter(None, attrs.split("+"))) <= ATTRS, (section, key, attrs)


requires_mc = pytest.mark.skipif(not (tmux_available() and MC.is_file()), reason="requires tmux and /usr/bin/mc")


@requires_mc
def test_mc_binary_is_midnight_commander():
    out = subprocess.run([str(MC), "--version"], capture_output=True, text=True).stdout
    assert "GNU Midnight Commander" in out


def run_mc(tmp_path, skin_name, **extra):
    tree = make_tree(tmp_path / "tree")
    env = isolated_env(tmp_path, TERM="tmux-256color", MC_SKIN=skin_name, **extra)
    skins = Path(env["XDG_DATA_HOME"]) / "mc" / "skins"
    skins.mkdir(parents=True)
    for name in ("deepwick.ini", "deepwick16.ini"):
        shutil.copy(REPO / name, skins / name)
    return capture(f"cd {tree} && exec env -u MC_SID {MC} -u", env, size=(120, 30), wait_for="run.sh", timeout=20)


@requires_mc
def test_mc_truecolor_skin_renders_file_roles(tmp_path):
    out = run_mc(tmp_path, "deepwick")
    assert "Unable to use" not in out
    assert has_bg(out, "background")
    assert has_bg(out, "selection")
    for name, role in SCREEN.items():
        expected = PALETTE.files[role]
        style = style_containing(out, name)
        assert style["fg"] == C[expected.color].lower(), (name, style)
        assert style["bold"] == ("bold" in expected.style), (name, style)


@requires_mc
def test_mc_16_color_skin_without_colorterm(tmp_path):
    out = run_mc(tmp_path, "deepwick16", COLORTERM="")
    assert "Unable to use" not in out
    assert style_containing(out, "src")["fg"] == "ansi:4"
    assert style_containing(out, "run.sh")["fg"] == "ansi:2"


def test_port_conventions():
    assert check_port(REPO, PALETTE.allowed_hex()) == []
