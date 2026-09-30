#!/usr/bin/env python3
# =============================================================================
# RJOS Desktop Icons — desktop_icons.py
# Ícones na área de trabalho do RJOS
#
# Exibe ícones do desktop (Lixeira, Home, pastas do ~/Desktop).
# Suporte a duplo-clique para abrir, grade com snap automático.
#
# Dependências:
#   python3-gi (PyGObject), gir1.2-gtk-4.0, gir1.2-adw-1
#   gtk4-layer-shell (libgtk4-layer-shell)
# =============================================================================

import gi
import os
import subprocess
from pathlib import Path

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gdk, Gio

try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except (ValueError, ImportError):
    HAS_LAYER_SHELL = False

# ─── Constantes ───────────────────────────────────────────────────────────────

ICON_SIZE       = 64       # Tamanho do ícone
ICON_GRID_X     = 100      # Largura da célula do grid
ICON_GRID_Y     = 96       # Altura da célula do grid
ICON_PADDING    = 20       # Margem da borda da tela
PANEL_HEIGHT    = 42       # Altura do painel superior
DOCK_RESERVED   = 80       # Espaço reservado para o dock

# Mapeamento de extensão → ícone emoji
FILE_ICONS = {
    ".txt": "📄", ".md": "📝", ".pdf": "📕",
    ".png": "🖼️", ".jpg": "🖼️", ".jpeg": "🖼️", ".gif": "🖼️", ".svg": "🖼️",
    ".mp3": "🎵", ".flac": "🎵", ".wav": "🎵", ".ogg": "🎵",
    ".mp4": "🎬", ".mkv": "🎬", ".avi": "🎬", ".webm": "🎬",
    ".zip": "📦", ".tar": "📦", ".gz": "📦", ".7z": "📦",
    ".py": "🐍", ".js": "📜", ".c": "📜", ".h": "📜",
    ".sh": "⚡", ".bash": "⚡",
    ".deb": "📦", ".rpm": "📦",
    ".iso": "💿",
    ".html": "🌐", ".css": "🎨",
}

FOLDER_ICON = "📁"
DEFAULT_FILE_ICON = "📄"

# ─── CSS ──────────────────────────────────────────────────────────────────────

DESKTOP_ICONS_CSS = """
/* ══════════════════════════════════════════════════════════════════
   RJOS Desktop Icons — Estilos Oficiais RJOS
   ══════════════════════════════════════════════════════════════════ */

.rjos-desktop-icons-window {
    background: transparent;
}

.rjos-desktop-icon {
    background: transparent;
    border: 2px solid transparent;
    border-radius: 10px;
    padding: 6px;
    min-width: 80px;
    min-height: 76px;
    transition: all 120ms ease;
}

.rjos-desktop-icon:hover {
    background-color: rgba(41, 41, 41, 0.75);
    border-color: rgba(0, 91, 150, 0.35);
}

.rjos-desktop-icon:active,
.rjos-desktop-icon-selected {
    background-color: rgba(0, 91, 150, 0.35);
    border-color: #005B96;
}

.rjos-desktop-icon-emoji {
    font-size: 36px;
    margin-bottom: 2px;
}

.rjos-desktop-icon-label {
    color: #FFFFFF;
    font-size: 11px;
    font-weight: 500;
    text-shadow: 0 1px 4px rgba(0, 0, 0, 0.9);
}

.rjos-desktop-icon-label-editing {
    background-color: #1E1E1E;
    border: 1px solid #005B96;
    border-radius: 4px;
    color: #FFFFFF;
    font-size: 11px;
    padding: 2px 4px;
}
"""

# ─── Itens especiais do desktop ───────────────────────────────────────────────

SPECIAL_ICONS = [
    {
        "name": "Home",
        "icon": "🏠",
        "action": "xdg-open ~",
    },
    {
        "name": "Lixeira",
        "icon": "🗑️",
        "action": "xdg-open trash:///",
    },
]


class DesktopIconData:
    """Dados de um ícone no desktop"""

    def __init__(self, name, icon, path=None, action=None, is_dir=False):
        self.name = name
        self.icon = icon
        self.path = path
        self.action = action
        self.is_dir = is_dir
        self.selected = False
        self.grid_x = 0  # Posição no grid (coluna)
        self.grid_y = 0  # Posição no grid (linha)


class RjosDesktopIcons(Gtk.Window):
    """Janela de ícones do desktop (transparente, cobrindo a tela)"""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.icons = []
        self.selected_icon = None

        self._setup_window()
        self._scan_desktop()
        self._build_ui()
        self._start_watcher()

    def _setup_window(self):
        self.set_decorated(False)
        self.set_resizable(False)
        self.add_css_class("rjos-desktop-icons-window")

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.BOTTOM)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_exclusive_zone(self, -1)
            GtkLayerShell.set_namespace(self, "rjos-desktop-icons")

    def _scan_desktop(self):
        """Escaneia ~/Desktop ou ~/Área de Trabalho"""
        self.icons = []
        grid_col = 0
        grid_row = 0

        # Ícones especiais primeiro
        for special in SPECIAL_ICONS:
            data = DesktopIconData(
                name=special["name"],
                icon=special["icon"],
                action=special["action"],
            )
            data.grid_x = grid_col
            data.grid_y = grid_row
            self.icons.append(data)
            grid_row += 1

        # Escaneia pasta do desktop
        desktop_dirs = [
            Path.home() / "Desktop",
            Path.home() / "Área de Trabalho",
            Path.home() / "Area de Trabalho",
        ]

        desktop_path = None
        for d in desktop_dirs:
            if d.exists():
                desktop_path = d
                break

        if desktop_path:
            try:
                entries = sorted(desktop_path.iterdir(),
                                 key=lambda p: (not p.is_dir(), p.name.lower()))
                for entry in entries[:30]:  # Limita a 30 ícones
                    if entry.name.startswith('.'):
                        continue

                    if entry.is_dir():
                        icon = FOLDER_ICON
                    else:
                        ext = entry.suffix.lower()
                        icon = FILE_ICONS.get(ext, DEFAULT_FILE_ICON)

                    data = DesktopIconData(
                        name=entry.name[:16],  # Trunca nomes longos
                        icon=icon,
                        path=str(entry),
                        is_dir=entry.is_dir(),
                    )
                    data.grid_x = grid_col
                    data.grid_y = grid_row
                    self.icons.append(data)

                    grid_row += 1
                    # Próxima coluna quando atinge o limite vertical
                    max_rows = 8
                    if grid_row >= max_rows:
                        grid_row = 0
                        grid_col += 1

            except PermissionError:
                pass

    def _build_ui(self):
        # Fixed layout para posicionamento absoluto
        fixed = Gtk.Fixed()

        for icon_data in self.icons:
            widget = self._create_icon_widget(icon_data)
            x = ICON_PADDING + icon_data.grid_x * ICON_GRID_X
            y = PANEL_HEIGHT + ICON_PADDING + icon_data.grid_y * ICON_GRID_Y
            fixed.put(widget, x, y)

        self.set_child(fixed)

    def _create_icon_widget(self, icon_data):
        """Cria widget de um ícone do desktop"""
        btn = Gtk.Button()
        btn.add_css_class("rjos-desktop-icon")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_halign(Gtk.Align.CENTER)

        # Ícone emoji
        icon_lbl = Gtk.Label(label=icon_data.icon)
        icon_lbl.add_css_class("rjos-desktop-icon-emoji")
        vbox.append(icon_lbl)

        # Nome
        name_lbl = Gtk.Label(label=icon_data.name)
        name_lbl.add_css_class("rjos-desktop-icon-label")
        name_lbl.set_max_width_chars(12)
        name_lbl.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        vbox.append(name_lbl)

        btn.set_child(vbox)

        # Duplo-clique para abrir
        gesture = Gtk.GestureClick()
        gesture.set_button(1)
        gesture.connect("pressed", self._on_icon_clicked, icon_data)
        btn.add_controller(gesture)

        # Clique direito → menu de contexto
        gesture_right = Gtk.GestureClick()
        gesture_right.set_button(3)
        gesture_right.connect("pressed", self._on_icon_right_click, icon_data)
        btn.add_controller(gesture_right)

        return btn

    def _on_icon_clicked(self, gesture, n_press, x, y, icon_data):
        """Duplo-clique abre, clique único seleciona"""
        if n_press == 2:
            self._open_icon(icon_data)
        elif n_press == 1:
            self._select_icon(icon_data)

    def _open_icon(self, icon_data):
        """Abre o item (arquivo ou pasta)"""
        if icon_data.action:
            subprocess.Popen(
                ["/bin/sh", "-c", icon_data.action],
                start_new_session=True
            )
        elif icon_data.path:
            subprocess.Popen(
                ["xdg-open", icon_data.path],
                start_new_session=True
            )

    def _select_icon(self, icon_data):
        """Seleciona um ícone (destaque visual)"""
        self.selected_icon = icon_data
        icon_data.selected = True

    def _on_icon_right_click(self, gesture, n_press, x, y, icon_data):
        """Menu de contexto para o ícone"""
        # TODO: Implementar menu de contexto por ícone
        # (Abrir, Abrir com..., Renomear, Mover para lixeira, Propriedades)
        print(f"[desktop-icons] Contexto: {icon_data.name}")

    def _start_watcher(self):
        """Monitora mudanças na pasta do desktop"""
        GLib.timeout_add_seconds(10, self._refresh)

    def _refresh(self):
        """Re-escaneia e atualiza ícones"""
        # TODO: Usar GFileMonitor para atualização em tempo real
        return True
