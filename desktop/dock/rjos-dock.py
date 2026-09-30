#!/usr/bin/env python3
# =============================================================================
# RJOS Dock — rjos-dock.py
# Dock inferior do RJOS: barra de aplicativos com efeito de magnificação
#
# Usa GTK4 + gtk4-layer-shell para ancorar na parte inferior da tela
# Usa Wayland nativo (WAYLAND_DISPLAY deve estar setado pelo compositor)
#
# Features:
#   - Apps fixados (pinned) + apps em execução
#   - Efeito de magnificação ao hover (estilo macOS)
#   - Indicador de app ativo (ponto luminoso cyan)
#   - Animação bounce ao lançar apps
#   - Menu de contexto (clique direito)
#   - Separador visual entre fixados e em execução
#
# Dependências:
#   python3-gi (PyGObject), gir1.2-gtk-4.0, gir1.2-adw-1
#   gtk4-layer-shell (libgtk4-layer-shell)
# =============================================================================

import gi
import os
import sys
import subprocess
import json
import math
import time
from pathlib import Path

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gdk, Gio

# Tenta importar gtk4-layer-shell
try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except (ValueError, ImportError):
    HAS_LAYER_SHELL = False
    print("[WARN] gtk4-layer-shell não disponível. Dock sem ancoragem.")

# ─── Configurações do Dock ────────────────────────────────────────────────────

DOCK_ICON_SIZE     = 48       # Tamanho normal do ícone (px)
DOCK_ICON_SIZE_MAX = 72       # Tamanho máximo com magnificação (px)
DOCK_MAGNIFY_RANGE = 3        # Número de ícones afetados pela magnificação
DOCK_PADDING       = 8        # Padding interno do dock
DOCK_MARGIN_BOTTOM = 8        # Margem inferior da tela
DOCK_SPACING       = 4        # Espaçamento entre ícones
DOCK_ANIM_FPS      = 60       # FPS da animação

# Caminho do arquivo de configuração dos apps fixados
DOCK_CONFIG_PATH = Path.home() / ".config" / "rjos" / "dock.json"

# ─── Paleta CSS ───────────────────────────────────────────────────────────────

DOCK_CSS = """
/* ══════════════════════════════════════════════════════════════════
   RJOS Dock — Estilos Oficiais RJOS
   ══════════════════════════════════════════════════════════════════ */

.rjos-dock-window {
    background: transparent;
}

.rjos-dock-container {
    background-color: rgba(30, 30, 30, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.7);
    padding: 6px 10px;
    margin: 0 auto;
}

.rjos-dock-item {
    background: transparent;
    border: none;
    border-radius: 12px;
    padding: 4px;
    min-width: 0;
    min-height: 0;
    transition: background-color 120ms ease;
}

.rjos-dock-item:hover {
    background-color: #292929;
}

.rjos-dock-item:active {
    background-color: rgba(0, 91, 150, 0.35);
}

/* Ícone do app no dock */
.rjos-dock-icon {
    font-size: 32px;
    transition: all 120ms ease;
}

/* Label do tooltip */
.rjos-dock-tooltip {
    background-color: #1E1E1E;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6);
    padding: 6px 12px;
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 500;
}

/* Indicador de app ativo (ponto Azul Oceano) */
.rjos-dock-indicator {
    min-width: 5px;
    min-height: 5px;
    border-radius: 50%;
    background-color: #005B96;
    box-shadow: 0 0 6px rgba(0, 91, 150, 0.8);
    margin-top: 2px;
}

.rjos-dock-indicator-inactive {
    min-width: 5px;
    min-height: 5px;
    border-radius: 50%;
    background: transparent;
    margin-top: 2px;
}

/* Separador entre fixados e abertos */
.rjos-dock-separator {
    background-color: rgba(255, 255, 255, 0.08);
    min-width: 1px;
    min-height: 32px;
    margin: 8px 6px;
    border-radius: 1px;
}

/* Animação suave de bounce ao abrir app */
@keyframes dock-bounce {
    0%   { transform: translateY(0); }
    25%  { transform: translateY(-8px); }
    50%  { transform: translateY(0); }
    75%  { transform: translateY(-4px); }
    100% { transform: translateY(0); }
}

.rjos-dock-bounce {
    animation: dock-bounce 400ms ease;
}

/* Menu de contexto do dock */
.rjos-dock-context-menu {
    background-color: #1E1E1E;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.7);
    padding: 4px;
}

.rjos-dock-context-item {
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 400;
    min-width: 140px;
    transition: all 100ms ease;
}

.rjos-dock-context-item:hover {
    background-color: #292929;
    color: #FFFFFF;
}

.rjos-dock-context-separator {
    background-color: rgba(255, 255, 255, 0.08);
    min-height: 1px;
    margin: 3px 6px;
}
"""

# ─── Apps padrão fixados no dock ──────────────────────────────────────────────

DEFAULT_PINNED_APPS = [
    {
        "id": "rjos-files",
        "name": "Arquivos",
        "icon": "📁",
        "cmd": "rjos-files",
        "desktop": "rjos-files.desktop",
    },
    {
        "id": "rjos-terminal",
        "name": "Terminal",
        "icon": "🖥️",
        "cmd": "rjos-terminal || foot || alacritty || xterm",
        "desktop": "rjos-terminal.desktop",
    },
    {
        "id": "firefox",
        "name": "Navegador",
        "icon": "🌐",
        "cmd": "firefox || chromium || chromium-browser",
        "desktop": "firefox.desktop",
    },
    {
        "id": "rjos-settings",
        "name": "Configurações",
        "icon": "⚙️",
        "cmd": "rjos-settings",
        "desktop": "rjos-settings.desktop",
    },
    {
        "id": "rjos-store",
        "name": "App Store",
        "icon": "🏪",
        "cmd": "rjos-store",
        "desktop": "rjos-store.desktop",
    },
    {
        "id": "editor",
        "name": "Editor de Texto",
        "icon": "📝",
        "cmd": "gedit || mousepad || xed",
        "desktop": "org.gnome.TextEditor.desktop",
    },
    {
        "id": "music",
        "name": "Música",
        "icon": "🎵",
        "cmd": "rhythmbox || elisa || lollypop",
        "desktop": "org.gnome.Rhythmbox3.desktop",
    },
]


# ─── Gerenciamento de configuração ────────────────────────────────────────────

def load_dock_config():
    """Carrega apps fixados do arquivo de configuração"""
    try:
        if DOCK_CONFIG_PATH.exists():
            with open(DOCK_CONFIG_PATH, "r") as f:
                data = json.load(f)
                return data.get("pinned_apps", DEFAULT_PINNED_APPS)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[WARN] Erro ao carregar dock config: {e}")
    return DEFAULT_PINNED_APPS


def save_dock_config(pinned_apps):
    """Salva apps fixados no arquivo de configuração"""
    try:
        DOCK_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {"pinned_apps": pinned_apps}
        with open(DOCK_CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"[ERROR] Erro ao salvar dock config: {e}")


# ─── Dock Item (cada ícone no dock) ──────────────────────────────────────────

class DockItem:
    """Representa um item no dock (app fixado ou em execução)"""

    def __init__(self, app_data, pinned=True):
        self.app_data = app_data
        self.pinned = pinned
        self.running = False
        self.focused = False
        self.scale = 1.0        # Fator de magnificação atual
        self.target_scale = 1.0
        self.bouncing = False

    @property
    def app_id(self):
        return self.app_data.get("id", "unknown")

    @property
    def name(self):
        return self.app_data.get("name", "App")

    @property
    def icon(self):
        return self.app_data.get("icon", "📦")

    @property
    def cmd(self):
        return self.app_data.get("cmd", "")


# ─── Dock Widget Principal ───────────────────────────────────────────────────

class RjosDock(Gtk.Window):
    """Dock principal do RJOS Desktop"""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.items = []
        self.context_menu = None
        self.tooltip_window = None
        self._hover_index = -1
        self._magnify_active = False

        self._setup_window()
        self._load_items()
        self._build_ui()
        self._start_running_apps_monitor()

    # ── Configuração da janela ──

    def _setup_window(self):
        self.set_decorated(False)
        self.set_resizable(False)
        self.add_css_class("rjos-dock-window")

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, True)
            # NÃO ancora esquerda/direita — dock fica centralizado
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.BOTTOM,
                                     DOCK_MARGIN_BOTTOM)
            GtkLayerShell.set_exclusive_zone(self, -1)  # Não reserva espaço
            GtkLayerShell.set_namespace(self, "rjos-dock")

    # ── Carrega apps ──

    def _load_items(self):
        pinned_apps = load_dock_config()
        self.items = [DockItem(app, pinned=True) for app in pinned_apps]

    # ── Constrói UI ──

    def _build_ui(self):
        # Container principal com alinhamento central
        self.outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.outer_box.set_halign(Gtk.Align.CENTER)
        self.outer_box.set_valign(Gtk.Align.END)

        # Container do dock com background glass
        self.dock_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=DOCK_SPACING
        )
        self.dock_box.add_css_class("rjos-dock-container")

        # Motion controller para magnificação
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_motion)
        motion.connect("leave", self._on_leave)
        self.dock_box.add_controller(motion)

        self._rebuild_dock_items()

        self.outer_box.append(self.dock_box)
        self.set_child(self.outer_box)

    def _rebuild_dock_items(self):
        """Reconstrói todos os ícones do dock"""
        # Limpa dock
        child = self.dock_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.dock_box.remove(child)
            child = next_child

        # Adiciona items fixados
        has_pinned = False
        for i, item in enumerate(self.items):
            if item.pinned:
                self._add_dock_button(item, i)
                has_pinned = True

        # Separador se tem items fixados E em execução (não fixados)
        running_not_pinned = [it for it in self.items
                              if it.running and not it.pinned]
        if has_pinned and running_not_pinned:
            sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
            sep.add_css_class("rjos-dock-separator")
            self.dock_box.append(sep)

        # Adiciona items em execução (não fixados)
        for i, item in enumerate(self.items):
            if item.running and not item.pinned:
                self._add_dock_button(item, i)

    def _add_dock_button(self, item, index):
        """Cria um botão de ícone no dock"""
        # Container vertical: ícone + indicador
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        vbox.set_halign(Gtk.Align.CENTER)

        # Botão do ícone
        btn = Gtk.Button()
        btn.add_css_class("rjos-dock-item")
        btn.set_tooltip_text(item.name)

        icon_label = Gtk.Label(label=item.icon)
        icon_label.add_css_class("rjos-dock-icon")
        icon_label.set_name(f"dock-icon-{index}")

        # Define tamanho com CSS inline
        self._set_icon_size(icon_label, DOCK_ICON_SIZE)

        btn.set_child(icon_label)

        # Eventos
        btn.connect("clicked", self._on_item_clicked, item)

        # Clique direito (menu de contexto)
        gesture_click = Gtk.GestureClick()
        gesture_click.set_button(3)  # Botão direito
        gesture_click.connect("pressed", self._on_item_right_click, item)
        btn.add_controller(gesture_click)

        vbox.append(btn)

        # Indicador de ativo (ponto luminoso)
        indicator = Gtk.Box()
        if item.running:
            indicator.add_css_class("rjos-dock-indicator")
        else:
            indicator.add_css_class("rjos-dock-indicator-inactive")
        indicator.set_halign(Gtk.Align.CENTER)
        vbox.append(indicator)

        # Armazena referências para magnificação
        btn._dock_index = index
        btn._icon_label = icon_label
        btn._dock_item = item

        self.dock_box.append(vbox)

    def _set_icon_size(self, label, size):
        """Define o tamanho do ícone via CSS font-size"""
        font_size = max(16, int(size * 0.7))
        css = f"font-size: {font_size}px;"
        # Usa CSS provider por widget
        provider = Gtk.CssProvider()
        provider.load_from_string(f".rjos-dock-icon {{ {css} }}")
        # Nota: em produção, a magnificação usa widget_set_size_request
        label.set_size_request(int(size), int(size))

    # ── Efeito de Magnificação ──

    def _on_motion(self, controller, x, y):
        """Aplica efeito de magnificação baseado na posição do cursor"""
        self._magnify_active = True

        # Calcula qual ícone está mais próximo
        child = self.dock_box.get_first_child()
        index = 0
        while child:
            if isinstance(child, Gtk.Box):
                # Pega o botão dentro do vbox
                btn = child.get_first_child()
                if btn and isinstance(btn, Gtk.Button) and hasattr(btn, '_dock_index'):
                    alloc = child.get_allocation()
                    center_x = alloc.x + alloc.width / 2

                    # Distância normalizada (0 = em cima, 1 = longe)
                    dist = abs(x - center_x)
                    max_dist = (DOCK_ICON_SIZE + DOCK_SPACING) * DOCK_MAGNIFY_RANGE

                    if dist < max_dist:
                        # Curva de magnificação (cosseno suavizado)
                        factor = 1.0 - (dist / max_dist)
                        scale = 1.0 + factor * (
                            (DOCK_ICON_SIZE_MAX / DOCK_ICON_SIZE) - 1.0
                        )
                        scale = min(scale, DOCK_ICON_SIZE_MAX / DOCK_ICON_SIZE)
                    else:
                        scale = 1.0

                    new_size = int(DOCK_ICON_SIZE * scale)
                    icon_label = btn._icon_label
                    self._set_icon_size(icon_label, new_size)

                    index += 1
            child = child.get_next_sibling()

    def _on_leave(self, controller):
        """Remove efeito de magnificação ao sair do dock"""
        self._magnify_active = False
        self._reset_magnification()

    def _reset_magnification(self):
        """Restaura todos os ícones ao tamanho normal"""
        child = self.dock_box.get_first_child()
        while child:
            if isinstance(child, Gtk.Box):
                btn = child.get_first_child()
                if btn and isinstance(btn, Gtk.Button) and hasattr(btn, '_icon_label'):
                    self._set_icon_size(btn._icon_label, DOCK_ICON_SIZE)
            child = child.get_next_sibling()

    # ── Eventos ──

    def _on_item_clicked(self, btn, item):
        """Lança o app ou foca se já está aberto"""
        if item.running:
            # TODO: Focar janela existente via wlr-foreign-toplevel
            print(f"[dock] Focar: {item.name}")
        else:
            self._launch_app(item)

    def _launch_app(self, item):
        """Lança um aplicativo"""
        print(f"[dock] Lançando: {item.name} → {item.cmd}")

        subprocess.Popen(
            ["/bin/sh", "-c", item.cmd],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ}
        )

        # Marca como "abrindo" temporariamente (animação bounce)
        item.running = True
        self._rebuild_dock_items()

    def _on_item_right_click(self, gesture, n_press, x, y, item):
        """Menu de contexto ao clicar com botão direito"""
        if self.context_menu:
            self.context_menu.close()

        self.context_menu = RjosDockContextMenu(self, item)
        self.context_menu.present()

    # ── Monitoramento de apps em execução ──

    def _start_running_apps_monitor(self):
        """Monitora apps em execução periodicamente"""
        GLib.timeout_add_seconds(3, self._check_running_apps)
        self._check_running_apps()

    def _check_running_apps(self):
        """Verifica quais apps fixados estão em execução"""
        try:
            result = subprocess.run(
                ["ps", "-eo", "comm"],
                capture_output=True, text=True, timeout=2
            )
            running_procs = set(result.stdout.strip().split('\n'))

            changed = False
            for item in self.items:
                # Pega o primeiro comando (antes de ||)
                main_cmd = item.cmd.split("||")[0].strip().split("/")[-1].strip()
                was_running = item.running
                item.running = main_cmd in running_procs
                if was_running != item.running:
                    changed = True

            if changed:
                GLib.idle_add(self._rebuild_dock_items)

        except Exception as e:
            print(f"[dock] Erro ao verificar apps: {e}")

        return True  # Continua o timeout

    # ── API pública ──

    def pin_app(self, app_data):
        """Fixa um app no dock"""
        # Verifica se já está fixado
        if any(it.app_id == app_data.get("id") for it in self.items if it.pinned):
            return

        new_item = DockItem(app_data, pinned=True)
        self.items.append(new_item)
        self._rebuild_dock_items()
        self._save_pinned()

    def unpin_app(self, item):
        """Remove um app fixado do dock"""
        item.pinned = False
        if not item.running:
            self.items.remove(item)
        self._rebuild_dock_items()
        self._save_pinned()

    def _save_pinned(self):
        """Salva a lista de apps fixados"""
        pinned = [it.app_data for it in self.items if it.pinned]
        save_dock_config(pinned)


# ─── Menu de Contexto do Dock ─────────────────────────────────────────────────

class RjosDockContextMenu(Gtk.Window):
    """Menu de contexto para itens do dock"""

    def __init__(self, dock, item):
        super().__init__()
        self.dock = dock
        self.item = item

        self.set_decorated(False)
        self.set_resizable(False)
        self.set_transient_for(dock)
        self.set_modal(True)

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_keyboard_mode(
                self, GtkLayerShell.KeyboardMode.EXCLUSIVE
            )

        self._build_ui()

        # Fecha com Escape
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_key)
        self.add_controller(key_ctrl)

        # Fecha ao clicar fora
        focus_ctrl = Gtk.EventControllerFocus()
        focus_ctrl.connect("leave", lambda c: self.close())
        self.add_controller(focus_ctrl)

    def _build_ui(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.add_css_class("rjos-dock-context-menu")

        # Título do app
        title = Gtk.Label(label=f"{self.item.icon}  {self.item.name}")
        title.set_halign(Gtk.Align.START)
        title.set_margin_start(8)
        title.set_margin_top(4)
        title.set_margin_bottom(4)
        title.add_css_class("rjos-dock-context-item")
        box.append(title)

        # Separador
        sep = Gtk.Separator()
        sep.add_css_class("rjos-dock-context-separator")
        box.append(sep)

        # Nova janela
        if self.item.running:
            btn_new = self._make_menu_item("Nova Janela", self._on_new_window)
            box.append(btn_new)

        # Fixar/Desafixar
        if self.item.pinned:
            btn_pin = self._make_menu_item("Desafixar do Dock", self._on_unpin)
        else:
            btn_pin = self._make_menu_item("Fixar no Dock", self._on_pin)
        box.append(btn_pin)

        # Fechar (se em execução)
        if self.item.running:
            sep2 = Gtk.Separator()
            sep2.add_css_class("rjos-dock-context-separator")
            box.append(sep2)

            btn_close = self._make_menu_item("Fechar", self._on_close)
            box.append(btn_close)

        self.set_child(box)

    def _make_menu_item(self, label, callback):
        btn = Gtk.Button(label=label)
        btn.add_css_class("rjos-dock-context-item")
        btn.set_halign(Gtk.Align.FILL)
        btn.connect("clicked", callback)
        return btn

    def _on_new_window(self, btn):
        self.close()
        subprocess.Popen(
            ["/bin/sh", "-c", self.item.cmd],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _on_pin(self, btn):
        self.close()
        self.dock.pin_app(self.item.app_data)

    def _on_unpin(self, btn):
        self.close()
        self.dock.unpin_app(self.item)

    def _on_close(self, btn):
        self.close()
        # Tenta fechar graciosamente
        main_cmd = self.item.cmd.split("||")[0].strip().split("/")[-1].strip()
        subprocess.run(
            ["pkill", "-f", main_cmd],
            capture_output=True, timeout=3
        )

    def _on_key(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False


# ─── Aplicação principal ──────────────────────────────────────────────────────

class RjosDockApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="org.rjos.dock",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.dock = None
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        # Carrega CSS
        provider = Gtk.CssProvider()
        provider.load_from_string(DOCK_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Cria e mostra dock
        self.dock = RjosDock(self)
        self.dock.present()


def main():
    # Verifica WAYLAND_DISPLAY
    if not os.environ.get("WAYLAND_DISPLAY"):
        print("[ERROR] WAYLAND_DISPLAY não definido.")
        print("Execute o compositor primeiro: rjos-compositor")
        sys.exit(1)

    app = RjosDockApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
