#!/usr/bin/env python3
# =============================================================================
# RJOS Files — rjos-files.py
# Gerenciador de arquivos próprio do RJOS
#
# Interface:
#   ┌─────────────────────────────────────────────┐
#   │ ← → ↑  /home/usuario             🔍  ⋮     │
#   ├─────────────┬───────────────────────────────┤
#   │ 🏠 Home     │ 📁 Documentos                 │
#   │ 🖥 Desktop  │ 📁 Downloads                  │
#   │ ⬇ Downloads │ 📁 Imagens                    │
#   │ 📄 Docs     │ 📄 arquivo.txt                │
#   │ 🖼 Imagens  │                               │
#   └─────────────┴───────────────────────────────┘
# =============================================================================

import gi
import os
import sys
import shutil
import subprocess
import mimetypes
from pathlib import Path
from datetime import datetime

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Gio, GdkPixbuf, Pango

RJOS_FILES_CSS = """
/* ══ RJOS Files ══════════════════════════════════════════════════ */

.rjos-files-window {
    background-color: #0D1B2A;
}

/* Sidebar */
.rjos-sidebar {
    background-color: #122030;
    border-right: 1px solid #1E3048;
    min-width: 180px;
    max-width: 220px;
    padding: 8px 0;
}
.rjos-sidebar-item {
    background: transparent;
    border: none;
    border-radius: 6px;
    color: #8BA7BF;
    font-size: 13px;
    padding: 8px 12px;
    margin: 1px 8px;
    text-align: left;
    transition: all 150ms ease;
}
.rjos-sidebar-item:hover {
    background-color: rgba(0, 212, 255, 0.1);
    color: #E8F4FD;
}
.rjos-sidebar-item.active {
    background-color: rgba(0, 212, 255, 0.15);
    color: #00D4FF;
}
.rjos-sidebar-section {
    color: #4A6580;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 8px 12px 4px 12px;
    text-transform: uppercase;
}

/* Barra de localização */
.rjos-location-bar {
    background-color: #122030;
    border-bottom: 1px solid #1E3048;
    padding: 6px 8px;
    min-height: 42px;
}
.rjos-location-entry {
    background-color: #0D1B2A;
    border: 1px solid #1E3048;
    border-radius: 6px;
    color: #E8F4FD;
    font-size: 13px;
    padding: 4px 10px;
    transition: border-color 150ms ease;
}
.rjos-location-entry:focus {
    border-color: #00D4FF;
    box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.15);
}
.rjos-nav-btn {
    background: transparent;
    border: none;
    border-radius: 6px;
    color: #8BA7BF;
    font-size: 16px;
    padding: 4px 8px;
    transition: all 150ms ease;
}
.rjos-nav-btn:hover {
    background-color: rgba(0, 212, 255, 0.1);
    color: #00D4FF;
}
.rjos-nav-btn:disabled {
    color: #2A3F58;
}

/* Grade de arquivos */
.rjos-file-area {
    background-color: #0D1B2A;
}
.rjos-file-item {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 8px;
    margin: 2px;
    transition: all 150ms ease;
    min-width: 90px;
    max-width: 110px;
}
.rjos-file-item:hover {
    background-color: rgba(0, 212, 255, 0.08);
    border-color: #1E3048;
}
.rjos-file-item.selected {
    background-color: rgba(0, 212, 255, 0.18);
    border-color: #00D4FF;
}
.rjos-file-icon {
    font-size: 36px;
    margin-bottom: 4px;
}
.rjos-file-name {
    color: #E8F4FD;
    font-size: 11px;
    text-align: center;
}

/* Barra de status */
.rjos-statusbar {
    background-color: #0A1520;
    border-top: 1px solid #1E3048;
    color: #4A6580;
    font-size: 11px;
    padding: 4px 12px;
    min-height: 24px;
}
"""

# ─── Ícones por tipo de arquivo ───────────────────────────────────────────────

MIME_ICONS = {
    "inode/directory":        "📁",
    "text/plain":             "📄",
    "text/html":              "🌐",
    "text/x-python":          "🐍",
    "text/x-csrc":            "⚙️",
    "text/x-chdr":            "⚙️",
    "application/pdf":        "📕",
    "application/zip":        "📦",
    "application/x-tar":      "📦",
    "application/gzip":       "📦",
    "application/x-7z-compressed": "📦",
    "image/jpeg":             "🖼️",
    "image/png":              "🖼️",
    "image/gif":              "🎞️",
    "image/svg+xml":          "🎨",
    "audio/mpeg":             "🎵",
    "audio/flac":             "🎵",
    "audio/ogg":              "🎵",
    "video/mp4":              "🎬",
    "video/mkv":              "🎬",
    "video/x-msvideo":        "🎬",
    "application/x-executable":"⚡",
    "application/x-sharedlib": "🔧",
    "application/json":       "📋",
    "application/xml":        "📋",
}

def get_file_icon(path: Path) -> str:
    if path.is_symlink():
        return "🔗"
    if path.is_dir():
        # Ícones especiais para dirs conhecidos
        name = path.name.lower()
        special = {
            "downloads": "⬇️",
            "desktop":   "🖥️",
            "documents": "📄",
            "pictures":  "🖼️",
            "music":     "🎵",
            "videos":    "🎬",
            "trash":     "🗑️",
        }
        return special.get(name, "📁")

    mime, _ = mimetypes.guess_type(str(path))
    if mime:
        # Tenta correspondência exata, depois por tipo base
        if mime in MIME_ICONS:
            return MIME_ICONS[mime]
        base = mime.split("/")[0]
        base_icons = {"image": "🖼️", "audio": "🎵", "video": "🎬", "text": "📄"}
        return base_icons.get(base, "📄")

    # Executável
    if os.access(path, os.X_OK):
        return "⚡"
    return "📄"


def human_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


# ─── Item de arquivo no grid ──────────────────────────────────────────────────

class FileItem(Gtk.Button):
    def __init__(self, path: Path):
        super().__init__()
        self.path = path
        self.selected = False

        self.add_css_class("rjos-file-item")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_halign(Gtk.Align.CENTER)

        icon_label = Gtk.Label(label=get_file_icon(path))
        icon_label.add_css_class("rjos-file-icon")
        vbox.append(icon_label)

        name = path.name
        name_label = Gtk.Label(label=name[:16] + ("…" if len(name) > 16 else ""))
        name_label.add_css_class("rjos-file-name")
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        name_label.set_max_width_chars(12)
        name_label.set_wrap(False)
        vbox.append(name_label)

        self.set_child(vbox)
        self.set_tooltip_text(name)

    def set_selected(self, selected: bool):
        self.selected = selected
        if selected:
            self.add_css_class("selected")
        else:
            self.remove_css_class("selected")


# ─── Janela principal ────────────────────────────────────────────────────────

class RjosFilesWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Arquivos — RJOS")
        self.set_default_size(900, 580)

        self.current_path = Path.home()
        self.history_back  = []
        self.history_fwd   = []
        self.selected_item = None
        self.show_hidden   = False

        self._build_ui()
        self._navigate_to(self.current_path, add_history=False)

    def _build_ui(self):
        # Titlebar
        header = Adw.HeaderBar()
        header.add_css_class("rjos-location-bar")

        # Botões de navegação
        self.btn_back = Gtk.Button(label="←")
        self.btn_back.add_css_class("rjos-nav-btn")
        self.btn_back.connect("clicked", lambda _: self._go_back())
        self.btn_back.set_sensitive(False)

        self.btn_fwd = Gtk.Button(label="→")
        self.btn_fwd.add_css_class("rjos-nav-btn")
        self.btn_fwd.connect("clicked", lambda _: self._go_forward())
        self.btn_fwd.set_sensitive(False)

        self.btn_up = Gtk.Button(label="↑")
        self.btn_up.add_css_class("rjos-nav-btn")
        self.btn_up.connect("clicked", lambda _: self._go_up())

        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        nav_box.append(self.btn_back)
        nav_box.append(self.btn_fwd)
        nav_box.append(self.btn_up)
        header.pack_start(nav_box)

        # Barra de localização
        self.location_entry = Gtk.Entry()
        self.location_entry.add_css_class("rjos-location-entry")
        self.location_entry.set_hexpand(True)
        self.location_entry.connect("activate", self._on_location_activate)
        header.set_title_widget(self.location_entry)

        # Menu de opções
        menu_btn = Gtk.Button(label="⋮")
        menu_btn.add_css_class("rjos-nav-btn")
        menu_btn.connect("clicked", self._on_menu_clicked)
        header.pack_end(menu_btn)

        # Busca
        search_btn = Gtk.Button(label="🔍")
        search_btn.add_css_class("rjos-nav-btn")
        search_btn.set_tooltip_text("Pesquisar")
        search_btn.connect("clicked", self._on_search_clicked)
        header.pack_end(search_btn)

        self.set_titlebar(header)

        # Layout principal
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_vexpand(True)
        paned.set_position(200)

        # Sidebar
        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar_scroll.add_css_class("rjos-sidebar")

        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._build_sidebar()
        sidebar_scroll.set_child(self.sidebar_box)
        paned.set_start_child(sidebar_scroll)

        # Área de arquivos
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.file_scroll = Gtk.ScrolledWindow()
        self.file_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.file_scroll.add_css_class("rjos-file-area")
        self.file_scroll.set_vexpand(True)

        self.file_flow = Gtk.FlowBox()
        self.file_flow.set_max_children_per_line(12)
        self.file_flow.set_min_children_per_line(4)
        self.file_flow.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.file_flow.set_homogeneous(False)
        self.file_flow.set_margin_start(8)
        self.file_flow.set_margin_top(8)
        self.file_flow.connect("child-activated", self._on_file_activated)
        self.file_scroll.set_child(self.file_flow)

        # Barra de status
        self.statusbar = Gtk.Label()
        self.statusbar.add_css_class("rjos-statusbar")
        self.statusbar.set_halign(Gtk.Align.START)
        self.statusbar.set_hexpand(True)

        right_box.append(self.file_scroll)
        right_box.append(self.statusbar)

        paned.set_end_child(right_box)

        self.set_content(paned)

        # Clique direito no área de arquivos
        gesture = Gtk.GestureClick()
        gesture.set_button(3)  # botão direito
        gesture.connect("released", self._on_right_click)
        self.file_flow.add_controller(gesture)

    def _build_sidebar(self):
        # Limpa
        child = self.sidebar_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.sidebar_box.remove(child)
            child = nxt

        favorites = [
            ("🏠 Home",        Path.home()),
            ("🖥️ Desktop",    Path.home() / "Desktop"),
            ("⬇️ Downloads",  Path.home() / "Downloads"),
            ("📄 Documentos", Path.home() / "Documents"),
            ("🖼️ Imagens",    Path.home() / "Pictures"),
            ("🎵 Música",     Path.home() / "Music"),
            ("🎬 Vídeos",     Path.home() / "Videos"),
        ]

        sec = Gtk.Label(label="Favoritos")
        sec.add_css_class("rjos-sidebar-section")
        sec.set_halign(Gtk.Align.START)
        self.sidebar_box.append(sec)

        for name, path in favorites:
            if path.exists():
                btn = Gtk.Button(label=name)
                btn.add_css_class("rjos-sidebar-item")
                btn.connect("clicked", self._on_sidebar_clicked, path)
                self.sidebar_box.append(btn)

        # Dispositivos montados
        devices = self._get_mounted_devices()
        if devices:
            sep = Gtk.Label(label="Dispositivos")
            sep.add_css_class("rjos-sidebar-section")
            sep.set_halign(Gtk.Align.START)
            sep.set_margin_top(8)
            self.sidebar_box.append(sep)

            for name, path in devices:
                btn = Gtk.Button(label=f"💾 {name}")
                btn.add_css_class("rjos-sidebar-item")
                btn.connect("clicked", self._on_sidebar_clicked, Path(path))
                self.sidebar_box.append(btn)

    def _get_mounted_devices(self):
        devices = []
        try:
            result = subprocess.run(
                ["lsblk", "-o", "LABEL,MOUNTPOINT", "-n", "-l"],
                capture_output=True, text=True, timeout=3
            )
            for line in result.stdout.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 2 and parts[1].startswith("/media"):
                    devices.append((parts[0] or "Disco", parts[1]))
        except Exception:
            pass
        return devices

    def _on_sidebar_clicked(self, btn, path: Path):
        self._navigate_to(path)

    def _navigate_to(self, path: Path, add_history=True):
        if not path.exists() or not path.is_dir():
            self._show_error(f"Não foi possível abrir: {path}")
            return

        if add_history and self.current_path != path:
            self.history_back.append(self.current_path)
            self.history_fwd.clear()

        self.current_path = path
        self.location_entry.set_text(str(path))

        self.btn_back.set_sensitive(len(self.history_back) > 0)
        self.btn_fwd.set_sensitive(len(self.history_fwd) > 0)
        self.btn_up.set_sensitive(path != path.parent)

        self._load_directory(path)

    def _load_directory(self, path: Path):
        # Remove itens existentes
        child = self.file_flow.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.file_flow.remove(child)
            child = nxt

        self.selected_item = None

        try:
            entries = sorted(
                path.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower())
            )
        except PermissionError:
            self._show_error("Permissão negada")
            return

        # Filtra arquivos ocultos
        if not self.show_hidden:
            entries = [e for e in entries if not e.name.startswith(".")]

        count_dirs  = 0
        count_files = 0

        for entry in entries:
            item = FileItem(entry)
            item.connect("clicked", self._on_file_clicked, entry)
            self.file_flow.append(item)

            if entry.is_dir():
                count_dirs += 1
            else:
                count_files += 1

        # Status
        total = count_dirs + count_files
        parts = []
        if count_dirs:  parts.append(f"{count_dirs} pasta{'s' if count_dirs > 1 else ''}")
        if count_files: parts.append(f"{count_files} arquivo{'s' if count_files > 1 else ''}")

        try:
            stat = shutil.disk_usage(str(path))
            free = human_size(stat.free)
            total_str = human_size(stat.total)
            disk_info = f" — {free} livre de {total_str}"
        except Exception:
            disk_info = ""

        self.statusbar.set_text(", ".join(parts) + disk_info if parts else "Pasta vazia")

    def _on_file_clicked(self, btn, path: Path):
        self.selected_item = path

    def _on_file_activated(self, flow, child):
        """Duplo clique (ou Enter) — abre arquivo/pasta"""
        item = child.get_child()
        if not isinstance(item, FileItem):
            return
        path = item.path
        self._open_path(path)

    def _open_path(self, path: Path):
        if path.is_dir():
            self._navigate_to(path)
        else:
            # Abre com aplicativo padrão
            subprocess.Popen(
                ["xdg-open", str(path)],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    def _on_right_click(self, gesture, n_press, x, y):
        """Menu de contexto com clique direito"""
        path = self.selected_item or self.current_path

        menu_items = [
            ("📂 Abrir",        lambda: self._open_path(path)),
            ("✂️ Recortar",     lambda: None),  # TODO Fase 3
            ("📋 Copiar",       lambda: None),
            ("📋 Colar",        lambda: None),
            ("✏️ Renomear",     lambda: self._rename_dialog(path)),
            ("🗑️ Mover para lixo", lambda: self._trash_item(path)),
            ("ℹ️ Propriedades", lambda: self._properties_dialog(path)),
        ]

        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_start(4)
        box.set_margin_end(4)
        box.set_margin_top(4)
        box.set_margin_bottom(4)

        for label, action in menu_items:
            if label == "─":
                box.append(Gtk.Separator())
                continue
            btn = Gtk.Button(label=label)
            btn.add_css_class("rjos-sidebar-item")
            btn.connect("clicked", lambda b, a=action: (popover.popdown(), a()))
            box.append(btn)

        popover.set_child(box)
        popover.set_parent(self.file_flow)
        popover.set_pointing_to(Gdk.Rectangle(x=int(x), y=int(y), width=1, height=1))
        popover.popup()

    def _rename_dialog(self, path: Path):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=f"Renomear {path.name}",
        )
        entry = Gtk.Entry()
        entry.set_text(path.name)
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("rename", "Renomear")
        dialog.set_default_response("rename")

        def on_response(d, response):
            if response == "rename":
                new_name = entry.get_text().strip()
                if new_name and new_name != path.name:
                    new_path = path.parent / new_name
                    try:
                        path.rename(new_path)
                        self._load_directory(self.current_path)
                    except Exception as e:
                        self._show_error(str(e))

        dialog.connect("response", on_response)
        dialog.present()

    def _trash_item(self, path: Path):
        trash = Path.home() / ".local/share/Trash/files"
        trash.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(path), str(trash / path.name))
            self._load_directory(self.current_path)
        except Exception as e:
            self._show_error(str(e))

    def _properties_dialog(self, path: Path):
        try:
            stat = path.stat()
            size = human_size(stat.st_size) if path.is_file() else "—"
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M")
            mime, _ = mimetypes.guess_type(str(path))

            dialog = Adw.MessageDialog(
                transient_for=self,
                heading=f"Propriedades — {path.name}",
                body=f"Localização: {path.parent}\n"
                     f"Tipo: {mime or ('Pasta' if path.is_dir() else 'Arquivo')}\n"
                     f"Tamanho: {size}\n"
                     f"Modificado: {modified}\n"
                     f"Permissões: {oct(stat.st_mode)[-3:]}"
            )
            dialog.add_response("ok", "OK")
            dialog.present()
        except Exception as e:
            self._show_error(str(e))

    def _show_error(self, msg: str):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Erro",
            body=msg
        )
        dialog.add_response("ok", "OK")
        dialog.present()

    def _go_back(self):
        if self.history_back:
            self.history_fwd.append(self.current_path)
            path = self.history_back.pop()
            self._navigate_to(path, add_history=False)

    def _go_forward(self):
        if self.history_fwd:
            self.history_back.append(self.current_path)
            path = self.history_fwd.pop()
            self._navigate_to(path, add_history=False)

    def _go_up(self):
        parent = self.current_path.parent
        if parent != self.current_path:
            self._navigate_to(parent)

    def _on_location_activate(self, entry):
        path = Path(entry.get_text().strip())
        self._navigate_to(path)

    def _on_search_clicked(self, btn):
        pass  # TODO: implementar busca com find/fd

    def _on_menu_clicked(self, btn):
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_start(4); box.set_margin_end(4)
        box.set_margin_top(4);   box.set_margin_bottom(4)

        items = [
            (f"{'✅' if self.show_hidden else '⬜'} Mostrar ocultos",
             self._toggle_hidden),
            ("📁 Nova pasta",  self._new_folder_dialog),
            ("🔄 Atualizar",   lambda: self._load_directory(self.current_path)),
            ("📂 Abrir terminal aqui", self._open_terminal_here),
        ]

        for label, action in items:
            btn2 = Gtk.Button(label=label)
            btn2.add_css_class("rjos-sidebar-item")
            btn2.connect("clicked", lambda b, a=action: (popover.popdown(), a()))
            box.append(btn2)

        popover.set_child(box)
        popover.set_parent(btn)
        popover.popup()

    def _toggle_hidden(self):
        self.show_hidden = not self.show_hidden
        self._load_directory(self.current_path)

    def _new_folder_dialog(self):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Nova Pasta",
        )
        entry = Gtk.Entry()
        entry.set_text("Nova Pasta")
        entry.select_region(0, -1)
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("create", "Criar")
        dialog.set_default_response("create")

        def on_response(d, response):
            if response == "create":
                name = entry.get_text().strip()
                if name:
                    try:
                        (self.current_path / name).mkdir()
                        self._load_directory(self.current_path)
                    except Exception as e:
                        self._show_error(str(e))

        dialog.connect("response", on_response)
        dialog.present()

    def _open_terminal_here(self):
        subprocess.Popen(
            ["rjos-terminal"],
            cwd=str(self.current_path),
            start_new_session=True,
            env={**os.environ, "PWD": str(self.current_path)}
        )


# ─── App ─────────────────────────────────────────────────────────────────────

class RjosFilesApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="org.rjos.files",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        provider = Gtk.CssProvider()
        provider.load_from_string(RJOS_FILES_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        win = RjosFilesWindow(application=self)
        win.present()


def main():
    app = RjosFilesApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
