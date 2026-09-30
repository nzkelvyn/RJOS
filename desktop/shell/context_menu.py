#!/usr/bin/env python3
# =============================================================================
# RJOS Context Menu — context_menu.py
# Menu de contexto do desktop (clique direito na área de trabalho)
#
# Integrado ao compositor via Layer Shell.
# Opções: Alterar wallpaper, Configurações de tela, Terminal, Organizar, Sobre
#
# Dependências:
#   python3-gi (PyGObject), gir1.2-gtk-4.0, gir1.2-adw-1
#   gtk4-layer-shell (libgtk4-layer-shell)
# =============================================================================

import gi
import os
import subprocess

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gdk, Gio

try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except (ValueError, ImportError):
    HAS_LAYER_SHELL = False

# ─── CSS ──────────────────────────────────────────────────────────────────────

CONTEXT_MENU_CSS = """
/* ══════════════════════════════════════════════════════════════════
   RJOS Context Menu — Estilos Oficiais RJOS
   ══════════════════════════════════════════════════════════════════ */

.rjos-ctx-menu {
    background-color: #1E1E1E;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    box-shadow: 0 10px 36px rgba(0, 0, 0, 0.75);
    padding: 6px;
    min-width: 220px;
}

.rjos-ctx-item {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 400;
    transition: all 100ms ease;
}

.rjos-ctx-item:hover {
    background-color: #292929;
    color: #FFFFFF;
}

.rjos-ctx-item-icon {
    font-size: 15px;
    min-width: 24px;
    margin-right: 8px;
    color: #005B96;
}

.rjos-ctx-item-label {
    color: inherit;
    font-size: 13px;
}

.rjos-ctx-item-shortcut {
    color: #B8B8B8;
    font-size: 11px;
    font-weight: 400;
}

.rjos-ctx-separator {
    background-color: rgba(255, 255, 255, 0.08);
    min-height: 1px;
    margin: 4px 8px;
}

.rjos-ctx-submenu-arrow {
    color: #B8B8B8;
    font-size: 10px;
}
"""


class RjosContextMenu(Gtk.Window):
    """Menu de contexto do desktop RJOS"""

    def __init__(self, parent_shell, x=0, y=0):
        super().__init__()
        self.parent_shell = parent_shell

        self.set_decorated(False)
        self.set_resizable(False)

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_keyboard_mode(
                self, GtkLayerShell.KeyboardMode.EXCLUSIVE
            )
            # Posiciona onde clicou
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, int(y))
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, int(x))

        self._build_ui()

        # Fecha com Escape
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_key)
        self.add_controller(key_ctrl)

    def _build_ui(self):
        menu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        menu.add_css_class("rjos-ctx-menu")

        # Itens do menu
        items = [
            ("🖼️", "Alterar Wallpaper",    None,        self._on_change_wallpaper),
            ("🖥️", "Configurações de Tela", None,        self._on_display_settings),
            None,  # separador
            ("📁", "Abrir Arquivos",        "Super+F",   self._on_open_files),
            ("🖥️", "Abrir Terminal",        "Super+T",   self._on_open_terminal),
            None,  # separador
            ("📐", "Organizar Ícones",      None,        self._on_arrange_icons),
            ("🧹", "Limpar Área de Trabalho", None,      self._on_clean_desktop),
            None,  # separador
            ("⚙️", "Configurações",         None,        self._on_settings),
            ("ℹ️", "Sobre o RJOS",          None,        self._on_about),
        ]

        for item in items:
            if item is None:
                sep = Gtk.Separator()
                sep.add_css_class("rjos-ctx-separator")
                menu.append(sep)
            else:
                icon, label, shortcut, callback = item
                menu.append(self._make_item(icon, label, shortcut, callback))

        self.set_child(menu)

    def _make_item(self, icon, label, shortcut, callback):
        """Cria um item do menu de contexto"""
        btn = Gtk.Button()
        btn.add_css_class("rjos-ctx-item")

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        # Ícone
        icon_lbl = Gtk.Label(label=icon)
        icon_lbl.add_css_class("rjos-ctx-item-icon")
        hbox.append(icon_lbl)

        # Label
        text_lbl = Gtk.Label(label=label)
        text_lbl.add_css_class("rjos-ctx-item-label")
        text_lbl.set_hexpand(True)
        text_lbl.set_halign(Gtk.Align.START)
        hbox.append(text_lbl)

        # Shortcut (se houver)
        if shortcut:
            sc_lbl = Gtk.Label(label=shortcut)
            sc_lbl.add_css_class("rjos-ctx-item-shortcut")
            hbox.append(sc_lbl)

        btn.set_child(hbox)
        btn.connect("clicked", callback)
        return btn

    # ── Handlers ──

    def _on_change_wallpaper(self, btn):
        self.close()
        subprocess.Popen(
            ["/bin/sh", "-c", "rjos-wallpaper-manager"],
            start_new_session=True
        )

    def _on_display_settings(self, btn):
        self.close()
        subprocess.Popen(
            ["/bin/sh", "-c", "rjos-settings display || wdisplays"],
            start_new_session=True
        )

    def _on_open_files(self, btn):
        self.close()
        subprocess.Popen(
            ["/bin/sh", "-c", "rjos-files"],
            start_new_session=True
        )

    def _on_open_terminal(self, btn):
        self.close()
        subprocess.Popen(
            ["/bin/sh", "-c", "rjos-terminal || foot || alacritty || xterm"],
            start_new_session=True
        )

    def _on_arrange_icons(self, btn):
        self.close()
        # TODO: Implementar organização de ícones do desktop
        print("[ctx] Organizar ícones — em breve")

    def _on_clean_desktop(self, btn):
        self.close()
        # TODO: Mover arquivos da área de trabalho para uma pasta
        print("[ctx] Limpar desktop — em breve")

    def _on_settings(self, btn):
        self.close()
        subprocess.Popen(
            ["/bin/sh", "-c", "rjos-settings"],
            start_new_session=True
        )

    def _on_about(self, btn):
        self.close()
        dialog = RjosAboutDialog()
        dialog.present()

    def _on_key(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False


# ─── Diálogo "Sobre o RJOS" ──────────────────────────────────────────────────

class RjosAboutDialog(Gtk.Window):
    """Janela 'Sobre o RJOS'"""

    def __init__(self):
        super().__init__()
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(360, 300)

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_keyboard_mode(
                self, GtkLayerShell.KeyboardMode.EXCLUSIVE
            )

        self._build_ui()

        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", lambda c, k, *a:
                         self.close() or True if k == Gdk.KEY_Escape else False)
        self.add_controller(key_ctrl)

    def _build_ui(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.add_css_class("rjos-ctx-menu")
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)

        # Logo
        logo = Gtk.Label(label="RJOS")
        logo.set_markup(
            '<span font_size="xx-large" font_weight="ultrabold"'
            ' foreground="#00D4FF">R J O S</span>'
        )
        box.append(logo)

        # Versão
        version = Gtk.Label(label="Versão 0.1.0-alpha")
        version.set_markup(
            '<span foreground="#8BA7BF" font_size="small">'
            'Versão 0.1.0-alpha</span>'
        )
        box.append(version)

        # Descrição
        desc = Gtk.Label(
            label="Uma distribuição Linux construída do zero\n"
                  "com identidade visual e experiência próprias."
        )
        desc.set_wrap(True)
        desc.set_justify(Gtk.Justification.CENTER)
        desc.set_markup(
            '<span foreground="#8BA7BF" font_size="small">'
            'Uma distribuição Linux construída do zero\n'
            'com identidade visual e experiência próprias.</span>'
        )
        box.append(desc)

        # Stack técnico
        stack_text = (
            "Compositor: wlroots + Wayland\n"
            "Shell: GTK4 + Python\n"
            "Tema: RJOS Dark\n"
            "Base: Debian"
        )
        stack_lbl = Gtk.Label(label=stack_text)
        stack_lbl.set_markup(
            '<span foreground="#4A6580" font_size="x-small">'
            f'{stack_text}</span>'
        )
        stack_lbl.set_justify(Gtk.Justification.CENTER)
        box.append(stack_lbl)

        # Botão fechar
        close_btn = Gtk.Button(label="Fechar")
        close_btn.add_css_class("rjos-ctx-item")
        close_btn.set_halign(Gtk.Align.CENTER)
        close_btn.connect("clicked", lambda b: self.close())
        box.append(close_btn)

        self.set_child(box)
