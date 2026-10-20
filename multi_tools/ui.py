"""Interfaz gráfica de Multi Tools (Tkinter)."""

from __future__ import annotations

import os
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageGrab, ImageTk

from . import microphone, ocr, settings, transcribe
from .config import APP_NAME, APP_VERSION, ICON_PATH

BG = "#f2f5fb"
CARD = "#ffffff"
BORDER = "#d9e1ef"
TEXT = "#1c2536"
MUTED = "#67748b"
ACCENT = "#2f6fed"
ACCENT_DARK = "#2358c7"
SOFT = "#e8eefb"

IMAGE_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".jfif",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp",
    ".avif",
    ".heic",
    ".heif",
    ".ico",
)

MEDIA_EXTENSIONS = (
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".ogg",
    ".oga",
    ".opus",
    ".flac",
    ".wma",
    ".aiff",
    ".aif",
    ".amr",
    ".caf",
    ".mka",
    ".mp4",
    ".mkv",
    ".mov",
    ".avi",
    ".webm",
    ".m4v",
    ".wmv",
    ".flv",
    ".mpeg",
    ".mpg",
    ".ogv",
    ".3gp",
    ".3g2",
    ".mts",
    ".m2ts",
    ".ts",
    ".asf",
    ".vob",
)

SORT_OPTIONS = (
    "Más recientes primero",
    "Más antiguos primero",
    "Nombre A–Z",
    "Nombre Z–A",
    "Tamaño mayor primero",
    "Tamaño menor primero",
)


class RegionSelector(tk.Toplevel):
    """Pantalla completa para dibujar el área que se quiere capturar."""

    def __init__(self, master: tk.Misc, screenshot: Image.Image, on_done) -> None:
        super().__init__(master)
        self.on_done = on_done
        self.screenshot = screenshot
        self._start: tuple[int, int] | None = None
        self._rect: int | None = None
        self._pending_box: tuple[int, int, int, int] | None = None
        self._confirm_panel: tk.Frame | None = None
        self._done = False

        width = self.winfo_screenwidth()
        height = self.winfo_screenheight()

        self.overrideredirect(True)
        self.geometry(f"{width}x{height}+0+0")
        self.attributes("-topmost", True)
        self.configure(bg="#000000")

        self.canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            highlightthickness=0,
            bd=0,
            cursor="crosshair",
        )
        self.canvas.pack(fill="both", expand=True)

        display = screenshot
        if screenshot.size != (width, height):
            display = screenshot.resize((width, height), Image.LANCZOS)

        self._scale_x = screenshot.width / width
        self._scale_y = screenshot.height / height
        self._photo = ImageTk.PhotoImage(display)
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo)

        self.canvas.create_rectangle(0, 0, width, 54, fill="#0b1220", outline="")
        self.canvas.create_text(
            width / 2,
            27,
            text="Arrastra para seleccionar el área   ·   Enter confirma   ·   Esc cancela",
            fill="#ffffff",
            font=("DejaVu Sans", 13, "bold"),
        )

        self.bind("<Escape>", lambda _event: self._cancel())
        self.bind("<Return>", lambda _event: self._confirm_selection())
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.after(60, self._activate)

    def _activate(self) -> None:
        try:
            self.focus_force()
            self.canvas.focus_set()
            self.grab_set()
        except tk.TclError:
            pass

    def _on_press(self, event) -> None:
        self._hide_confirmation()
        self._pending_box = None
        self._start = (event.x, event.y)
        if self._rect is not None:
            self.canvas.delete(self._rect)
        self._rect = self.canvas.create_rectangle(
            event.x, event.y, event.x, event.y, outline="#5b91ff", width=2
        )

    def _on_drag(self, event) -> None:
        if self._start is None or self._rect is None:
            return
        x1, y1 = self._start
        self.canvas.coords(self._rect, x1, y1, event.x, event.y)

    def _on_release(self, event) -> None:
        if self._start is None:
            return
        x1, y1 = self._start
        x2, y2 = event.x, event.y
        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))

        if right - left < 8 or bottom - top < 8:
            self._reset_selection()
            return

        box = (
            max(0, int(left * self._scale_x)),
            max(0, int(top * self._scale_y)),
            min(self.screenshot.width, int(right * self._scale_x)),
            min(self.screenshot.height, int(bottom * self._scale_y)),
        )
        self._pending_box = box
        self._show_confirmation(right - left, bottom - top)

    def _show_confirmation(self, width: int, height: int) -> None:
        self._hide_confirmation()

        panel = tk.Frame(self, bg="#0b1220", padx=14, pady=10)
        panel.place(relx=0.5, rely=1.0, anchor="s", y=-36)

        tk.Label(
            panel,
            text=f"Área seleccionada: {width} × {height} px",
            bg="#0b1220",
            fg="#ffffff",
            font=("DejaVu Sans", 10, "bold"),
        ).pack(side="left", padx=(0, 16))

        ttk.Button(
            panel,
            text="Repetir",
            style="Secondary.TButton",
            command=self._reset_selection,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            panel,
            text="Confirmar",
            style="Accent.TButton",
            command=self._confirm_selection,
        ).pack(side="left")

        self._confirm_panel = panel

    def _hide_confirmation(self) -> None:
        if self._confirm_panel is not None:
            self._confirm_panel.destroy()
            self._confirm_panel = None

    def _reset_selection(self) -> None:
        self._hide_confirmation()
        self._pending_box = None
        self._start = None
        if self._rect is not None:
            self.canvas.delete(self._rect)
            self._rect = None

    def _confirm_selection(self) -> None:
        if self._pending_box is None or self._done:
            return
        box = self._pending_box
        self._pending_box = None
        self._finish(box)

    def _cancel(self) -> None:
        self._complete(None)

    def _finish(self, box) -> None:
        self._complete(box)

    def _complete(self, box) -> None:
        if self._done:
            return
        self._done = True
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
        self.on_done(box)


class TranscribeDialog(tk.Toplevel):
    """Diálogo compacto para elegir modelo e idioma antes de transcribir."""

    def __init__(self, master: tk.Misc, path: str, model: str, language: str, on_start) -> None:
        super().__init__(master)
        self.on_start = on_start
        self.path = path

        self.title("Transcribir audio / video")
        self.geometry("430x285")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.transient(master)

        model_var = tk.StringVar(value=model)
        language_var = tk.StringVar(value=language)

        box = tk.Frame(
            self,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        box.pack(fill="both", expand=True, padx=14, pady=14)
        box.columnconfigure(1, weight=1)

        tk.Label(
            box,
            text="Archivo seleccionado",
            bg=CARD,
            fg=MUTED,
            font=("DejaVu Sans", 9),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 2))
        tk.Label(
            box,
            text=Path(path).name,
            bg=CARD,
            fg=TEXT,
            font=("DejaVu Sans", 10, "bold"),
            anchor="w",
            justify="left",
            wraplength=370,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12))

        ttk.Label(box, text="Modelo", style="Card.TLabel").grid(
            row=2, column=0, sticky="w", padx=(14, 8), pady=4
        )
        ttk.Combobox(
            box,
            textvariable=model_var,
            values=transcribe.MODEL_SIZES,
            state="readonly",
        ).grid(row=2, column=1, sticky="ew", padx=(0, 14), pady=4)

        ttk.Label(box, text="Idioma", style="Card.TLabel").grid(
            row=3, column=0, sticky="w", padx=(14, 8), pady=4
        )
        ttk.Combobox(
            box,
            textvariable=language_var,
            values=list(transcribe.LANGUAGES),
            state="readonly",
        ).grid(row=3, column=1, sticky="ew", padx=(0, 14), pady=4)

        ttk.Label(
            box,
            text=(
                "«Automático» detecta el idioma solo. «base» es el más rápido; "
                "«small» mejora la precisión. La primera vez se descarga el modelo."
            ),
            style="Muted.TLabel",
            wraplength=355,
            justify="left",
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=14, pady=(8, 0))

        buttons = ttk.Frame(box, style="Card.TFrame")
        buttons.grid(row=5, column=0, columnspan=2, sticky="e", padx=14, pady=(12, 14))

        ttk.Button(
            buttons,
            text="Cancelar",
            style="Ghost.TButton",
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            buttons,
            text="Transcribir",
            style="Accent.TButton",
            command=lambda: self._start(model_var.get(), language_var.get()),
        ).pack(side="left")

        self.bind("<Escape>", lambda _event: self.destroy())
        self.after(60, self._activate)

    def _activate(self) -> None:
        try:
            self.focus_force()
            self.grab_set()
        except tk.TclError:
            pass

    def _start(self, model: str, language: str) -> None:
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
        self.on_start(model, language)


class FilePickerDialog(tk.Toplevel):
    """Selector de archivos con búsqueda, orden y navegación de carpetas."""

    def __init__(
        self,
        master: tk.Misc,
        title: str,
        extensions: tuple[str, ...],
        initialdir: str,
        on_select,
    ) -> None:
        super().__init__(master)
        self.on_select = on_select
        self.extensions = {extension.lower() for extension in extensions}
        self._search_after_id: str | None = None
        self._selected_path: Path | None = None
        self._done = False
        self._current_dir = self._valid_directory(initialdir)

        self.title(title)
        self.geometry("860x580")
        self.minsize(660, 420)
        self.configure(bg=BG)
        self.transient(master)

        self.path_var = tk.StringVar(value=str(self._current_dir))
        self.search_var = tk.StringVar()
        self.sort_var = tk.StringVar(value=SORT_OPTIONS[0])
        self.recursive_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar()

        self._build_ui()
        self.search_var.trace_add("write", self._queue_refresh)
        self.bind("<Escape>", lambda _event: self._cancel())
        self.bind("<Control-f>", lambda _event: self.search_entry.focus_set())
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self._refresh()
        self.after(60, self._activate)

    def _valid_directory(self, value: str) -> Path:
        try:
            path = Path(value).expanduser().resolve()
            if path.is_dir():
                return path
        except OSError:
            pass
        return Path.home()

    def _build_ui(self) -> None:
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True, padx=14, pady=12)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(3, weight=1)

        nav = tk.Frame(outer, bg=BG)
        nav.grid(row=0, column=0, sticky="ew")

        ttk.Button(
            nav, text="Subir", style="Picker.TButton", command=self._go_up
        ).pack(side="left")
        ttk.Button(
            nav,
            text="Descargas",
            style="Picker.TButton",
            command=lambda: self._navigate(settings.downloads_directory()),
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            nav,
            text="Inicio",
            style="Picker.TButton",
            command=lambda: self._navigate(Path.home()),
        ).pack(side="left", padx=(6, 0))

        self.path_entry = ttk.Entry(nav, textvariable=self.path_var)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(8, 6))
        self.path_entry.bind("<Return>", lambda _event: self._go_path())

        ttk.Button(
            nav, text="Ir", style="Picker.TButton", command=self._go_path
        ).pack(side="left")

        tools = tk.Frame(outer, bg=BG)
        tools.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        tools.columnconfigure(1, weight=1)

        ttk.Label(tools, text="Buscar").grid(row=0, column=0, padx=(0, 6))
        self.search_entry = ttk.Entry(tools, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky="ew")

        ttk.Checkbutton(
            tools,
            text="Subcarpetas",
            variable=self.recursive_var,
            command=self._refresh,
        ).grid(row=0, column=2, padx=(10, 12))

        ttk.Label(tools, text="Ordenar").grid(row=0, column=3, padx=(0, 6))
        sort_box = ttk.Combobox(
            tools,
            textvariable=self.sort_var,
            values=SORT_OPTIONS,
            state="readonly",
            width=23,
        )
        sort_box.grid(row=0, column=4)
        sort_box.bind("<<ComboboxSelected>>", lambda _event: self._refresh())

        tree_frame = tk.Frame(
            outer,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        tree_frame.grid(row=3, column=0, sticky="nsew", pady=(10, 0))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("name", "modified", "size", "type"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("name", text="Nombre")
        self.tree.heading("modified", text="Modificado")
        self.tree.heading("size", text="Tamaño")
        self.tree.heading("type", text="Tipo")
        self.tree.column("name", width=440, minwidth=220, anchor="w", stretch=True)
        self.tree.column("modified", width=140, minwidth=120, anchor="w", stretch=False)
        self.tree.column("size", width=90, minwidth=70, anchor="e", stretch=False)
        self.tree.column("type", width=80, minwidth=60, anchor="w", stretch=False)

        scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-1>", self._on_activate)
        self.tree.bind("<Return>", self._on_activate)
        self.tree.bind("<<TreeviewSelect>>", self._on_selection)

        footer = tk.Frame(outer, bg=BG)
        footer.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)

        ttk.Label(footer, textvariable=self.status_var).grid(
            row=0, column=0, sticky="w"
        )

        self.select_btn = ttk.Button(
            footer,
            text="Seleccionar",
            style="Accent.TButton",
            command=self._accept,
            state="disabled",
        )
        self.select_btn.grid(row=0, column=1, padx=(8, 0))

        ttk.Button(
            footer, text="Cancelar", style="Secondary.TButton", command=self._cancel
        ).grid(row=0, column=2, padx=(8, 0))

    def _activate(self) -> None:
        try:
            self.lift()
            self.focus_force()
            self.grab_set()
            self.tree.focus_set()
        except tk.TclError:
            pass

    def _queue_refresh(self, *_args) -> None:
        if self._search_after_id is not None:
            try:
                self.after_cancel(self._search_after_id)
            except tk.TclError:
                pass
        self._search_after_id = self.after(180, self._refresh)

    def _refresh(self) -> None:
        if not self.winfo_exists():
            return
        self._search_after_id = None
        self.tree.delete(*self.tree.get_children())
        self._selected_path = None
        self.select_btn.state(["disabled"])

        query = self.search_var.get().strip().lower()
        recursive = bool(query) and self.recursive_var.get()

        try:
            if recursive:
                directories: list[tuple[Path, os.stat_result, str]] = []
                files = self._scan_recursive(query)
            else:
                directories, files = self._scan_current(query)
        except OSError as exc:
            self.status_var.set(f"No se pudo leer la carpeta: {exc}")
            return

        self._sort_files(files)

        if self._current_dir.parent != self._current_dir:
            self.tree.insert(
                "", "end", iid="__parent__", values=("..", "", "", "Carpeta")
            )

        for path, stat_result, name in directories:
            self.tree.insert(
                "",
                "end",
                iid=str(path),
                values=(
                    name,
                    self._format_date(stat_result.st_mtime),
                    "",
                    "Carpeta",
                ),
            )

        for path, stat_result, display_name in files:
            file_type = path.suffix.lstrip(".").upper() or "Archivo"
            self.tree.insert(
                "",
                "end",
                iid=str(path),
                values=(
                    display_name,
                    self._format_date(stat_result.st_mtime),
                    self._format_size(stat_result.st_size),
                    file_type,
                ),
            )

        parts = [f"{len(files)} archivos", f"{len(directories)} carpetas"]
        if recursive:
            parts.append("búsqueda en subcarpetas")
        self.status_var.set(" · ".join(parts))

    def _scan_current(
        self, query: str
    ) -> tuple[
        list[tuple[Path, os.stat_result, str]], list[tuple[Path, os.stat_result, str]]
    ]:
        directories: list[tuple[Path, os.stat_result, str]] = []
        files: list[tuple[Path, os.stat_result, str]] = []

        with os.scandir(self._current_dir) as entries:
            for entry in entries:
                name = entry.name
                if name.startswith("."):
                    continue
                if query and query not in name.lower():
                    continue
                try:
                    if entry.is_dir(follow_symlinks=False):
                        stat_result = entry.stat(follow_symlinks=False)
                        directories.append(
                            (Path(entry.path), stat_result, name)
                        )
                    elif (
                        entry.is_file(follow_symlinks=False)
                        and Path(name).suffix.lower() in self.extensions
                    ):
                        stat_result = entry.stat(follow_symlinks=False)
                        files.append((Path(entry.path), stat_result, name))
                except OSError:
                    continue

        directories.sort(key=lambda item: item[2].lower())
        return directories, files

    def _scan_recursive(
        self, query: str
    ) -> list[tuple[Path, os.stat_result, str]]:
        files: list[tuple[Path, os.stat_result, str]] = []
        base = self._current_dir

        for root, dirnames, filenames in os.walk(base):
            dirnames[:] = [
                name for name in dirnames if not name.startswith(".")
            ]
            for filename in filenames:
                if filename.startswith("."):
                    continue
                if Path(filename).suffix.lower() not in self.extensions:
                    continue

                path = Path(root) / filename
                try:
                    relative = str(path.relative_to(base)).lower()
                except ValueError:
                    relative = filename.lower()
                if query not in relative:
                    continue

                try:
                    stat_result = path.stat()
                except OSError:
                    continue

                files.append((path, stat_result, str(path.relative_to(base))))
                if len(files) >= 5000:
                    return files

        return files

    def _sort_files(self, files: list[tuple[Path, os.stat_result, str]]) -> None:
        option = self.sort_var.get()
        if option == "Más recientes primero":
            files.sort(key=lambda item: item[1].st_mtime, reverse=True)
        elif option == "Más antiguos primero":
            files.sort(key=lambda item: item[1].st_mtime)
        elif option == "Nombre A–Z":
            files.sort(key=lambda item: item[2].lower())
        elif option == "Nombre Z–A":
            files.sort(key=lambda item: item[2].lower(), reverse=True)
        elif option == "Tamaño mayor primero":
            files.sort(key=lambda item: item[1].st_size, reverse=True)
        elif option == "Tamaño menor primero":
            files.sort(key=lambda item: item[1].st_size)

    @staticmethod
    def _format_date(timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def _format_size(size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                if unit == "B":
                    return f"{int(value)} B"
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} TB"

    def _navigate(self, path: Path | str) -> None:
        try:
            target = Path(path).expanduser().resolve()
        except OSError:
            target = Path(path)
        if not target.is_dir():
            messagebox.showwarning(
                "Carpeta no válida",
                f"La carpeta no existe:\n\n{target}",
                parent=self,
            )
            self.path_var.set(str(self._current_dir))
            return

        self._current_dir = target
        self.path_var.set(str(target))
        settings.set_last_directory(target)
        self._refresh()

    def _go_up(self) -> None:
        parent = self._current_dir.parent
        if parent != self._current_dir:
            self._navigate(parent)

    def _go_path(self) -> None:
        self._navigate(self.path_var.get().strip())

    def _on_selection(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection or selection[0] == "__parent__":
            self._selected_path = None
            self.select_btn.state(["disabled"])
            return

        path = Path(selection[0])
        if path.is_file():
            self._selected_path = path
            self.select_btn.state(["!disabled"])
        else:
            self._selected_path = None
            self.select_btn.state(["disabled"])

    def _on_activate(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        if item == "__parent__":
            self._go_up()
            return

        path = Path(item)
        if path.is_dir():
            self._navigate(path)
        elif path.is_file():
            self._selected_path = path
            self._accept()

    def _accept(self) -> None:
        if self._selected_path is None or self._done:
            return
        path = self._selected_path
        settings.set_last_directory(path.parent)
        self._finish(str(path))

    def _cancel(self) -> None:
        self._finish(None)

    def _finish(self, result: str | None) -> None:
        if self._done:
            return
        self._done = True
        if self._search_after_id is not None:
            try:
                self.after_cancel(self._search_after_id)
            except tk.TclError:
                pass
            self._search_after_id = None
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
        if result is not None:
            self.on_select(result)


class MicrophoneDialog(tk.Toplevel):
    """Grabadora de micrófono con iniciar, pausar, reanudar y detener."""

    def __init__(
        self,
        master: tk.Misc,
        model: str,
        language: str,
        on_ready,
    ) -> None:
        super().__init__(master)
        self.on_ready = on_ready
        self._recorder: microphone.Recorder | None = None
        self._state = "idle"
        self._tick_id: str | None = None
        self._done = False

        self.model_var = tk.StringVar(value=model)
        self.language_var = tk.StringVar(value=language)
        self.timer_var = tk.StringVar(value="00:00")
        self.status_var = tk.StringVar(value="Pulsa Iniciar grabación y habla.")

        self.title("Grabar con micrófono")
        self.geometry("460x360")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.transient(master)

        self._build_ui()
        self.bind("<Escape>", lambda _event: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.after(60, self._activate)

    def _build_ui(self) -> None:
        box = tk.Frame(
            self,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        box.pack(fill="both", expand=True, padx=14, pady=14)
        box.columnconfigure(0, weight=1)

        tk.Label(
            box,
            text="Grabación de voz",
            bg=CARD,
            fg=TEXT,
            font=("DejaVu Sans", 14, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 0))
        tk.Label(
            box,
            text="Habla con claridad. Puedes pausar y continuar cuando quieras.",
            bg=CARD,
            fg=MUTED,
            font=("DejaVu Sans", 9),
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(2, 8))

        tk.Label(
            box,
            textvariable=self.timer_var,
            bg=CARD,
            fg=TEXT,
            font=("DejaVu Sans", 30, "bold"),
        ).grid(row=2, column=0, pady=(4, 4))

        self.level_canvas = tk.Canvas(
            box,
            height=12,
            bg=SOFT,
            highlightthickness=0,
            bd=0,
        )
        self.level_canvas.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 6))
        self._level_bar = self.level_canvas.create_rectangle(
            0, 0, 0, 12, fill=ACCENT, outline=""
        )

        tk.Label(
            box,
            textvariable=self.status_var,
            bg=CARD,
            fg=MUTED,
            font=("DejaVu Sans", 9),
            anchor="w",
        ).grid(row=4, column=0, sticky="ew", padx=16)

        options = tk.Frame(box, bg=CARD)
        options.grid(row=5, column=0, sticky="ew", padx=16, pady=(12, 0))
        options.columnconfigure(1, weight=1)
        options.columnconfigure(3, weight=1)

        ttk.Label(options, text="Modelo", style="Card.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 6)
        )
        self.model_box = ttk.Combobox(
            options,
            textvariable=self.model_var,
            values=transcribe.MODEL_SIZES,
            state="readonly",
            width=11,
        )
        self.model_box.grid(row=0, column=1, sticky="ew")

        ttk.Label(options, text="Idioma", style="Card.TLabel").grid(
            row=0, column=2, sticky="w", padx=(14, 6)
        )
        self.language_box = ttk.Combobox(
            options,
            textvariable=self.language_var,
            values=list(transcribe.LANGUAGES),
            state="readonly",
            width=12,
        )
        self.language_box.grid(row=0, column=3, sticky="ew")

        self.start_btn = ttk.Button(
            box,
            text="Iniciar grabación",
            style="Accent.TButton",
            command=self._start,
        )
        self.start_btn.grid(row=6, column=0, sticky="ew", padx=16, pady=(14, 0))

        controls = tk.Frame(box, bg=CARD)
        controls.grid(row=7, column=0, sticky="ew", padx=16, pady=(8, 14))
        controls.columnconfigure(2, weight=1)

        self.pause_btn = ttk.Button(
            controls,
            text="Pausar",
            style="Secondary.TButton",
            command=self._toggle_pause,
            state="disabled",
        )
        self.pause_btn.grid(row=0, column=0, padx=(0, 8))

        self.stop_btn = ttk.Button(
            controls,
            text="Detener y transcribir",
            style="Danger.TButton",
            command=self._stop,
            state="disabled",
        )
        self.stop_btn.grid(row=0, column=1)

        ttk.Button(
            controls,
            text="Cancelar",
            style="Secondary.TButton",
            command=self._cancel,
        ).grid(row=0, column=2, sticky="e")

    def _activate(self) -> None:
        try:
            self.lift()
            self.focus_force()
            self.grab_set()
        except tk.TclError:
            pass

    def _start(self) -> None:
        if self._state != "idle":
            return
        recorder = microphone.Recorder()
        try:
            recorder.start()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                "Micrófono no disponible",
                f"No se pudo iniciar la grabación:\n\n{exc}",
                parent=self,
            )
            return

        self._recorder = recorder
        self._state = "recording"
        self.start_btn.state(["disabled"])
        self.pause_btn.state(["!disabled"])
        self.stop_btn.state(["!disabled"])
        self.model_box.state(["disabled"])
        self.language_box.state(["disabled"])
        self.status_var.set("Grabando…")
        self._tick()

    def _toggle_pause(self) -> None:
        if self._recorder is None:
            return

        if self._state == "recording":
            self._recorder.pause()
            self._state = "paused"
            self.pause_btn.configure(text="Reanudar")
            self.status_var.set("En pausa. Pulsa Reanudar para continuar.")
        elif self._state == "paused":
            self._recorder.resume()
            self._state = "recording"
            self.pause_btn.configure(text="Pausar")
            self.status_var.set("Grabando…")

    def _tick(self) -> None:
        self._tick_id = None
        if self._recorder is None:
            return

        elapsed = int(self._recorder.duration)
        self.timer_var.set(f"{elapsed // 60:02d}:{elapsed % 60:02d}")

        width = max(1, self.level_canvas.winfo_width())
        level = self._recorder.level if self._state == "recording" else 0.0
        self.level_canvas.coords(
            self._level_bar, 0, 0, int(width * level), 12
        )
        self._tick_id = self.after(150, self._tick)

    def _stop_tick(self) -> None:
        if self._tick_id is not None:
            try:
                self.after_cancel(self._tick_id)
            except tk.TclError:
                pass
            self._tick_id = None

    def _stop(self) -> None:
        if self._recorder is None or self._done:
            return

        self._stop_tick()
        path = self._recorder.stop()
        duration = self._recorder.duration
        self._recorder = None
        self._state = "idle"
        self.pause_btn.configure(text="Pausar")

        if duration < 0.6:
            try:
                path.unlink()
            except OSError:
                pass
            self.status_var.set("La grabación es demasiado corta. Inténtalo de nuevo.")
            self.timer_var.set("00:00")
            self.level_canvas.coords(self._level_bar, 0, 0, 0, 12)
            self.start_btn.state(["!disabled"])
            self.pause_btn.state(["disabled"])
            self.stop_btn.state(["disabled"])
            self.model_box.state(["!disabled"])
            self.language_box.state(["!disabled"])
            return

        self._done = True
        self.status_var.set("Grabación lista. Transcribiendo…")
        self.start_btn.state(["disabled"])
        self.pause_btn.state(["disabled"])
        self.stop_btn.state(["disabled"])
        model = self.model_var.get()
        language = self.language_var.get()
        self._close()
        self.on_ready(str(path), model, language)

    def _cancel(self) -> None:
        if self._done:
            return
        self._done = True
        self._stop_tick()
        if self._recorder is not None:
            self._recorder.cancel()
            self._recorder = None
        self._close()

    def _close(self) -> None:
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()


class ResultWindow(tk.Toplevel):
    """Ventana con el texto extraído y las acciones de copiar/guardar."""

    def __init__(self, master: tk.Misc, app: "MultiToolsApp") -> None:
        super().__init__(master)
        self.app = app
        self.title("Resultado — Multi Tools")
        self.geometry("760x520")
        self.minsize(480, 320)
        self.configure(bg=BG)
        self.transient(master)

        self.status_var = tk.StringVar(value="Listo.")
        self.counter_var = tk.StringVar(value="0 caracteres")

        container = tk.Frame(self, bg=BG)
        container.pack(fill="both", expand=True, padx=16, pady=16)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        head = tk.Frame(container, bg=BG)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(
            head,
            text="Texto extraído",
            bg=BG,
            fg=TEXT,
            font=("DejaVu Sans", 15, "bold"),
        ).pack(side="left")
        tk.Label(
            head,
            textvariable=self.counter_var,
            bg=BG,
            fg=MUTED,
            font=("DejaVu Sans", 9),
        ).pack(side="right")

        card = tk.Frame(
            container,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        card.grid(row=1, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)

        text_frame = tk.Frame(card, bg=CARD)
        text_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self.text = tk.Text(
            text_frame,
            wrap="word",
            undo=True,
            font=("DejaVu Sans", 11),
            bg="#fbfcff",
            fg=TEXT,
            insertbackground=TEXT,
            selectbackground="#cfe0ff",
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            padx=12,
            pady=10,
            spacing1=2,
            spacing3=2,
        )
        scrollbar = ttk.Scrollbar(
            text_frame, orient="vertical", command=self.text.yview
        )
        self.text.configure(yscrollcommand=scrollbar.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text.bind("<<Modified>>", self._on_text_modified)

        actions = tk.Frame(card, bg=CARD)
        actions.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))

        ttk.Button(
            actions, text="Copiar texto", style="Accent.TButton", command=self._copy
        ).pack(side="left")
        ttk.Button(
            actions, text="Guardar .txt", style="Secondary.TButton", command=self._save
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            actions, text="Limpiar", style="Ghost.TButton", command=self._clear
        ).pack(side="right")

        tk.Label(
            container,
            textvariable=self.status_var,
            bg=BG,
            fg=MUTED,
            font=("DejaVu Sans", 9),
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", pady=(8, 0))

    def set_text(self, text: str) -> None:
        self.text.delete("1.0", "end")
        if text:
            self.text.insert("1.0", text)
        self.text.edit_modified(False)
        self._update_counter()
        self.status_var.set("Texto listo para copiar o guardar.")
        self.app._set_last_text(text)

    def _update_counter(self) -> None:
        count = len(self.text.get("1.0", "end-1c"))
        self.counter_var.set(f"{count} caracteres")

    def _on_text_modified(self, _event=None) -> None:
        if self.text.edit_modified():
            self.text.edit_modified(False)
            self._update_counter()
            self.app._set_last_text(self.text.get("1.0", "end-1c"))

    def _copy(self) -> None:
        text = self.text.get("1.0", "end-1c").strip()
        if not text:
            self.status_var.set("No hay texto para copiar.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update_idletasks()
        self.status_var.set("Texto copiado al portapapeles.")
        self.app._set_status("Texto copiado al portapapeles.")

    def _save(self) -> None:
        text = self.text.get("1.0", "end-1c").strip()
        if not text:
            self.status_var.set("No hay texto para guardar.")
            return

        default_name = f"texto_{datetime.now():%Y%m%d_%H%M%S}.txt"
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Guardar texto",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=(("Archivo de texto", "*.txt"), ("Todos los archivos", "*.*")),
        )
        if not path:
            return

        try:
            Path(path).write_text(text + "\n", encoding="utf-8")
        except OSError as exc:
            messagebox.showerror(
                "No se pudo guardar",
                f"No se pudo escribir el archivo:\n\n{exc}",
                parent=self,
            )
            return

        self.status_var.set(f"Texto guardado en {Path(path).name}.")
        self.app._set_status(f"Texto guardado en {Path(path).name}.")

    def _clear(self) -> None:
        self.text.delete("1.0", "end")
        self._update_counter()
        self.status_var.set("Texto limpiado.")
        self.app._set_last_text("")


class MultiToolsApp:
    def __init__(self) -> None:
        self.root = tk.Tk(className="MultiTools")
        self.root.title(f"{APP_NAME} — OCR y transcripción")
        self.root.iconname(APP_NAME)
        self.root.geometry("320x200")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self._busy = False
        self._selector: RegionSelector | None = None
        self._result: ResultWindow | None = None
        self._last_text = ""
        self._action_buttons: list[ttk.Button] = []
        self._icon_photos: list[ImageTk.PhotoImage] = []
        self._icon_photo: ImageTk.PhotoImage | None = None
        self._logo_photo: ImageTk.PhotoImage | None = None

        self._load_icon()

        self.ocr_lang_var = tk.StringVar(value=ocr.DEFAULT_LANGUAGE)
        self.model_var = tk.StringVar(value=transcribe.DEFAULT_MODEL)
        self.whisper_lang_var = tk.StringVar(value="Automático")
        self.status_var = tk.StringVar(value="Listo.")

        self._build_styles()
        self._build_ui()

        languages = ocr.available_languages()
        if not ocr.is_available():
            self._set_status("Tesseract no encontrado. Ejecuta ./setup.sh.")
        elif "spa" not in languages:
            self._set_status("Tesseract está disponible, pero falta el idioma español.")
        else:
            self._set_status("Listo. Captura la pantalla o elige un archivo.")

    # ---------------------------------------------------------------- estilos

    def _load_icon(self) -> None:
        try:
            with Image.open(ICON_PATH) as source:
                icon = source.convert("RGBA")
                icon.load()
        except Exception:  # noqa: BLE001 - el icono es opcional
            return

        self._icon_photos = [
            ImageTk.PhotoImage(icon.resize((size, size), Image.LANCZOS))
            for size in (128, 64, 32)
        ]
        self._icon_photo = self._icon_photos[0]
        try:
            self.root.iconphoto(True, *self._icon_photos)
        except tk.TclError:
            pass

        logo = icon.resize((26, 26), Image.LANCZOS)
        self._logo_photo = ImageTk.PhotoImage(logo)

    def _apply_icon(self, window: tk.Toplevel) -> None:
        if not self._icon_photos:
            return
        try:
            window.iconphoto(True, *self._icon_photos)
        except tk.TclError:
            pass

    def _build_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("Card.TLabel", background=CARD, foreground=TEXT)
        style.configure(
            "Muted.TLabel", background=CARD, foreground=MUTED, font=("DejaVu Sans", 9)
        )

        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="#ffffff",
            borderwidth=0,
            padding=(14, 8),
            font=("DejaVu Sans", 10, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[("disabled", "#a8c0ef"), ("active", ACCENT_DARK)],
            foreground=[("disabled", "#f3f6fd")],
        )

        style.configure(
            "Secondary.TButton",
            background=SOFT,
            foreground=TEXT,
            borderwidth=0,
            padding=(12, 8),
            font=("DejaVu Sans", 10),
        )
        style.map(
            "Secondary.TButton",
            background=[("disabled", "#f0f3f9"), ("active", "#d9e4fa")],
            foreground=[("disabled", "#9aa6ba")],
        )

        style.configure(
            "Ghost.TButton",
            background=CARD,
            foreground=MUTED,
            borderwidth=0,
            padding=(12, 8),
            font=("DejaVu Sans", 10),
        )
        style.map(
            "Ghost.TButton",
            background=[("active", SOFT)],
            foreground=[("active", TEXT)],
        )

        style.configure(
            "MiniGhost.TButton",
            background=BG,
            foreground=ACCENT,
            borderwidth=0,
            padding=(8, 4),
            font=("DejaVu Sans", 9, "bold"),
        )
        style.map(
            "MiniGhost.TButton",
            background=[("active", SOFT)],
            foreground=[("disabled", "#aab6c9"), ("active", ACCENT_DARK)],
        )

        style.configure(
            "Danger.TButton",
            background="#d64550",
            foreground="#ffffff",
            borderwidth=0,
            padding=(12, 8),
            font=("DejaVu Sans", 10, "bold"),
        )
        style.map(
            "Danger.TButton",
            background=[("disabled", "#eab4b8"), ("active", "#b8323c")],
            foreground=[("disabled", "#fff2f3")],
        )

        style.configure(
            "Compact.TButton",
            background=SOFT,
            foreground=TEXT,
            borderwidth=0,
            padding=(6, 7),
            font=("DejaVu Sans", 9),
        )
        style.map(
            "Compact.TButton",
            background=[("disabled", "#f0f3f9"), ("active", "#d9e4fa")],
            foreground=[("disabled", "#9aa6ba")],
        )

        style.configure(
            "Picker.TButton",
            background=SOFT,
            foreground=TEXT,
            borderwidth=0,
            padding=(9, 4),
            font=("DejaVu Sans", 9),
        )
        style.map(
            "Picker.TButton",
            background=[("active", "#d9e4fa")],
            foreground=[("active", TEXT)],
        )

        style.configure(
            "TCombobox",
            fieldbackground="#ffffff",
            background="#ffffff",
            foreground=TEXT,
            padding=3,
        )

        style.configure("TCheckbutton", background=BG, foreground=TEXT)
        style.map("TCheckbutton", background=[("active", BG)])

        style.configure(
            "Treeview",
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground=TEXT,
            rowheight=26,
            font=("DejaVu Sans", 9),
        )
        style.configure(
            "Treeview.Heading",
            background=SOFT,
            foreground=TEXT,
            font=("DejaVu Sans", 9, "bold"),
            padding=(6, 5),
        )
        style.map(
            "Treeview",
            background=[("selected", "#dbe7ff")],
            foreground=[("selected", TEXT)],
        )

    # ------------------------------------------------------------------- UI

    def _build_ui(self) -> None:
        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=14, pady=12)

        header = tk.Frame(container, bg=BG)
        header.pack(fill="x")
        if self._logo_photo is not None:
            tk.Label(header, image=self._logo_photo, bg=BG).pack(
                side="left", padx=(0, 6)
            )
        tk.Label(
            header,
            text=APP_NAME,
            bg=BG,
            fg=TEXT,
            font=("DejaVu Sans", 16, "bold"),
        ).pack(side="left")

        ttk.Combobox(
            header,
            textvariable=self.ocr_lang_var,
            values=ocr.LANGUAGES,
            state="readonly",
            width=9,
        ).pack(side="right")

        capture_btn = ttk.Button(
            container,
            text="Capturar pantalla",
            style="Accent.TButton",
            command=self._start_capture,
        )
        capture_btn.pack(fill="x", pady=(10, 0))

        file_row = tk.Frame(container, bg=BG)
        file_row.pack(fill="x", pady=(6, 0))
        file_row.columnconfigure(0, weight=1)
        file_row.columnconfigure(1, weight=1)
        file_row.columnconfigure(2, weight=1)

        image_btn = ttk.Button(
            file_row,
            text="Imagen…",
            style="Compact.TButton",
            command=self._choose_image,
        )
        image_btn.grid(row=0, column=0, sticky="ew", padx=(0, 3))

        media_btn = ttk.Button(
            file_row,
            text="Audio/video…",
            style="Compact.TButton",
            command=self._choose_media,
        )
        media_btn.grid(row=0, column=1, sticky="ew", padx=(3, 3))

        mic_btn = ttk.Button(
            file_row,
            text="Micrófono…",
            style="Compact.TButton",
            command=self._open_microphone,
        )
        mic_btn.grid(row=0, column=2, sticky="ew", padx=(3, 0))

        bottom = tk.Frame(container, bg=BG)
        bottom.pack(fill="x", pady=(10, 0))
        bottom.columnconfigure(0, weight=1)

        tk.Label(
            bottom,
            textvariable=self.status_var,
            bg=BG,
            fg=MUTED,
            font=("DejaVu Sans", 8),
            anchor="w",
            justify="left",
            wraplength=220,
        ).grid(row=0, column=0, sticky="ew")

        self.view_btn = ttk.Button(
            bottom,
            text="Ver texto",
            style="MiniGhost.TButton",
            command=self._show_last_result,
            state="disabled",
        )
        self.view_btn.grid(row=0, column=1, sticky="e", padx=(8, 0))

        self._action_buttons.extend([capture_btn, image_btn, media_btn, mic_btn])

    # --------------------------------------------------------------- helpers

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        for button in self._action_buttons:
            if busy:
                button.state(["disabled"])
            else:
                button.state(["!disabled"])

    def _set_last_text(self, text: str) -> None:
        self._last_text = text
        if text.strip():
            self.view_btn.state(["!disabled"])
        else:
            self.view_btn.state(["disabled"])

    def _set_output(self, text: str) -> None:
        if self._result is not None and self._result.winfo_exists():
            self._result.set_text(text)
            self._result.deiconify()
            self._result.lift()
            self._result.focus_force()
        else:
            self._result = ResultWindow(self.root, self)
            self._apply_icon(self._result)
            self._result.set_text(text)
            self._result.lift()
            self._result.focus_force()
        self._set_last_text(text)

    def _show_last_result(self) -> None:
        if not self._last_text.strip():
            self._set_status("Todavía no hay texto extraído.")
            return
        if self._result is not None and self._result.winfo_exists():
            self._result.deiconify()
            self._result.lift()
            self._result.focus_force()
        else:
            self._set_output(self._last_text)

    def _run_async(self, work, on_done, on_error) -> None:
        def runner() -> None:
            try:
                result = work()
            except Exception as exc:  # noqa: BLE001 - se muestra en la interfaz
                self.root.after(0, lambda error=exc: on_error(error))
                return
            self.root.after(0, lambda value=result: on_done(value))

        threading.Thread(target=runner, daemon=True).start()

    def _restore_main_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        try:
            self.root.focus_force()
        except tk.TclError:
            pass

    # -------------------------------------------------------------- captura

    def _start_capture(self) -> None:
        if self._busy:
            return
        self._set_status("Selecciona el área y confirma con Enter o el botón Confirmar.")
        self.root.withdraw()
        self.root.after(250, self._grab_screen)

    def _grab_screen(self) -> None:
        try:
            screenshot = ImageGrab.grab()
        except Exception as exc:  # noqa: BLE001
            self._restore_main_window()
            self._set_status("No se pudo capturar la pantalla.")
            messagebox.showerror(
                "Captura de pantalla",
                f"No se pudo tomar la captura:\n\n{exc}",
                parent=self.root,
            )
            return

        self._selector = RegionSelector(
            self.root,
            screenshot,
            lambda box, shot=screenshot: self._on_region_selected(box, shot),
        )

    def _on_region_selected(self, box, screenshot: Image.Image) -> None:
        self._selector = None
        self._restore_main_window()

        if box is None:
            self._set_status("Captura cancelada.")
            return

        image = screenshot.crop(box)
        self._start_ocr(image, "captura de pantalla")

    # ----------------------------------------------------------------- OCR

    def _choose_image(self) -> None:
        if self._busy:
            return
        picker = FilePickerDialog(
            self.root,
            "Seleccionar imagen",
            IMAGE_EXTENSIONS,
            settings.initial_directory(),
            self._open_selected_image,
        )
        self._apply_icon(picker)

    def _open_selected_image(self, path: str) -> None:
        settings.set_last_directory(Path(path).parent)

        try:
            with Image.open(path) as source:
                image = source.convert("RGB")
                image.load()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                "Imagen no válida",
                f"No se pudo abrir la imagen:\n\n{exc}",
                parent=self.root,
            )
            return

        self._start_ocr(image, Path(path).name)

    def _start_ocr(self, image: Image.Image, source_name: str) -> None:
        if not ocr.is_available():
            messagebox.showerror(
                "OCR no disponible",
                "No se encontró Tesseract. Ejecuta ./setup.sh en la carpeta del proyecto.",
                parent=self.root,
            )
            return

        self._set_busy(True)
        self._set_status(f"Extrayendo texto de {source_name}…")

        language = self.ocr_lang_var.get()

        def work() -> str:
            return ocr.extract_text(image, language)

        def done(text: str) -> None:
            self._set_busy(False)
            if text:
                self._set_status(f"Listo: {len(text)} caracteres extraídos. Ver texto.")
                self._set_output(text)
            else:
                self._set_status("No se detectó texto en la imagen.")

        def error(exc: Exception) -> None:
            self._set_busy(False)
            self._set_status("Error al extraer el texto.")
            messagebox.showerror(
                "Error de OCR",
                f"No se pudo extraer el texto:\n\n{exc}",
                parent=self.root,
            )

        self._run_async(work, done, error)

    # ------------------------------------------------------- audio y video

    def _choose_media(self) -> None:
        if self._busy:
            return
        picker = FilePickerDialog(
            self.root,
            "Seleccionar audio o video",
            MEDIA_EXTENSIONS,
            settings.initial_directory(),
            self._open_media_dialog,
        )
        self._apply_icon(picker)

    def _open_media_dialog(self, path: str) -> None:
        settings.set_last_directory(Path(path).parent)

        threading.Thread(
            target=transcribe.preload_model,
            args=(self.model_var.get(),),
            daemon=True,
        ).start()

        dialog = TranscribeDialog(
            self.root,
            path,
            self.model_var.get(),
            self.whisper_lang_var.get(),
            lambda model, language, media=path: self._transcribe_media(
                media, model, language
            ),
        )
        self._apply_icon(dialog)

    def _open_microphone(self) -> None:
        if self._busy:
            return
        if not microphone.is_available():
            messagebox.showerror(
                "Micrófono no disponible",
                "No se encontró PortAudio. Ejecuta ./setup.sh en la carpeta del proyecto.",
                parent=self.root,
            )
            return

        dialog = MicrophoneDialog(
            self.root,
            self.model_var.get(),
            self.whisper_lang_var.get(),
            self._recording_ready,
        )
        self._apply_icon(dialog)

    def _recording_ready(
        self, path: str, model_size: str, language_name: str
    ) -> None:
        self.model_var.set(model_size)
        self.whisper_lang_var.set(language_name)
        self._transcribe_media(path, model_size, language_name, cleanup=True)

    def _transcribe_media(
        self,
        path: str,
        model_size: str,
        language_name: str,
        cleanup: bool = False,
    ) -> None:
        if self._busy:
            if cleanup:
                try:
                    Path(path).unlink()
                except OSError:
                    pass
            return
        if not Path(path).exists():
            messagebox.showerror(
                "Archivo no encontrado",
                "El archivo seleccionado ya no existe.",
                parent=self.root,
            )
            return

        self.model_var.set(model_size)
        self.whisper_lang_var.set(language_name)
        language = transcribe.LANGUAGES.get(language_name)
        name = Path(path).name

        self._set_busy(True)
        self._set_status(f"Preparando la transcripción de {name}…")

        def on_status(message: str) -> None:
            self.root.after(0, lambda text=message: self._set_status(text))

        def on_progress(fraction: float) -> None:
            percent = int(fraction * 100)
            self.root.after(
                0,
                lambda value=percent: self._set_status(
                    f"Transcribiendo {name}… {value}%"
                ),
            )

        def work() -> str:
            return transcribe.transcribe(
                path,
                model_size=model_size,
                language=language,
                on_status=on_status,
                on_progress=on_progress,
            )

        def cleanup_file() -> None:
            if cleanup:
                try:
                    Path(path).unlink()
                except OSError:
                    pass

        def done(text: str) -> None:
            cleanup_file()
            self._set_busy(False)
            if text:
                self._set_status(f"Listo: {len(text)} caracteres transcritos. Ver texto.")
                self._set_output(text)
            else:
                self._set_status("No se detectó voz en el archivo.")

        def error(exc: Exception) -> None:
            cleanup_file()
            self._set_busy(False)
            self._set_status("Error durante la transcripción.")
            messagebox.showerror(
                "Error de transcripción",
                f"No se pudo transcribir el archivo:\n\n{exc}\n\n"
                "Comprueba tu conexión a Internet si es la primera vez que usas el modelo.",
                parent=self.root,
            )

        self._run_async(work, done, error)

    # ----------------------------------------------------------------- run

    def run(self) -> None:
        self.root.mainloop()
