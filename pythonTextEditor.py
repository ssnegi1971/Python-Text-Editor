#!/usr/bin/env python3
"""
txt_studio.py - a small desktop browser + editor for text and code files.

Left pane  : the text and code files in the folder you picked, each row with
             a "x" to remove it from the list, plus New File / Open File
             actions that add the file to the list too.
Right pane : an editor for the file you open, with a line-number gutter.

Features
    * Scan a chosen directory for text and code files (.txt, .py, .js, .md,
      .json, .c, .cpp, .java, .go, .rs, .sql, .sh and ~80 more) and list them
    * A "Showing" filter switches between text & code, plain text only, and
      every file in the folder
    * "x" on a row removes that file from the left pane (never from the disk);
      if it is the file you have open, it is closed first (with a save prompt)
    * New File: create a file in the scanned folder, listed and opened
    * Open File: open any file (files outside the folder join the list too)
    * Save / Save As, with an "unsaved changes" guard
    * Close file, Go to line, Find & replace (case / whole word / regex)
    * Every match is highlighted yellow in the editor as you type; the match
      Find jumps to is amber

Standard library only: tkinter. No third-party packages.

Run:
    python3 txt_studio.py                # then use "Choose Folder..."
    python3 txt_studio.py ~/notes        # start in a folder

Keys:
    Ctrl+N  new file        Ctrl+O  open file       Ctrl+Shift+O  choose folder
    Ctrl+S  save            Ctrl+Shift+S  save as   Ctrl+W  close file
    Ctrl+F  find & replace  Ctrl+G  go to line      F5      rescan folder
    Delete  remove the selected row from the left pane      Ctrl+Q  quit

Notes:
    Files are decoded as UTF-8, then cp1252 / latin-1 as a fallback, and are
    written back in the encoding they were read in. The file's own line-ending
    style (LF or CRLF) is preserved.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, simpledialog, ttk

APP_NAME = "txt studio"
DEFAULT_SUFFIX = ".txt"

FILTER_TEXT_AND_CODE = "Text & code"
FILTER_TEXT_ONLY = "Text files only"
FILTER_ALL_FILES = "All files"
FILTER_CHOICES = (FILTER_TEXT_AND_CODE, FILTER_TEXT_ONLY, FILTER_ALL_FILES)

TEXT_EXTENSIONS = (".txt", ".text", ".md", ".markdown", ".rst", ".log", ".tex")

CODE_EXTENSIONS = TEXT_EXTENSIONS + (
    # data & config
    ".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".conf", ".config", ".xml", ".properties", ".env",
    # web
    ".html", ".htm", ".xhtml", ".css", ".scss", ".sass", ".less",
    ".vue", ".svelte", ".svg",
    # python
    ".py", ".pyw", ".pyi", ".ipynb",
    # javascript / typescript
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    # c family and jvm
    ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hxx", ".hh",
    ".m", ".mm", ".cs", ".java", ".kt", ".kts", ".scala", ".groovy",
    # other languages
    ".go", ".rs", ".rb", ".erb", ".php", ".swift", ".dart", ".lua",
    ".pl", ".pm", ".r", ".jl", ".hs", ".ex", ".exs", ".erl", ".clj",
    ".cljs", ".vb", ".f", ".f90", ".f95", ".asm", ".s", ".sql",
    ".sh", ".bash", ".zsh", ".fish", ".bat", ".cmd", ".ps1",
)

# extensionless files that are still code / text
CODE_FILENAMES = (
    "makefile", "dockerfile", "gemfile", "rakefile", "procfile", "jenkinsfile",
    "vagrantfile", "pipfile", "cmakelists.txt", ".gitignore", ".gitattributes",
    ".editorconfig", ".env", ".bashrc", ".zshrc",
)
READ_ENCODINGS = ("utf-8", "utf-8-sig", "cp1252", "latin-1")

GUTTER_BG = "#f3f4f6"
GUTTER_FG = "#9ca3af"
GUTTER_FG_CURRENT = "#111827"
EDITOR_BG = "#ffffff"
EDITOR_FG = "#1f2937"
HIGHLIGHT_BG = "#fff3b0"
MATCH_BG = "#fff59d"          # every find hit
MATCH_CURRENT_BG = "#ffb300"    # the hit Find just jumped to
ROW_CURRENT_BG = "#e8f0fe"
CLOSE_GLYPH = "\u00d7"


# --------------------------------------------------------------------------- #
# Pure helpers (no Tk needed - easy to test)
# --------------------------------------------------------------------------- #
def matches_filter(name: str, extensions=CODE_EXTENSIONS, all_files: bool = False,
                   named=CODE_FILENAMES) -> bool:
    """True when *name* belongs in the left pane under the current filter."""
    if all_files:
        return True
    lower = name.lower()
    if named and lower in named:
        return True
    return lower.endswith(tuple(e.lower() for e in extensions))


def scan_files(folder: str, recursive: bool = True, extensions=CODE_EXTENSIONS,
               all_files: bool = False, named=CODE_FILENAMES) -> list[str]:
    """Return sorted paths of matching files under *folder*, relative to it."""
    found: list[str] = []
    if recursive:
        for root, dirs, names in os.walk(folder, onerror=lambda e: None):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            for name in names:
                if matches_filter(name, extensions, all_files, named):
                    found.append(os.path.relpath(os.path.join(root, name), folder))
    else:
        try:
            entries = os.listdir(folder)
        except OSError:
            entries = []
        for name in entries:
            full = os.path.join(folder, name)
            if os.path.isfile(full) and matches_filter(name, extensions, all_files, named):
                found.append(name)
    found.sort(key=lambda p: (p.count(os.sep), p.lower()))
    return found


def file_patterns(extensions) -> str:
    """Tk filetype pattern string, e.g. '*.txt *.md *.py'."""
    return " ".join("*" + e for e in extensions)


def is_inside(path: str, folder: str) -> bool:
    """True when *path* lives under *folder* (after normalising both)."""
    if not folder:
        return False
    path = os.path.abspath(path)
    folder = os.path.abspath(folder)
    try:
        return os.path.commonpath([path, folder]) == folder
    except ValueError:          # different drives on Windows
        return False


def display_label(path: str, folder: str | None) -> str:
    """Short label for the left pane: relative when inside the folder."""
    if folder and is_inside(path, folder):
        try:
            rel = os.path.relpath(path, folder)
            return rel.replace(os.sep, "/")
        except ValueError:
            pass
    return path.replace(os.sep, "/")


def merge_entries(scanned: list[str], external: list[str],
                  folder: str | None) -> list[str]:
    """Combine scan results with files opened from elsewhere.

    Duplicates are dropped, missing files are skipped, and entries inside the
    folder are listed before outside ones.
    """
    result: list[str] = []
    seen: set[str] = set()
    for path in list(scanned) + list(external):
        if not path:
            continue
        norm = os.path.normcase(os.path.abspath(path))
        if norm in seen:
            continue
        if not os.path.isfile(path):
            continue
        seen.add(norm)
        result.append(os.path.abspath(path))
    inside = [p for p in result if is_inside(p, folder)] if folder else []
    outside = [p for p in result if p not in inside]
    inside.sort(key=lambda p: (display_label(p, folder).count("/"),
                               display_label(p, folder).lower()))
    outside.sort(key=lambda p: os.path.basename(p).lower())
    return inside + outside


def read_text_file(path: str) -> tuple[str, str, str]:
    """Read *path* and return (text, encoding, newline).

    Newlines are normalised to "\\n" in memory; the original style is returned
    so it can be written back unchanged.
    """
    with open(path, "rb") as fh:
        raw = fh.read()
    newline = "\r\n" if b"\r\n" in raw else ("\r" if b"\r" in raw else "\n")
    text, encoding = None, "utf-8"
    for enc in READ_ENCODINGS:
        try:
            text = raw.decode(enc)
            encoding = enc
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text, encoding = raw.decode("utf-8", "replace"), "utf-8"
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text, encoding, newline


def write_text_file(path: str, text: str, encoding: str, newline: str) -> None:
    """Write *text* (LF in memory) back out with the original newline style."""
    data = text if newline == "\n" else text.replace("\n", newline)
    with open(path, "w", encoding=encoding, newline="") as fh:
        fh.write(data)


def compile_pattern(needle: str, case: bool = False, whole: bool = False,
                    regex: bool = False):
    """Compile *needle* into a regex, honouring the search options."""
    if not needle:
        return None
    pattern = needle if regex else re.escape(needle)
    if whole:
        pattern = r"\b(?:" + pattern + r")\b"
    return re.compile(pattern, 0 if case else re.IGNORECASE)


def offset_to_index(content: str, offset: int) -> str:
    """Convert a character offset into a Tk text index ("line.col")."""
    offset = max(0, min(offset, len(content)))
    line = content.count("\n", 0, offset) + 1
    col = offset - (content.rfind("\n", 0, offset) + 1)
    return f"{line}.{col}"


def index_to_offset(content: str, index: str) -> int:
    """Convert a Tk text index ("line.col") into a character offset."""
    line_s, _, col_s = str(index).partition(".")
    line = int(line_s or 1)
    col = int(col_s or 0)
    pos = 0
    for _ in range(line - 1):
        nxt = content.find("\n", pos)
        if nxt < 0:
            return len(content)
        pos = nxt + 1
    return min(pos + col, len(content))


# --------------------------------------------------------------------------- #
# Find & replace dialog
# --------------------------------------------------------------------------- #
class FindReplaceDialog(tk.Toplevel):
    def __init__(self, app: "TxtStudio"):
        super().__init__(app)
        self.app = app
        self.title("Find & Replace")
        self.transient(app)
        self.resizable(False, False)

        self.find_var = tk.StringVar()
        self.repl_var = tk.StringVar()
        self.case_var = tk.BooleanVar(value=False)
        self.word_var = tk.BooleanVar(value=False)
        self.regex_var = tk.BooleanVar(value=False)
        self.info_var = tk.StringVar(value="Esc closes this window.")
        self._pending: str | None = None
        self.find_var.trace_add("write", lambda *a: self.schedule_highlight())

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="Find:").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.find_entry = ttk.Entry(body, textvariable=self.find_var, width=38)
        self.find_entry.grid(row=0, column=1, sticky="ew", pady=(0, 6))

        ttk.Label(body, text="Replace:").grid(row=1, column=0, sticky="w", pady=(0, 6))
        self.repl_entry = ttk.Entry(body, textvariable=self.repl_var, width=38)
        self.repl_entry.grid(row=1, column=1, sticky="ew", pady=(0, 6))

        opts = ttk.Frame(body)
        opts.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 10))
        ttk.Checkbutton(opts, text="Match case", variable=self.case_var,
                        command=self.apply_highlights).pack(side="left")
        ttk.Checkbutton(opts, text="Whole word", variable=self.word_var,
                        command=self.apply_highlights).pack(side="left", padx=(10, 0))
        ttk.Checkbutton(opts, text="Regex", variable=self.regex_var,
                        command=self.apply_highlights).pack(side="left", padx=(10, 0))

        buttons = ttk.Frame(body)
        buttons.grid(row=3, column=0, columnspan=2, sticky="ew")
        ttk.Button(buttons, text="Find", width=10, command=self.on_find).pack(side="left")
        ttk.Button(buttons, text="Replace", width=10, command=self.on_replace).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Replace All", command=self.on_replace_all).pack(side="right")

        ttk.Label(body, textvariable=self.info_var, foreground="#6b7280").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))

        self.find_entry.bind("<Return>", lambda e: self.on_find())
        self.repl_entry.bind("<Return>", lambda e: self.on_replace())
        self.bind("<Escape>", lambda e: self._close())
        self.protocol("WM_DELETE_WINDOW", self._close)

        selection = self.app.selected_text()
        if selection and "\n" not in selection and len(selection) < 200:
            self.find_var.set(selection)

        self.show_on_screen()
        self.find_entry.focus_set()
        self.find_entry.select_range(0, "end")

    # -- window handling --------------------------------------------------- #
    def show_on_screen(self) -> None:
        """Put the popup near the main window's top-right and raise it."""
        self.update_idletasks()
        width = max(self.winfo_reqwidth(), 400)
        height = self.winfo_reqheight()
        try:
            x = self.app.winfo_rootx() + self.app.winfo_width() - width - 40
            y = self.app.winfo_rooty() + 70
        except tk.TclError:
            x, y = 120, 120
        x = max(0, min(x, self.winfo_screenwidth() - width - 10))
        y = max(0, min(y, self.winfo_screenheight() - height - 60))
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.deiconify()
        self.lift()
        try:
            self.attributes("-topmost", True)

            def drop_topmost():
                try:
                    self.attributes("-topmost", False)
                except tk.TclError:
                    pass

            self.after(400, drop_topmost)
        except tk.TclError:
            pass
        self.focus_force()

    # -- live highlighting -------------------------------------------------- #
    def apply_highlights(self) -> None:
        """Yellow-highlight every match of whatever is in the Find box."""
        needle, case, whole, regex = self._search_options()
        if not needle:
            self.app.clear_highlights()
            self.info_var.set("Type something to find.")
            return
        count = self.app.highlight_all(needle, case, whole, regex)
        if count:
            self.info_var.set(f"{count} match(es) highlighted in yellow.")
        else:
            self.info_var.set(f"No match for \u201c{needle}\u201d.")

    def schedule_highlight(self, delay: int = 150) -> None:
        """Debounce re-highlighting while the user is still typing."""
        if self._pending is not None:
            try:
                self.after_cancel(self._pending)
            except tk.TclError:
                pass
        self._pending = self.after(delay, self.apply_highlights)

    # -- actions ---------------------------------------------------------- #
    def _search_options(self) -> tuple[str, bool, bool, bool]:
        return (self.find_var.get(), self.case_var.get(),
                self.word_var.get(), self.regex_var.get())

    def on_find(self) -> None:
        needle, case, whole, regex = self._search_options()
        if not needle:
            self.info_var.set("Type something to find.")
            return
        result = self.app.find_next(needle, case, whole, regex)
        if result is None:
            self.info_var.set("No file is open.")
        elif result["count"] == 0:
            self.info_var.set(f"No match for \u201c{needle}\u201d.")
        elif result["wrapped"]:
            self.info_var.set(f"Wrapped to the top \u2014 {result['count']} match(es) in file.")
        else:
            self.info_var.set(f"{result['count']} match(es) in file.")

    def on_replace(self) -> None:
        needle, case, whole, regex = self._search_options()
        if not needle:
            self.info_var.set("Type something to find.")
            return
        status = self.app.replace_current(needle, self.repl_var.get(), case, whole, regex)
        self.info_var.set(status)

    def on_replace_all(self) -> None:
        needle, case, whole, regex = self._search_options()
        if not needle:
            self.info_var.set("Type something to find.")
            return
        status = self.app.replace_all(needle, self.repl_var.get(), case, whole, regex)
        self.info_var.set(status)

    def _close(self) -> None:
        if self._pending is not None:
            try:
                self.after_cancel(self._pending)
            except tk.TclError:
                pass
            self._pending = None
        self.app.clear_highlights()
        self.app._find_dialog = None
        self.destroy()


# --------------------------------------------------------------------------- #
# Main window
# --------------------------------------------------------------------------- #
class TxtStudio(tk.Tk):
    def __init__(self, folder: str | None = None):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1040x660")
        self.minsize(700, 440)

        self.folder: str | None = None
        self.current_path: str | None = None
        self.encoding = "utf-8"
        self.newline = "\n"
        self.dirty = False
        self.entries: list[str] = []      # absolute paths shown in the left pane
        self.external: list[str] = []     # files opened from outside the folder
        self._iid_path: dict[str, str] = {}
        self._find_dialog: FindReplaceDialog | None = None

        base = tkfont.nametofont("TkFixedFont").actual()
        self.editor_font = tkfont.Font(family=base["family"], size=12)
        self.ui_font = tkfont.nametofont("TkDefaultFont")
        self.bold_font = tkfont.Font(font=self.ui_font)
        self.bold_font.configure(weight="bold")

        ttk.Style(self).configure("Treeview", rowheight=24)

        self._build_toolbar()
        self._build_status()
        self._build_body()
        self._build_menu()
        self._bind_keys()

        self.set_editor_enabled(False)
        self.update_status()

        if folder and os.path.isdir(folder):
            self.load_folder(folder)
        self.protocol("WM_DELETE_WINDOW", self.on_quit)

    # -- layout ----------------------------------------------------------- #
    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self, padding=(10, 8))
        bar.pack(side="top", fill="x")

        ttk.Button(bar, text="Choose Folder\u2026", command=self.choose_folder).pack(side="left")

        self.recursive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Include subfolders", variable=self.recursive_var,
                        command=self.rescan).pack(side="left", padx=(12, 0))

        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=12)

        ttk.Button(bar, text="Save", command=self.save).pack(side="left")
        ttk.Button(bar, text="Save As\u2026", command=self.save_as).pack(side="left", padx=(6, 0))
        ttk.Button(bar, text="Close File", command=self.close_file).pack(side="left", padx=(6, 0))

        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=12)

        ttk.Button(bar, text="Find & Replace\u2026", command=self.open_find_dialog).pack(side="left")
        ttk.Button(bar, text="Go to Line\u2026", command=self.go_to_line).pack(side="left", padx=(6, 0))

    def _build_body(self) -> None:
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        # ---- left pane: the file list ---- #
        left = ttk.Frame(paned, padding=(0, 0, 6, 0))
        self.folder_label = ttk.Label(left, text="No folder selected", anchor="w",
                                      foreground="#6b7280")
        self.folder_label.pack(fill="x", pady=(0, 4))

        actions = ttk.Frame(left)
        actions.pack(fill="x", pady=(0, 6))
        ttk.Button(actions, text="New File", command=self.new_file).pack(side="left")
        ttk.Button(actions, text="Open File\u2026", command=self.open_any_file).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Rescan", command=self.rescan).pack(side="left", padx=(6, 0))

        filter_row = ttk.Frame(left)
        filter_row.pack(fill="x", pady=(0, 6))
        ttk.Label(filter_row, text="Showing:").pack(side="left")
        self.filter_var = tk.StringVar(value=FILTER_TEXT_AND_CODE)
        self.filter_box = ttk.Combobox(filter_row, textvariable=self.filter_var,
                                       values=FILTER_CHOICES, state="readonly",
                                       width=16)
        self.filter_box.pack(side="left", padx=(6, 0), fill="x", expand=True)
        self.filter_box.bind("<<ComboboxSelected>>", lambda e: self.rescan())

        list_wrap = ttk.Frame(left)
        list_wrap.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(list_wrap, columns=("name", "close"),
                                 show="headings", selectmode="browse")
        self.tree.heading("name", text="File", anchor="w")
        self.tree.heading("close", text="", anchor="center")
        self.tree.column("name", anchor="w", width=250, minwidth=120, stretch=True)
        self.tree.column("close", anchor="center", width=32, minwidth=32, stretch=False)
        self.tree.tag_configure("current", background=ROW_CURRENT_BG, font=self.bold_font)

        scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.count_label = ttk.Label(left, text="", anchor="w", foreground="#6b7280")
        self.count_label.pack(fill="x", pady=(4, 0))
        ttk.Label(left, text="\u00d7 closes a file \u00b7 double-click opens",
                  anchor="w", foreground="#9ca3af").pack(fill="x")
        paned.add(left, weight=1)

        # ---- right pane: the editor ---- #
        right = ttk.Frame(paned)
        right.rowconfigure(0, weight=1)
        right.columnconfigure(1, weight=1)

        self.gutter = tk.Canvas(right, width=56, background=GUTTER_BG,
                                highlightthickness=0, borderwidth=0)
        self.gutter.grid(row=0, column=0, sticky="ns")

        self.text = tk.Text(
            right, wrap="none", undo=True, maxundo=-1, autoseparators=True,
            font=self.editor_font, background=EDITOR_BG, foreground=EDITOR_FG,
            insertbackground="#111827", selectbackground="#bfdbfe",
            selectforeground="#111827", borderwidth=0, highlightthickness=0,
            padx=10, pady=6, tabs=("4c",),
        )
        self.text.grid(row=0, column=1, sticky="nsew")

        self.vbar = ttk.Scrollbar(right, orient="vertical", command=self.on_vscroll)
        self.vbar.grid(row=0, column=2, sticky="ns")
        self.hbar = ttk.Scrollbar(right, orient="horizontal", command=self.text.xview)
        self.hbar.grid(row=1, column=1, sticky="ew")

        self.text.configure(yscrollcommand=self.on_yscroll, xscrollcommand=self.hbar.set)
        self.text.tag_configure("goto", background=HIGHLIGHT_BG)
        self.text.tag_configure("match", background=MATCH_BG)
        self.text.tag_configure("match_current", background=MATCH_CURRENT_BG)

        paned.add(right, weight=4)

        # ---- events ---- #
        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<Double-Button-1>", self.on_tree_double_click)
        self.tree.bind("<Return>", self.on_list_open)
        self.tree.bind("<Delete>", self.on_list_close_key)
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.tree.bind(seq, self.on_list_wheel)

        self.text.bind("<<Modified>>", self.on_modified)
        self.text.bind("<KeyRelease>", self.update_status)
        self.text.bind("<ButtonRelease-1>", self.update_status)
        self.text.bind("<Configure>", lambda e: self.redraw_gutter())

    def _build_status(self) -> None:
        bar = ttk.Frame(self, padding=(10, 5))
        bar.pack(side="bottom", fill="x")
        self.status_left = ttk.Label(bar, text="No file open", anchor="w", foreground="#374151")
        self.status_left.pack(side="left")
        self.status_right = ttk.Label(bar, text="", anchor="e", foreground="#6b7280")
        self.status_right.pack(side="right")

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New File\u2026", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Open File\u2026", command=self.open_any_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Choose Folder\u2026", command=self.choose_folder,
                              accelerator="Ctrl+Shift+O")
        file_menu.add_command(label="Rescan Folder", command=self.rescan, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self.save, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As\u2026", command=self.save_as, accelerator="Ctrl+Shift+S")
        file_menu.add_command(label="Close File", command=self.close_file, accelerator="Ctrl+W")
        file_menu.add_command(label="Remove From List",
                              command=self.remove_selected_row, accelerator="Delete")
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.on_quit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Find & Replace\u2026", command=self.open_find_dialog,
                              accelerator="Ctrl+F")
        edit_menu.add_command(label="Go to Line\u2026", command=self.go_to_line, accelerator="Ctrl+G")
        edit_menu.add_separator()
        edit_menu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self.redo, accelerator="Ctrl+Y")
        menubar.add_cascade(label="Edit", menu=edit_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.configure(menu=menubar)

    def _bind_keys(self) -> None:
        for mod in ("Control", "Command"):
            self.bind(f"<{mod}-s>", self._event(self.save))
            self.bind(f"<{mod}-Shift-S>", self._event(self.save_as))
            self.bind(f"<{mod}-Shift-s>", self._event(self.save_as))
            self.bind(f"<{mod}-w>", self._event(self.close_file))
            self.bind(f"<{mod}-f>", self._event(self.open_find_dialog))
            self.bind(f"<{mod}-g>", self._event(self.go_to_line))
            self.bind(f"<{mod}-n>", self._event(self.new_file))
            self.bind(f"<{mod}-o>", self._event(self.open_any_file))
            self.bind(f"<{mod}-Shift-O>", self._event(self.choose_folder))
            self.bind(f"<{mod}-Shift-o>", self._event(self.choose_folder))
            self.bind(f"<{mod}-q>", self._event(self.on_quit))
        self.bind("<F5>", self._event(self.rescan))

    @staticmethod
    def _event(func):
        def handler(event=None):
            func()
            return "break"
        return handler

    # -- scrolling / gutter ----------------------------------------------- #
    def on_yscroll(self, first: str, last: str) -> None:
        self.vbar.set(first, last)
        self.redraw_gutter()

    def on_vscroll(self, *args) -> None:
        self.text.yview(*args)
        self.redraw_gutter()

    def redraw_gutter(self) -> None:
        self.gutter.delete("all")
        if not self.current_path:
            return
        cursor_line = self.text.index("insert").split(".")[0]
        index = self.text.index("@0,0")
        while True:
            info = self.text.dlineinfo(index)
            if info is None:
                break
            y = info[1]
            number = index.split(".")[0]
            self.gutter.create_text(
                46, y, anchor="ne", text=number, font=self.editor_font,
                fill=GUTTER_FG_CURRENT if number == cursor_line else GUTTER_FG,
            )
            nxt = self.text.index(f"{index}+1line")
            if nxt == index:
                break
            index = nxt

    # -- folder / file list ------------------------------------------------ #
    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="Choose a folder to scan for text and code files",
                                         initialdir=self.folder or os.getcwd())
        if folder:
            self.load_folder(folder)

    def filter_spec(self) -> dict:
        """Scan arguments for whatever the Showing box is set to."""
        choice = self.filter_var.get()
        if choice == FILTER_ALL_FILES:
            return {"extensions": CODE_EXTENSIONS, "all_files": True, "named": ()}
        if choice == FILTER_TEXT_ONLY:
            return {"extensions": TEXT_EXTENSIONS, "all_files": False, "named": ()}
        return {"extensions": CODE_EXTENSIONS, "all_files": False, "named": CODE_FILENAMES}

    def load_folder(self, folder: str) -> None:
        self.folder = os.path.abspath(folder)
        self.rescan()

    def rescan(self) -> None:
        if not self.folder:
            return
        scanned = [os.path.join(self.folder, rel)
                   for rel in scan_files(self.folder, self.recursive_var.get(),
                                         **self.filter_spec())]
        self.entries = merge_entries(scanned, self.external, self.folder)
        self.external = [p for p in self.external if os.path.isfile(p)]
        self.refresh_list()

        shown = os.path.basename(self.folder.rstrip(os.sep)) or self.folder
        self.folder_label.configure(text=f"{shown}  \u2014  {self.folder}")
        if self.current_path:
            self.select_current_in_list()

    def refresh_list(self) -> None:
        """Rebuild the left pane from self.entries."""
        self.tree.delete(*self.tree.get_children())
        self._iid_path.clear()
        for path in self.entries:
            iid = self.tree.insert(
                "", "end", values=(display_label(path, self.folder), CLOSE_GLYPH))
            self._iid_path[iid] = path
        self.retag_rows()
        scope = "including subfolders" if self.recursive_var.get() else "top level only"
        self.count_label.configure(
            text=f"{len(self.entries)} file(s) \u00b7 {self.filter_var.get().lower()} "
                 f"\u00b7 {scope}")

    def retag_rows(self) -> None:
        for iid, path in self._iid_path.items():
            self.tree.item(iid, tags=("current",) if path == self.current_path else ())

    def path_for_row(self, iid: str | None) -> str | None:
        if not iid:
            return None
        return self._iid_path.get(iid)

    def selected_row_path(self) -> str | None:
        selection = self.tree.selection()
        if not selection:
            return None
        return self.path_for_row(selection[0])

    def select_current_in_list(self) -> None:
        for iid, path in self._iid_path.items():
            if path == self.current_path:
                self.tree.selection_set(iid)
                self.tree.focus(iid)
                self.tree.see(iid)
                return

    # -- left pane clicks -------------------------------------------------- #
    def on_tree_click(self, event=None) -> str | None:
        """A click on the "x" column closes that row; elsewhere selects."""
        if event is None:
            return None
        region = self.tree.identify_region(event.x, event.y)
        row = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if region == "cell" and row and column == "#2":
            self.close_entry(self.path_for_row(row))
            return "break"
        return None

    def on_tree_double_click(self, event=None) -> str | None:
        if event is not None and self.tree.identify_column(event.x) == "#2":
            return "break"          # the x column is single-click only
        self.on_list_open()
        return "break"

    def on_list_open(self, event=None) -> None:
        path = self.selected_row_path()
        if path:
            self.open_file(path)

    def on_list_close_key(self, event=None) -> str:
        self.remove_selected_row()
        return "break"

    def on_list_wheel(self, event=None) -> str:
        if event is None:
            return "break"
        num = getattr(event, "num", None)
        if num == 4:
            self.tree.yview_scroll(-1, "units")
        elif num == 5:
            self.tree.yview_scroll(1, "units")
        else:
            delta = getattr(event, "delta", 0) or 0
            if delta:
                self.tree.yview_scroll(-1 if delta > 0 else 1, "units")
        return "break"

    def remove_selected_row(self) -> None:
        path = self.selected_row_path()
        if path:
            self.close_entry(path)

    def close_entry(self, path: str | None) -> None:
        """Drop a file from the left pane. The file on disk is never touched."""
        if not path:
            return
        if path == self.current_path:
            if not self.confirm_discard():
                return
            self.unload_editor()
        self.entries = [p for p in self.entries if p != path]
        self.external = [p for p in self.external if p != path]
        self.refresh_list()
        self.flash_status(
            f"Removed {os.path.basename(path)} from the list "
            f"\u2014 the file on disk is untouched. Press F5 to bring it back.")

    # -- new / open files -------------------------------------------------- #
    def new_file(self) -> None:
        if not self.folder:
            messagebox.showinfo(
                "Choose a folder first",
                "Pick a folder with \u201cChoose Folder\u2026\u201d so the new file "
                "has somewhere to live and can show up in the list.",
                parent=self)
            return
        name = simpledialog.askstring("New file", "File name:", parent=self,
                                      initialvalue="untitled.txt")
        if name is None:
            return
        name = name.strip()
        if not name:
            return
        if not os.path.splitext(name)[1]:
            name += DEFAULT_SUFFIX
        if name in (".", "..") or os.sep in name or (os.altsep and os.altsep in name):
            messagebox.showerror("Bad file name",
                                 "Use a plain file name, without folders in it.",
                                 parent=self)
            return

        path = os.path.join(self.folder, name)
        try:
            with open(path, "x", encoding="utf-8", newline=""):
                pass
        except FileExistsError:
            messagebox.showerror(
                "Already exists",
                f"\u201c{name}\u201d already exists in this folder.\n"
                "Pick another name, or double-click the existing file to open it.",
                parent=self)
            return
        except OSError as exc:
            messagebox.showerror("Cannot create file", f"{path}\n\n{exc}", parent=self)
            return

        self.rescan()
        self.open_file(path)
        self.select_current_in_list()
        self.flash_status(f"Created {name}")

    def open_any_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Open file", parent=self,
            initialdir=self.folder or os.getcwd(),
            filetypes=[(FILTER_TEXT_AND_CODE, file_patterns(CODE_EXTENSIONS)),
                       (FILTER_TEXT_ONLY, file_patterns(TEXT_EXTENSIONS)),
                       ("All files", "*.*")])
        if not path:
            return
        path = os.path.abspath(path)
        if path not in self.entries:
            if not (self.folder and is_inside(path, self.folder)):
                self.external.append(path)
            self.rescan()
            if path not in self.entries:      # e.g. a type the filter hides
                self.entries.append(path)
                self.refresh_list()
        self.open_file(path)
        self.select_current_in_list()

    # -- open / save / close ---------------------------------------------- #
    def open_file(self, path: str) -> None:
        path = os.path.abspath(path)
        if self.current_path and path == self.current_path and not self.dirty:
            return
        if not self.confirm_discard():
            return
        try:
            text, encoding, newline = read_text_file(path)
        except OSError as exc:
            messagebox.showerror("Cannot open file", f"{path}\n\n{exc}", parent=self)
            return

        self.set_editor_enabled(True)
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)
        self.text.mark_set("insert", "1.0")
        self.text.edit_reset()
        self.text.edit_modified(False)
        self.text.tag_remove("goto", "1.0", "end")
        self.clear_highlights()

        self.current_path = path
        self.encoding = encoding
        self.newline = newline
        self.dirty = False
        self.update_title()
        self.update_status()
        self.redraw_gutter()
        self.retag_rows()
        self.select_current_in_list()
        self.text.focus_set()
        if self._find_dialog is not None:
            self._find_dialog.apply_highlights()

    def save(self) -> bool:
        if not self.current_path:
            return self.save_as()
        content = self.text.get("1.0", "end-1c")
        try:
            write_text_file(self.current_path, content, self.encoding, self.newline)
        except OSError as exc:
            messagebox.showerror("Cannot save file",
                                 f"{self.current_path}\n\n{exc}", parent=self)
            return False
        self.text.edit_modified(False)
        self.dirty = False
        self.update_title()
        self.update_status()
        self.flash_status(f"Saved {os.path.basename(self.current_path)}")
        return True

    def save_as(self) -> bool:
        if not self.current_path:
            return False
        initial_dir = self.folder or os.path.dirname(self.current_path)
        path = filedialog.asksaveasfilename(
            title="Save file as", parent=self, initialdir=initial_dir,
            initialfile=os.path.basename(self.current_path),
            defaultextension=os.path.splitext(self.current_path)[1] or DEFAULT_SUFFIX,
            filetypes=[(FILTER_TEXT_AND_CODE, file_patterns(CODE_EXTENSIONS)),
                       ("All files", "*.*")],
        )
        if not path:
            return False
        content = self.text.get("1.0", "end-1c")
        try:
            write_text_file(path, content, self.encoding, self.newline)
        except OSError as exc:
            messagebox.showerror("Cannot save file", f"{path}\n\n{exc}", parent=self)
            return False
        self.current_path = os.path.abspath(path)
        self.text.edit_modified(False)
        self.dirty = False
        self.update_title()
        self.update_status()
        self.rescan()
        self.flash_status(f"Saved {os.path.basename(self.current_path)}")
        return True

    def close_file(self) -> None:
        """Unload the open file, leaving its row in the left pane."""
        if not self.current_path:
            return
        if not self.confirm_discard():
            return
        name = os.path.basename(self.current_path)
        self.unload_editor()
        self.flash_status(f"Closed {name}")

    def unload_editor(self) -> None:
        self.text.delete("1.0", "end")
        self.text.edit_reset()
        self.text.edit_modified(False)
        self.text.tag_remove("goto", "1.0", "end")
        self.clear_highlights()
        self.current_path = None
        self.dirty = False
        self.set_editor_enabled(False)
        self.update_title()
        self.update_status()
        self.gutter.delete("all")
        self.retag_rows()

    def confirm_discard(self) -> bool:
        """True if it is OK to drop the buffer (saving first if asked)."""
        if not self.dirty or not self.current_path:
            return True
        answer = messagebox.askyesnocancel(
            "Unsaved changes",
            f"Save changes to \u201c{os.path.basename(self.current_path)}\u201d first?",
            parent=self,
        )
        if answer is None:      # cancel
            return False
        if answer:              # yes -> save, and only proceed if it worked
            return self.save()
        return True             # no -> discard

    def set_editor_enabled(self, enabled: bool) -> None:
        self.text.configure(state="normal" if enabled else "disabled")
        if not enabled:
            self.text.delete("1.0", "end")

    def on_modified(self, event=None) -> None:
        if self.text.edit_modified():
            if self.current_path and not self.dirty:
                self.dirty = True
                self.update_title()
                self.update_status()
            self.text.edit_modified(False)
            self.redraw_gutter()
            if self._find_dialog is not None:
                self._find_dialog.schedule_highlight()

    # -- go to line -------------------------------------------------------- #
    def go_to_line(self) -> None:
        if not self.current_path:
            self.flash_status("Open a file first.")
            return
        total = max(1, int(self.text.index("end-1c").split(".")[0]))
        current = int(self.text.index("insert").split(".")[0])
        number = simpledialog.askinteger(
            "Go to line", f"Line number (1\u2013{total}):", parent=self,
            minvalue=1, maxvalue=total, initialvalue=current,
        )
        if number is None:
            return
        self.jump_to_line(number)

    def jump_to_line(self, number: int) -> None:
        total = max(1, int(self.text.index("end-1c").split(".")[0]))
        number = max(1, min(int(number), total))
        index = f"{number}.0"
        self.text.mark_set("insert", index)
        self.text.see(index)
        self.text.tag_remove("goto", "1.0", "end")
        self.text.tag_add("goto", index, f"{number}.end")
        self.after(1500, lambda: self.text.tag_remove("goto", "1.0", "end"))
        self.text.focus_set()
        self.update_status()

    # -- find & replace ---------------------------------------------------- #
    def open_find_dialog(self) -> None:
        """Open the Find & Replace popup, or raise it if it is already up."""
        if self._find_dialog is not None:
            try:
                if self._find_dialog.winfo_exists():
                    self._find_dialog.show_on_screen()
                    self._find_dialog.find_entry.focus_set()
                    return
            except tk.TclError:
                pass
            self._find_dialog = None
        try:
            self._find_dialog = FindReplaceDialog(self)
        except Exception as exc:            # never fail silently
            self._find_dialog = None
            messagebox.showerror(
                "Cannot open Find & Replace",
                f"{type(exc).__name__}: {exc}",
                parent=self)

    def selected_text(self) -> str:
        if not self.text.tag_ranges("sel"):
            return ""
        return self.text.get("sel.first", "sel.last")

    def highlight_matches(self, content: str, matches) -> int:
        """Paint every match in *matches* yellow; return how many were painted."""
        self.clear_highlights()
        painted = 0
        for match in matches:
            start, end = match.start(), match.end()
            if end <= start:        # zero-width regex match: nothing to colour
                continue
            self.text.tag_add("match",
                              offset_to_index(content, start),
                              offset_to_index(content, end))
            painted += 1
        return painted

    def highlight_all(self, needle: str, case: bool = False, whole: bool = False,
                      regex: bool = False) -> int:
        """Yellow-highlight every occurrence of *needle* in the open file."""
        pattern = compile_pattern(needle, case, whole, regex)
        if pattern is None:
            self.clear_highlights()
            return 0
        content = self.text.get("1.0", "end-1c")
        return self.highlight_matches(content, pattern.finditer(content))

    def clear_highlights(self) -> None:
        self.text.tag_remove("match", "1.0", "end")
        self.text.tag_remove("match_current", "1.0", "end")

    def find_next(self, needle: str, case: bool = False, whole: bool = False,
                  regex: bool = False) -> dict | None:
        if not self.current_path:
            return None
        pattern = compile_pattern(needle, case, whole, regex)
        if pattern is None:
            self.clear_highlights()
            return None
        content = self.text.get("1.0", "end-1c")
        matches = list(pattern.finditer(content))
        starts = [m.start() for m in matches]
        self.highlight_matches(content, matches)
        if not starts:
            return {"count": 0, "wrapped": False}

        if self.text.tag_ranges("sel"):
            start = index_to_offset(content, self.text.index("sel.last"))
        else:
            start = index_to_offset(content, self.text.index("insert"))

        wrapped = False
        position = next((s for s in starts if s >= start), None)
        if position is None:
            position = starts[0]
            wrapped = True

        match = pattern.match(content, position)
        end = match.end() if match else position + len(needle)
        self.select_offsets(content, position, end)
        return {"count": len(starts), "wrapped": wrapped}

    def replace_current(self, needle: str, replacement: str, case: bool = False,
                        whole: bool = False, regex: bool = False) -> str:
        if not self.current_path:
            return "No file is open."
        pattern = compile_pattern(needle, case, whole, regex)
        if pattern is None:
            return "Type something to find."

        if self.text.tag_ranges("sel"):
            selected = self.text.get("sel.first", "sel.last")
            match = pattern.fullmatch(selected)
            if match:
                try:
                    new_text = match.expand(replacement) if regex else replacement
                except re.error as exc:
                    return f"Bad replacement: {exc}"
                start_index = self.text.index("sel.first")
                self.text.delete("sel.first", "sel.last")
                self.text.insert(start_index, new_text)
                self.text.mark_set("insert", f"{start_index}+{len(new_text)}c")
                self.text.tag_remove("sel", "1.0", "end")
                result = self.find_next(needle, case, whole, regex)
                if result and result["count"]:
                    return "Replaced 1 occurrence."
                return "Replaced 1 occurrence. No further matches."

        result = self.find_next(needle, case, whole, regex)
        if result is None:
            return "No file is open."
        if result["count"] == 0:
            return f"No match for \u201c{needle}\u201d."
        return "Moved to next match \u2014 press Replace again."

    def replace_all(self, needle: str, replacement: str, case: bool = False,
                    whole: bool = False, regex: bool = False) -> str:
        if not self.current_path:
            return "No file is open."
        pattern = compile_pattern(needle, case, whole, regex)
        if pattern is None:
            return "Type something to find."
        content = self.text.get("1.0", "end-1c")

        try:
            if regex:
                new_content, count = pattern.subn(lambda m: m.expand(replacement), content)
            else:
                new_content, count = pattern.subn(lambda m: replacement, content)
        except re.error as exc:
            return f"Bad replacement: {exc}"

        if not count:
            return f"No match for \u201c{needle}\u201d."
        if new_content == content:
            return f"{count} match(es) found, nothing changed."

        insert_at = self.text.index("insert")
        self.text.edit_separator()
        self.text.delete("1.0", "end")
        self.text.insert("1.0", new_content)
        self.text.mark_set("insert", insert_at)
        self.text.edit_separator()
        self.redraw_gutter()
        self.highlight_all(needle, case, whole, regex)
        return f"Replaced {count} occurrence(s)."

    def select_offsets(self, content: str, start: int, end: int) -> None:
        start_index = offset_to_index(content, start)
        end_index = offset_to_index(content, end)
        self.text.tag_remove("sel", "1.0", "end")
        self.text.tag_add("sel", start_index, end_index)
        self.text.tag_remove("match_current", "1.0", "end")
        self.text.tag_add("match_current", start_index, end_index)
        self.text.mark_set("insert", end_index)
        self.text.see(start_index)
        self.update_status()

    # -- misc -------------------------------------------------------------- #
    def undo(self) -> None:
        try:
            self.text.edit_undo()
        except tk.TclError:
            pass

    def redo(self) -> None:
        try:
            self.text.edit_redo()
        except tk.TclError:
            pass

    def update_title(self) -> None:
        if self.current_path:
            name = os.path.basename(self.current_path)
            marker = "\u2022 " if self.dirty else ""
            self.title(f"{marker}{name} \u2014 {APP_NAME}")
        else:
            self.title(APP_NAME)

    def update_status(self, event=None) -> None:
        if self.current_path:
            line, col = self.text.index("insert").split(".")
            self.status_left.configure(text=self.current_path)
            self.status_right.configure(
                text=f"Ln {line}, Col {int(col) + 1}   |   {self.encoding}   |   "
                     f"{'modified' if self.dirty else 'saved'}")
        else:
            self.status_left.configure(text="No file open")
            self.status_right.configure(text="")
        self.redraw_gutter()

    def flash_status(self, message: str, ms: int = 4000) -> None:
        self.status_left.configure(text=message)
        self.after(ms, self.update_status)

    def show_about(self) -> None:
        messagebox.showinfo(
            "About",
            f"{APP_NAME}\n\nA tiny text and code browser and editor built with tkinter.\n"
            "Pick a folder, double-click a file, edit, then Save / Close.\n"
            "The \u00d7 on a row removes it from the list \u2014 never from the disk.",
            parent=self,
        )

    def on_quit(self) -> None:
        if not self.confirm_discard():
            return
        self.destroy()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Browse and edit text and code files in a folder.")
    parser.add_argument("folder", nargs="?", help="folder to scan on startup")
    args = parser.parse_args(argv)

    folder = args.folder
    if folder and not os.path.isdir(folder):
        print(f"Not a directory: {folder}", file=sys.stderr)
        return 2

    app = TxtStudio(folder)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
