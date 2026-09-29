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

# Tenta importar gtk4-layer-shell
try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except (ValueError, ImportError):
    HAS_LAYER_SHELL = False
    print("[WARN] gtk4-layer-shell não disponível. Painel sem ancoragem.")

# ─── Paleta RJOS ─────────────────────────────────────────────────────────────
RJOS_CSS = """
/* ══════════════════════════════════════════════════════════════════
   RJOS Design System — Tokens
   ══════════════════════════════════════════════════════════════════ */

@define-color rjos-bg-deep      #0D1B2A;
@define-color rjos-bg-dark      #1B2838;
@define-color rjos-surface      #1E2D40;
@define-color rjos-surface-2    #243347;
@define-color rjos-border       #2A3F58;
@define-color rjos-cyan         #00D4FF;
@define-color rjos-cyan-dim     rgba(0, 212, 255, 0.15);
@define-color rjos-purple       #7B2FBE;
@define-color rjos-text         #E8F4FD;
@define-color rjos-subtext      #8BA7BF;
@define-color rjos-success      #00E676;
@define-color rjos-warning      #FFB300;
@define-color rjos-error        #FF3D71;

/* ══════════════════════════════════════════════════════════════════
   Panel / Topbar
   ══════════════════════════════════════════════════════════════════ */

.rjos-panel {
    background-color: rgba(13, 27, 42, 0.92);
    border-bottom: 1px solid @rjos-border;
    box-shadow: 0 2px 16px rgba(0, 0, 0, 0.5);
    padding: 0;
    min-height: 38px;
}

.rjos-panel-left,
.rjos-panel-center,
.rjos-panel-right {
    padding: 0 8px;
}

/* Logo/distro button */
.rjos-logo-btn {
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px 10px;
    color: @rjos-cyan;
    font-weight: 800;
    font-size: 13px;
    letter-spacing: 2px;
    transition: all 150ms ease;
}
.rjos-logo-btn:hover {
    background-color: @rjos-cyan-dim;
    box-shadow: 0 0 12px rgba(0, 212, 255, 0.3);
}

/* Botões do painel */
.rjos-panel-btn {
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px 8px;
    color: @rjos-text;
    font-size: 13px;
    min-width: 0;
    transition: all 150ms ease;
}
.rjos-panel-btn:hover {
    background-color: @rjos-cyan-dim;
    color: @rjos-cyan;
}

/* Relógio */
.rjos-clock {
    color: @rjos-text;
    font-size: 13px;
    font-weight: 500;
    padding: 0 8px;
}

/* Status icons */
.rjos-status-icon {
    color: @rjos-subtext;
    font-size: 14px;
    padding: 4px 4px;
    border-radius: 4px;
    transition: all 150ms ease;
}
.rjos-status-icon:hover {
    color: @rjos-cyan;
    background-color: @rjos-cyan-dim;
}

/* ══════════════════════════════════════════════════════════════════
   Launcher (App Menu)
   ══════════════════════════════════════════════════════════════════ */

.rjos-launcher {
    background-color: rgba(13, 27, 42, 0.97);
    border: 1px solid @rjos-border;
    border-radius: 12px;
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(0, 212, 255, 0.1);
    padding: 16px;
    min-width: 480px;
    min-height: 400px;
}

.rjos-launcher-search {
    background-color: @rjos-surface;
    border: 1px solid @rjos-border;
    border-radius: 8px;
    color: @rjos-text;
    font-size: 15px;
    padding: 10px 14px;
    margin-bottom: 12px;
    transition: all 200ms ease;
}
.rjos-launcher-search:focus {
    border-color: @rjos-cyan;
    box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.2);
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
    transition: all 180ms ease;
    min-width: 80px;
}
.rjos-app-btn:hover {
    background-color: @rjos-surface;
    border-color: @rjos-border;
    color: @rjos-cyan;
}
.rjos-app-btn:active {
    background-color: @rjos-cyan-dim;
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
   Notificações
   ══════════════════════════════════════════════════════════════════ */

.rjos-notification {
    background-color: rgba(30, 45, 64, 0.97);
    border: 1px solid @rjos-border;
    border-left: 3px solid @rjos-cyan;
    border-radius: 10px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    padding: 12px 16px;
    margin: 4px;
    min-width: 320px;
    max-width: 400px;
    animation: slide-in 250ms ease-out;
}

@keyframes slide-in {
    from { opacity: 0; transform: translateX(20px); }
    to   { opacity: 1; transform: translateX(0); }
}

.rjos-notification-title {
    color: @rjos-text;
    font-weight: 600;
    font-size: 13px;
}
.rjos-notification-body {
    color: @rjos-subtext;
    font-size: 12px;
    margin-top: 2px;
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
    {"name": "Terminal",    "icon": "🖥️",  "cmd": "rjos-terminal"},
    {"name": "Arquivos",    "icon": "📁",  "cmd": "rjos-files"},
    {"name": "Navegador",   "icon": "🌐",  "cmd": "firefox || chromium"},
    {"name": "Configurações","icon": "⚙️", "cmd": "rjos-settings"},
    {"name": "App Store",   "icon": "🏪",  "cmd": "rjos-store"},
    {"name": "Editor",      "icon": "📝",  "cmd": "gedit || mousepad || nano"},
    {"name": "Música",      "icon": "🎵",  "cmd": "rhythmbox || elisa"},
    {"name": "Imagens",     "icon": "🖼️",  "cmd": "eog || gthumb"},
    {"name": "Vídeo",       "icon": "🎬",  "cmd": "mpv || vlc"},
    {"name": "Rede",        "icon": "📶",  "cmd": "nm-connection-editor"},
    {"name": "Monitor",     "icon": "📊",  "cmd": "gnome-system-monitor || htop"},
    {"name": "Calculadora", "icon": "🧮",  "cmd": "gnome-calculator || bc"},
]

# ─── Painel Superior ──────────────────────────────────────────────────────────

class RjosPanel(Gtk.Window):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.launcher_visible = False
        self.launcher_window  = None

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

        # ── Esquerda: Logo + Apps abertos ──
        left_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        left_box.add_css_class("rjos-panel-left")

        logo_btn = Gtk.Button(label="RJOS")
        logo_btn.add_css_class("rjos-logo-btn")
        logo_btn.connect("clicked", self._on_logo_clicked)
        left_box.append(logo_btn)

        # Separador
        sep1 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep1.set_margin_top(8)
        sep1.set_margin_bottom(8)
        sep1.set_margin_start(4)
        sep1.set_margin_end(4)
        left_box.append(sep1)

        # Menu Atividades
        activities_btn = Gtk.Button(label="Atividades")
        activities_btn.add_css_class("rjos-panel-btn")
        activities_btn.connect("clicked", self._on_logo_clicked)
        left_box.append(activities_btn)

        # ── Centro: Relógio ──
        center_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        center_box.set_hexpand(True)
        center_box.set_halign(Gtk.Align.CENTER)

        self.clock_label = Gtk.Label(label="00:00")
        self.clock_label.add_css_class("rjos-clock")

        self.date_label = Gtk.Label(label="")
        self.date_label.add_css_class("rjos-status-icon")
        self.date_label.set_margin_start(8)

        center_box.append(self.clock_label)
        center_box.append(self.date_label)

        # ── Direita: Status ──
        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        right_box.add_css_class("rjos-panel-right")
        right_box.set_halign(Gtk.Align.END)

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

        # Usuário / Power
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
        self.date_label.set_text(now.strftime("%a, %d %b"))
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
        name = exec_cmd = icon = ""
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("Name=") and not name:
                    name = line[5:]
                elif line.startswith("Exec="):
                    exec_cmd = line[5:].replace("%u", "").replace("%f", "").strip()
                elif line.startswith("Icon="):
                    icon = line[5:]
                elif line == "NoDisplay=true":
                    return
        if name and exec_cmd:
            # Evita duplicatas
            if not any(a["name"] == name for a in self.all_apps):
                self.all_apps.append({
                    "name": name,
                    "icon": "📦",
                    "cmd": exec_cmd,
                })

    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.add_css_class("rjos-launcher")

        # Título
        title = Gtk.Label(label="Aplicativos")
        title.set_halign(Gtk.Align.START)
        title.add_css_class("rjos-clock")
        title.set_margin_bottom(8)
        outer.append(title)

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

        self.set_child(outer)
        self._populate_apps(self.all_apps)

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
            btn.connect("clicked", self._launch_app, app_data["cmd"])

            self.flow.append(btn)

    def _on_search_changed(self, entry):
        query = entry.get_text().lower().strip()
        if not query:
            self._populate_apps(self.all_apps)
        else:
            filtered = [a for a in self.all_apps
                        if query in a["name"].lower()]
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
        wallpaper_paths = [
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
            # Sem wallpaper: usa cor sólida
            subprocess.Popen(
                ["swaybg", "-c", "#0D1B2A"],
                start_new_session=True
            )

    def _start_desktop_services(self):
        """Inicia serviços de suporte do desktop"""
        services = [
            # Gerenciador de clipboard
            "wl-paste --watch cliphist store",
            # Notificações (mako é leve e Wayland-nativo)
            "mako",
            # Atalhos globais via wl-clipboard
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
