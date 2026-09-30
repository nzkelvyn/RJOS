#!/usr/bin/env python3
# =============================================================================
# RJOS Shell — rjos-shell.py
# Desktop shell do RJOS: painel superior, launcher, wallpaper
#
# Usa GTK4 + gtk4-layer-shell para ancorar o painel no topo da tela
# Usa Wayland nativo (WAYLAND_DISPLAY deve estar setado pelo compositor)
#
# Dependências:
#   python3-gi (PyGObject), gir1.2-gtk-4.0, gir1.2-adw-1
#   gtk4-layer-shell (libgtk4-layer-shell ou gtk-layer-shell)
# =============================================================================

import gi
import os
import sys
import subprocess
import threading
import time
import json
from datetime import datetime
from pathlib import Path

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gdk, GdkPixbuf, Gio

# Importa componentes do desktop RJOS
try:
    from quick_settings import RjosQuickSettings
    HAS_QUICK_SETTINGS = True
except ImportError:
    HAS_QUICK_SETTINGS = False

try:
    from context_menu import RjosContextMenu
    HAS_CONTEXT_MENU = True
except ImportError:
    HAS_CONTEXT_MENU = False

# Tenta importar gtk4-layer-shell
try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except (ValueError, ImportError):
    HAS_LAYER_SHELL = False
    print("[WARN] gtk4-layer-shell não disponível. Painel sem ancoragem.")

# ─── Paleta RJOS ─────────────────────────────────────────────────────────────
# ─── Paleta Oficial RJOS ─────────────────────────────────────────────────────
RJOS_CSS = """
/* ══════════════════════════════════════════════════════════════════
   RJOS Shell Design System — Paleta Oficial
   ══════════════════════════════════════════════════════════════════ */

@define-color rjos-bg            #121212;
@define-color rjos-surface       #1E1E1E;
@define-color rjos-surface-hover #292929;
@define-color rjos-surface-active #333333;
@define-color rjos-border        rgba(255, 255, 255, 0.08);
@define-color rjos-blue          #005B96;
@define-color rjos-blue-hover    #006FB7;
@define-color rjos-blue-dim      rgba(0, 91, 150, 0.2);
@define-color rjos-green         #00A86B;
@define-color rjos-yellow        #F2C94C;
@define-color rjos-text          #FFFFFF;
@define-color rjos-subtext       #B8B8B8;
@define-color rjos-error         #E05252;

/* ══════════════════════════════════════════════════════════════════
   Painel Superior (Topbar)
   ══════════════════════════════════════════════════════════════════ */

.rjos-panel {
    background-color: #1E1E1E;
    border-bottom: 1px solid @rjos-border;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.6);
    padding: 0;
    min-height: 38px;
}

.rjos-panel-left,
.rjos-panel-center,
.rjos-panel-right {
    padding: 0 8px;
}

/* Botão Logo / Menu RJOS */
.rjos-logo-btn {
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px 10px;
    color: @rjos-blue;
    font-weight: 800;
    font-size: 13px;
    letter-spacing: 2px;
    transition: all 120ms ease;
}
.rjos-logo-btn:hover {
    background-color: @rjos-blue-dim;
    color: #FFFFFF;
}

/* Botões do painel */
.rjos-panel-btn {
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px 10px;
    color: @rjos-text;
    font-size: 13px;
    min-width: 0;
    transition: all 120ms ease;
}
.rjos-panel-btn:hover {
    background-color: @rjos-surface-hover;
    color: #FFFFFF;
}
.rjos-panel-btn:active {
    background-color: @rjos-surface-active;
}

/* Relógio */
.rjos-clock {
    color: @rjos-text;
    font-size: 13px;
    font-weight: 500;
    padding: 0 8px;
}

/* Ícones de Status / Tray */
.rjos-status-icon {
    color: @rjos-subtext;
    font-size: 14px;
    padding: 4px 6px;
    border-radius: 6px;
    transition: all 120ms ease;
}
.rjos-status-icon:hover {
    color: #FFFFFF;
    background-color: @rjos-surface-hover;
}

/* ══════════════════════════════════════════════════════════════════
   Launcher (Menu de Aplicativos)
   ══════════════════════════════════════════════════════════════════ */

.rjos-launcher {
    background-color: #1E1E1E;
    border: 1px solid @rjos-border;
    border-radius: 12px;
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.8);
    min-width: 640px;
    min-height: 480px;
}

.rjos-launcher-main {
    padding: 16px;
}

.rjos-launcher-sidebar {
    background-color: #161616;
    border-right: 1px solid @rjos-border;
    padding: 12px 8px;
    min-width: 140px;
    border-top-left-radius: 12px;
    border-bottom-left-radius: 12px;
}

.rjos-launcher-cat-btn {
    background: transparent;
    border: none;
    border-radius: 6px;
    color: @rjos-subtext;
    padding: 8px 12px;
    font-size: 13px;
    font-weight: 500;
    transition: all 100ms ease;
}

.rjos-launcher-cat-btn:hover {
    background-color: @rjos-surface-hover;
    color: @rjos-text;
}

.rjos-launcher-cat-btn-active {
    background-color: @rjos-blue-dim;
    color: #FFFFFF;
    border-left: 3px solid @rjos-blue;
    font-weight: 600;
}

.rjos-workspace-btn {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    color: @rjos-subtext;
    min-width: 26px;
    min-height: 26px;
    font-size: 12px;
    padding: 0 8px;
    transition: all 100ms ease;
}

.rjos-workspace-btn:hover {
    background-color: @rjos-surface-hover;
    color: @rjos-text;
}

.rjos-workspace-btn-active {
    background-color: @rjos-blue;
    border-color: @rjos-blue;
    color: #FFFFFF;
    font-weight: 600;
}

.rjos-launcher-search {
    background-color: #161616;
    border: 1px solid @rjos-border;
    border-radius: 8px;
    color: @rjos-text;
    font-size: 14px;
    padding: 10px 14px;
    margin-bottom: 12px;
    transition: all 120ms ease;
}
.rjos-launcher-search:focus {
    border-color: @rjos-blue;
    box-shadow: 0 0 0 2px @rjos-blue-dim;
    outline: none;
}

.rjos-app-grid {
    padding: 4px;
}

.rjos-app-btn {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 12px 8px;
    color: @rjos-text;
    font-size: 11px;
    transition: all 120ms ease;
    min-width: 80px;
}
.rjos-app-btn:hover {
    background-color: @rjos-surface-hover;
    border-color: @rjos-border;
    color: #FFFFFF;
}
.rjos-app-btn:active {
    background-color: @rjos-blue-dim;
    border-color: @rjos-blue;
    transform: scale(0.97);
}

.rjos-app-icon {
    font-size: 32px;
    margin-bottom: 4px;
}

.rjos-app-name {
    font-size: 11px;
    color: @rjos-subtext;
}

/* ══════════════════════════════════════════════════════════════════
   Notificações e Hierarquia Visual
   ══════════════════════════════════════════════════════════════════ */

.rjos-notification {
    background-color: #1E1E1E;
    border: 1px solid @rjos-border;
    border-left: 4px solid @rjos-blue;
    border-radius: 10px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.7);
    padding: 12px 16px;
    margin: 4px;
    min-width: 320px;
    max-width: 400px;
}

.rjos-notification-info {
    border-left-color: @rjos-blue;
}

.rjos-notification-success {
    border-left-color: @rjos-green;
}

.rjos-notification-warning {
    border-left-color: @rjos-yellow;
}

.rjos-notification-error {
    border-left-color: @rjos-error;
}

.rjos-notification-title {
    color: @rjos-text;
    font-weight: 600;
    font-size: 13px;
}
.rjos-notification-body {
    color: @rjos-subtext;
    font-size: 12px;
    margin-top: 3px;
}

/* ══════════════════════════════════════════════════════════════════
   Wallpaper overlay
   ══════════════════════════════════════════════════════════════════ */

.rjos-desktop-overlay {
    background: transparent;
}
"""

# ─── Lista de apps padrão do launcher ────────────────────────────────────────
DEFAULT_APPS = [
    {"name": "Terminal",    "icon": "🖥️",  "cmd": "rjos-terminal", "category": "Sistema"},
    {"name": "Arquivos",    "icon": "📁",  "cmd": "rjos-files", "category": "Sistema"},
    {"name": "Navegador",   "icon": "🌐",  "cmd": "firefox || chromium", "category": "Internet"},
    {"name": "Configurações","icon": "⚙️", "cmd": "rjos-settings", "category": "Sistema"},
    {"name": "App Store",   "icon": "🏪",  "cmd": "rjos-store", "category": "Sistema"},
    {"name": "Editor",      "icon": "📝",  "cmd": "gedit || mousepad || nano", "category": "Utilitários"},
    {"name": "Música",      "icon": "🎵",  "cmd": "rhythmbox || elisa", "category": "Mídia"},
    {"name": "Imagens",     "icon": "🖼️",  "cmd": "eog || gthumb", "category": "Mídia"},
    {"name": "Vídeo",       "icon": "🎬",  "cmd": "mpv || vlc", "category": "Mídia"},
    {"name": "Rede",        "icon": "📶",  "cmd": "nm-connection-editor", "category": "Internet"},
    {"name": "Monitor",     "icon": "📊",  "cmd": "gnome-system-monitor || htop", "category": "Sistema"},
    {"name": "Calculadora", "icon": "🧮",  "cmd": "gnome-calculator || bc", "category": "Utilitários"},
]

# ─── Painel Superior ──────────────────────────────────────────────────────────

class RjosPanel(Gtk.Window):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.launcher_visible = False
        self.launcher_window  = None
        self.quick_settings_window = None

        self._setup_window()
        self._build_ui()
        self._start_clock()
        self._start_status_updates()

    def _setup_window(self):
        self.set_decorated(False)
        self.set_resizable(False)
        self.add_css_class("rjos-panel")

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_exclusive_zone(self, 38)
            GtkLayerShell.set_namespace(self, "rjos-panel")

    def _build_ui(self):
        # Container principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.set_hexpand(True)

        # ── Esquerda: Logo ──
        left_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        left_box.add_css_class("rjos-panel-left")

        logo_btn = Gtk.Button(label="RJOS")
        logo_btn.add_css_class("rjos-logo-btn")
        logo_btn.connect("clicked", self._on_logo_clicked)
        left_box.append(logo_btn)

        # ── Centro: Workspace / Contexto ──
        center_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        center_box.set_hexpand(True)
        center_box.set_halign(Gtk.Align.CENTER)

        self.workspace_label = Gtk.Label(label="Área de trabalho 1")
        self.workspace_label.add_css_class("rjos-clock") # Reutilizando a classe de texto em negrito
        center_box.append(self.workspace_label)

        # ── Direita: Status (Bluetooth, Rede, Áudio, Bateria, Notif, Relógio) ──
        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        right_box.add_css_class("rjos-panel-right")
        right_box.set_halign(Gtk.Align.END)

        # Bluetooth
        self.bt_label = Gtk.Label(label="ᛒ")
        self.bt_label.add_css_class("rjos-status-icon")
        right_box.append(self.bt_label)

        # Rede
        self.net_label = Gtk.Label(label="🌐")
        self.net_label.add_css_class("rjos-status-icon")
        right_box.append(self.net_label)

        # Volume
        vol_btn = Gtk.Button(label="🔊")
        vol_btn.add_css_class("rjos-status-icon")
        vol_btn.set_tooltip_text("Áudio")
        vol_btn.connect("clicked", self._on_volume_clicked)
        right_box.append(vol_btn)

        # Bateria
        self.battery_label = Gtk.Label(label="🔋")
        self.battery_label.add_css_class("rjos-status-icon")
        right_box.append(self.battery_label)

        # Notificações
        notif_btn = Gtk.Button(label="🔔")
        notif_btn.add_css_class("rjos-status-icon")
        notif_btn.set_tooltip_text("Notificações")
        right_box.append(notif_btn)

        # Relógio
        self.clock_label = Gtk.Label(label="00:00")
        self.clock_label.add_css_class("rjos-clock")
        self.clock_label.set_margin_start(8)
        self.clock_label.set_margin_end(8)
        right_box.append(self.clock_label)

        # Usuário / Power (opcional, mantido por usabilidade)
        power_btn = Gtk.Button(label="⏻")
        power_btn.add_css_class("rjos-panel-btn")
        power_btn.set_tooltip_text("Energia")
        power_btn.connect("clicked", self._on_power_clicked)
        right_box.append(power_btn)

        # Monta layout
        main_box.append(left_box)
        main_box.append(center_box)
        main_box.append(right_box)

        self.set_child(main_box)

    def _start_clock(self):
        self._update_clock()
        # Atualiza a cada segundo
        GLib.timeout_add_seconds(1, self._update_clock)

    def _update_clock(self):
        now = datetime.now()
        self.clock_label.set_text(now.strftime("%H:%M"))
        return True  # continua o timeout

    def _start_status_updates(self):
        # Atualiza status a cada 5 segundos
        GLib.timeout_add_seconds(5, self._update_status)
        self._update_status()

    def _update_status(self):
        threading.Thread(target=self._check_network, daemon=True).start()
        threading.Thread(target=self._check_battery, daemon=True).start()
        return True

    def _check_network(self):
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "STATE", "general"],
                capture_output=True, text=True, timeout=3
            )
            connected = "connected" in result.stdout.lower()
            icon = "🌐" if connected else "⛔"
            GLib.idle_add(self.net_label.set_text, icon)
        except Exception:
            pass

    def _check_battery(self):
        try:
            bat_path = Path("/sys/class/power_supply/BAT0/capacity")
            charging_path = Path("/sys/class/power_supply/BAT0/status")
            if bat_path.exists():
                cap = int(bat_path.read_text().strip())
                status = charging_path.read_text().strip()
                if status == "Charging":
                    icon = f"⚡{cap}%"
                elif cap >= 75:
                    icon = f"🔋{cap}%"
                elif cap >= 30:
                    icon = f"🔋{cap}%"
                else:
                    icon = f"🪫{cap}%"
                GLib.idle_add(self.battery_label.set_text, icon)
            else:
                # Sem bateria (desktop/VM)
                GLib.idle_add(self.battery_label.set_text, "🔌")
        except Exception:
            pass

    def _on_logo_clicked(self, btn):
        if self.launcher_window and self.launcher_window.get_visible():
            self.launcher_window.hide()
        else:
            if not self.launcher_window:
                self.launcher_window = RjosLauncher(self.app)
            self.launcher_window.show()
            self.launcher_window.focus_search()

    def _on_volume_clicked(self, btn):
        """Abre painel de Quick Settings"""
        if HAS_QUICK_SETTINGS:
            if self.quick_settings_window and self.quick_settings_window.get_visible():
                self.quick_settings_window.close()
                self.quick_settings_window = None
            else:
                self.quick_settings_window = RjosQuickSettings(self)
                self.quick_settings_window.present()
        else:
            subprocess.Popen(["pavucontrol"], start_new_session=True)

    def _on_power_clicked(self, btn):
        dialog = RjosPowerDialog(self)
        dialog.present()


# ─── Launcher (App Menu) ──────────────────────────────────────────────────────

class RjosLauncher(Gtk.Window):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.all_apps = DEFAULT_APPS.copy()
        self._load_desktop_apps()

        self.set_decorated(False)
        self.set_resizable(False)

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 42)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, 12)
            GtkLayerShell.set_keyboard_mode(self,
                GtkLayerShell.KeyboardMode.EXCLUSIVE)

        self._build_ui()

        # Fecha ao pressionar Escape
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctrl)

    def _load_desktop_apps(self):
        """Carrega apps de arquivos .desktop do sistema"""
        desktop_dirs = [
            Path("/usr/share/applications"),
            Path.home() / ".local/share/applications",
        ]
        for d in desktop_dirs:
            if d.exists():
                for f in d.glob("*.desktop"):
                    try:
                        self._parse_desktop_file(f)
                    except Exception:
                        pass

    def _parse_desktop_file(self, path):
        name = exec_cmd = icon = categories = ""
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("Name=") and not name:
                    name = line[5:]
                elif line.startswith("Exec="):
                    exec_cmd = line[5:].replace("%u", "").replace("%f", "").strip()
                elif line.startswith("Icon="):
                    icon = line[5:]
                elif line.startswith("Categories="):
                    categories = line[11:]
                elif line == "NoDisplay=true":
                    return
        if name and exec_cmd:
            cat = "Outros"
            if "Network" in categories or "WebBrowser" in categories: cat = "Internet"
            elif "Audio" in categories or "Video" in categories: cat = "Mídia"
            elif "System" in categories or "Settings" in categories: cat = "Sistema"
            elif "Utility" in categories: cat = "Utilitários"

            if not any(a["name"] == name for a in self.all_apps):
                self.all_apps.append({
                    "name": name,
                    "icon": "📦",
                    "cmd": exec_cmd,
                    "category": cat
                })

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        main_box.add_css_class("rjos-launcher")

        # Sidebar
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sidebar.add_css_class("rjos-launcher-sidebar")
        
        self.cat_buttons = {}
        cats = ["Todos", "Favoritos", "Sistema", "Internet", "Mídia", "Utilitários", "Outros"]
        for cat in cats:
            btn = Gtk.Button(label=cat)
            btn.add_css_class("rjos-launcher-cat-btn")
            if cat == "Todos":
                btn.add_css_class("rjos-launcher-cat-btn-active")
            btn.connect("clicked", self._on_category_clicked, cat)
            sidebar.append(btn)
            self.cat_buttons[cat] = btn
        
        main_box.append(sidebar)

        # Área principal
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.add_css_class("rjos-launcher-main")
        outer.set_hexpand(True)

        # Pesquisa
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Pesquisar aplicativo...")
        self.search_entry.add_css_class("rjos-launcher-search")
        self.search_entry.connect("search-changed", self._on_search_changed)
        outer.append(self.search_entry)

        # Grid de apps (scrollável)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        self.flow = Gtk.FlowBox()
        self.flow.set_max_children_per_line(5)
        self.flow.set_min_children_per_line(3)
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_homogeneous(True)
        self.flow.add_css_class("rjos-app-grid")
        self.flow.connect("child-activated", self._on_app_activated)

        scroll.set_child(self.flow)
        outer.append(scroll)

        main_box.append(outer)
        self.set_child(main_box)
        self.active_category = "Todos"
        self._populate_apps(self.all_apps)

    def _on_category_clicked(self, btn, cat):
        for c, b in self.cat_buttons.items():
            b.remove_css_class("rjos-launcher-cat-btn-active")
        btn.add_css_class("rjos-launcher-cat-btn-active")
        self.active_category = cat
        self._filter_apps()

    def _populate_apps(self, apps):
        # Remove filhos existentes
        child = self.flow.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.flow.remove(child)
            child = next_child

        for app_data in apps[:40]:  # máximo 40 apps exibidos
            btn = Gtk.Button()
            btn.add_css_class("rjos-app-btn")
            btn._app_cmd = app_data["cmd"]

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            vbox.set_halign(Gtk.Align.CENTER)

            icon_lbl = Gtk.Label(label=app_data["icon"])
            icon_lbl.add_css_class("rjos-app-icon")
            vbox.append(icon_lbl)

            name_lbl = Gtk.Label(label=app_data["name"][:12])
            name_lbl.add_css_class("rjos-app-name")
            vbox.append(name_lbl)

            btn.set_child(vbox)
            # Como btn é filho de FlowBox, _on_app_activated lida com o click
            
            self.flow.append(btn)

    def _on_search_changed(self, entry):
        self._filter_apps()

    def _filter_apps(self):
        query = self.search_entry.get_text().lower().strip()
        filtered = self.all_apps
        
        if self.active_category == "Favoritos":
            # Para simplificar, favoritos são os primeiros 10
            filtered = self.all_apps[:10]
        elif self.active_category != "Todos":
            filtered = [a for a in self.all_apps if a.get("category") == self.active_category]
            
        if query:
            filtered = [a for a in filtered if query in a["name"].lower()]
            
        self._populate_apps(filtered)

    def _launch_app(self, btn, cmd):
        self.hide()
        subprocess.Popen(
            ["/bin/sh", "-c", cmd],
            start_new_session=True,
            env={**os.environ}
        )

    def _on_app_activated(self, flow, child):
        # Suporte a ativação por teclado
        pass

    def _on_key_pressed(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        return False

    def focus_search(self):
        self.search_entry.grab_focus()
        self.search_entry.set_text("")


# ─── Power Dialog ─────────────────────────────────────────────────────────────

class RjosPowerDialog(Gtk.Window):
    ACTIONS = [
        ("🔒 Bloquear",    "loginctl lock-session"),
        ("↩️ Sair",        "loginctl terminate-user $USER"),
        ("🔄 Reiniciar",   "systemctl reboot"),
        ("⏸️ Suspender",   "systemctl suspend"),
        ("⏻ Desligar",     "systemctl poweroff"),
    ]

    def __init__(self, parent):
        super().__init__()
        self.set_decorated(False)
        self.set_transient_for(parent)
        self.set_modal(True)

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 42)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 12)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        title = Gtk.Label(label="Energia")
        title.add_css_class("rjos-clock")
        title.set_halign(Gtk.Align.CENTER)
        title.set_margin_bottom(8)
        box.append(title)

        for label, cmd in self.ACTIONS:
            btn = Gtk.Button(label=label)
            btn.add_css_class("rjos-panel-btn")
            btn.set_halign(Gtk.Align.FILL)
            btn.connect("clicked", self._do_action, cmd)
            box.append(btn)

        cancel = Gtk.Button(label="✕ Cancelar")
        cancel.add_css_class("rjos-panel-btn")
        cancel.connect("clicked", lambda _: self.close())
        cancel.set_margin_top(4)
        box.append(cancel)

        frame = Gtk.Frame()
        frame.add_css_class("rjos-launcher")
        frame.set_child(box)
        self.set_child(frame)

        # Fecha com Escape
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", lambda c, k, *a:
                         self.close() or True if k == Gdk.KEY_Escape else False)
        self.add_controller(key_ctrl)

    def _do_action(self, btn, cmd):
        self.close()
        subprocess.Popen(["/bin/sh", "-c", cmd], start_new_session=True)


# ─── Aplicação principal ──────────────────────────────────────────────────────

class RjosShellApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="org.rjos.shell",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.panel = None
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        # Carrega CSS
        provider = Gtk.CssProvider()
        provider.load_from_string(RJOS_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Cria e mostra painel
        self.panel = RjosPanel(self)
        self.panel.present()

        # Configura wallpaper via swaybg ou feh
        self._set_wallpaper()

        # Inicia serviços de desktop
        self._start_desktop_services()

    def _set_wallpaper(self):
        """Define o wallpaper usando swaybg (Wayland)"""
        local_wp = str(Path(__file__).resolve().parent.parent / "wallpapers" / "rjos-pao-de-acucar.svg")
        wallpaper_paths = [
            "/usr/share/rjos/wallpapers/default.svg",
            "/usr/share/rjos/wallpapers/rjos-pao-de-acucar.svg",
            local_wp,
            "/usr/share/rjos/wallpapers/default.jpg",
            "/usr/share/rjos/wallpapers/default.png",
            os.path.expanduser("~/.config/rjos/wallpaper"),
        ]

        wallpaper = None
        for p in wallpaper_paths:
            if os.path.exists(p):
                wallpaper = p
                break

        if wallpaper:
            subprocess.Popen(
                ["swaybg", "-i", wallpaper, "-m", "fill"],
                start_new_session=True
            )
        else:
            # Sem wallpaper: usa cor sólida oficial Carvão (#121212)
            subprocess.Popen(
                ["swaybg", "-c", "#121212"],
                start_new_session=True
            )

    def _start_desktop_services(self):
        """Inicia serviços de suporte do desktop"""
        services = [
            # Gerenciador de clipboard
            "wl-paste --watch cliphist store",
            # Notificações (mako é leve e Wayland-nativo)
            "mako",
            # Dock do RJOS
            "rjos-dock",
        ]
        for svc in services:
            subprocess.Popen(
                ["/bin/sh", "-c", svc],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )


def main():
    # Verifica WAYLAND_DISPLAY
    if not os.environ.get("WAYLAND_DISPLAY"):
        print("[ERROR] WAYLAND_DISPLAY não definido.")
        print("Execute o compositor primeiro: rjos-compositor")
        sys.exit(1)

    app = RjosShellApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
