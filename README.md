This is a Python Text Editor.

It can browse to a given directory and map all the .txt files.

These files are displayed in left pane.

A file selected in open for reading and editing in right pane.

These are options to Add a new file, Find and Replace Text, Save File, close File and Close All Files.

You can add to these extensions in the program.

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
