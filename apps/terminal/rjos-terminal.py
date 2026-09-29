#!/usr/bin/env python3
# =============================================================================
# RJOS Terminal — rjos-terminal.py
# Terminal emulador próprio usando VTE + GTK4
#
# Suporta: múltiplas abas, cores RJOS, fontes mono, scrollback
# Dependências: python3-gi, gir1.2-vte-3.91 ou gir1.2-vte-2.91-gtk4
# =============================================================================

import gi
import os
import sys

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

try:
    gi.require_version('Vte', '3.91')
    from gi.repository import Vte
    VTE_OK = True
except (ValueError, ImportError):
    VTE_OK = False

from gi.repository import Gtk, Adw, GLib, Gdk, Gio, Pango
import subprocess

# ─── Paleta de cores RJOS para o terminal ────────────────────────────────────
# Baseada na paleta oficial RJOS
RJOS_TERM_CSS = """
.rjos-terminal-window {
    background-color: #0D1B2A;
}
.rjos-tab-bar {
    background-color: #0D1B2A;
    border-bottom: 1px solid #2A3F58;
}
.rjos-tab-btn {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: #8BA7BF;
    padding: 6px 16px;
    font-size: 12px;
    transition: all 150ms ease;
    border-radius: 0;
}
.rjos-tab-btn.active {
    color: #00D4FF;
    border-bottom-color: #00D4FF;
}
.rjos-tab-btn:hover {
    color: #E8F4FD;
    background-color: rgba(0, 212, 255, 0.08);
}
.rjos-tab-new {
    background: transparent;
    border: none;
    color: #8BA7BF;
    padding: 6px 10px;
    font-size: 16px;
    border-radius: 4px;
}
.rjos-tab-new:hover {
    color: #00D4FF;
    background-color: rgba(0, 212, 255, 0.08);
}
.rjos-titlebar {
    background-color: #0D1B2A;
    border-bottom: 1px solid #122840;
    min-height: 38px;
}
.rjos-title-label {
    color: #E8F4FD;
    font-size: 13px;
    font-weight: 500;
}
"""

# Cores VTE (16 cores ANSI mapeadas para paleta RJOS)
VTE_COLORS = [
    "#0D1B2A",  # 0  black
    "#FF3D71",  # 1  red
    "#00E676",  # 2  green
    "#FFB300",  # 3  yellow
    "#00D4FF",  # 4  blue (cyan no RJOS)
    "#7B2FBE",  # 5  magenta/purple
    "#00BCD4",  # 6  cyan
    "#E8F4FD",  # 7  white
    "#2A3F58",  # 8  bright black
    "#FF6B9D",  # 9  bright red
    "#69F0AE",  # 10 bright green
    "#FFD54F",  # 11 bright yellow
    "#80DFFF",  # 12 bright blue
    "#CE93D8",  # 13 bright magenta
    "#4DD0E1",  # 14 bright cyan
    "#FFFFFF",  # 15 bright white
]


def parse_color(hex_str):
    """Converte string hex para Gdk.RGBA"""
    color = Gdk.RGBA()
    color.parse(hex_str)
    return color


# ─── Widget do Terminal VTE ──────────────────────────────────────────────────

class TerminalWidget(Gtk.Box):
    def __init__(self, cwd=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_vexpand(True)
        self.set_hexpand(True)

        if not VTE_OK:
            # Fallback: mostra mensagem de erro
            label = Gtk.Label(
                label="VTE não disponível.\nInstale: sudo apt install python3-gi gir1.2-vte-2.91-gtk4"
            )
            label.set_vexpand(True)
            self.append(label)
            return

        # Cria terminal VTE
        self.term = Vte.Terminal()
        self._configure_terminal()
        self._spawn_shell(cwd)

        # Scroll
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.set_child(self.term)
        self.append(scroll)

        # Callback de título
        self.term.connect("window-title-changed", self._on_title_changed)
        self.term.connect("child-exited", self._on_child_exited)
        self._title_callbacks = []

    def _configure_terminal(self):
        # Fonte monospace RJOS
        font = Pango.FontDescription.from_string("JetBrains Mono 12")
        self.term.set_font(font)

        # Cores
        fg = parse_color("#E8F4FD")
        bg = parse_color("#0A1520")

        palette = [parse_color(c) for c in VTE_COLORS]
        self.term.set_colors(fg, bg, palette)

        # Configurações
        self.term.set_scrollback_lines(10000)
        self.term.set_cursor_blink_mode(Vte.CursorBlinkMode.ON)
        self.term.set_cursor_shape(Vte.CursorShape.BLOCK)
        self.term.set_mouse_autohide(True)
        self.term.set_bold_is_bright(True)
        self.term.set_allow_hyperlink(True)

        # Padding
        self.term.set_margin_start(4)
        self.term.set_margin_end(4)
        self.term.set_margin_top(4)
        self.term.set_margin_bottom(4)

    def _spawn_shell(self, cwd=None):
        shell = os.environ.get("SHELL", "/bin/bash")
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["COLORTERM"] = "truecolor"

        self.term.spawn_async(
            Vte.PtyFlags.DEFAULT,
            cwd or os.path.expanduser("~"),
            [shell],
            [f"{k}={v}" for k, v in env.items()],
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None, None,
            -1,
            None,
            None, None
        )

    def _on_title_changed(self, term):
        title = term.get_window_title() or "Terminal"
        for cb in self._title_callbacks:
            cb(title)

    def _on_child_exited(self, term, status):
        # Fecha aba ao sair do shell
        for cb in getattr(self, "_exit_callbacks", []):
            cb()

    def on_title_changed(self, callback):
        self._title_callbacks.append(callback)

    def on_exit(self, callback):
        if not hasattr(self, "_exit_callbacks"):
            self._exit_callbacks = []
        self._exit_callbacks.append(callback)

    def feed_text(self, text):
        if VTE_OK:
            self.term.feed_child(text.encode())

    def copy(self):
        if VTE_OK:
            self.term.copy_clipboard_format(Vte.Format.TEXT)

    def paste(self):
        if VTE_OK:
            self.term.paste_clipboard()


# ─── Janela principal do Terminal ────────────────────────────────────────────

class RjosTerminalWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_title("Terminal — RJOS")
        self.set_default_size(800, 520)
        self.tabs = []
        self.active_tab_index = 0

        self._build_ui()
        self._setup_shortcuts()
        self._add_tab()  # Primeira aba

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Barra de título customizada
        self.titlebar = Adw.HeaderBar()
        self.titlebar.add_css_class("rjos-titlebar")

        self.title_label = Gtk.Label(label="Terminal")
        self.title_label.add_css_class("rjos-title-label")
        self.titlebar.set_title_widget(self.title_label)

        # Botão nova aba no header
        new_tab_btn = Gtk.Button(label="+")
        new_tab_btn.add_css_class("rjos-tab-new")
        new_tab_btn.set_tooltip_text("Nova aba (Ctrl+Shift+T)")
        new_tab_btn.connect("clicked", lambda _: self._add_tab())
        self.titlebar.pack_end(new_tab_btn)

        self.set_titlebar(self.titlebar)

        # Barra de abas
        self.tab_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.tab_bar.add_css_class("rjos-tab-bar")
        self.tab_bar.set_hexpand(True)
        main_box.append(self.tab_bar)

        # Stack de terminais
        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150)
        main_box.append(self.stack)

        self.set_content(main_box)

    def _setup_shortcuts(self):
        # Ctrl+Shift+T — Nova aba
        ctrl = Gtk.ShortcutController()
        ctrl.set_scope(Gtk.ShortcutScope.MANAGED)

        new_tab = Gtk.Shortcut(
            trigger=Gtk.KeyvalTrigger.new(
                Gdk.KEY_t,
                Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK
            ),
            action=Gtk.CallbackAction.new(lambda *a: self._add_tab() or True)
        )
        ctrl.add_shortcut(new_tab)

        # Ctrl+Shift+W — Fecha aba
        close_tab = Gtk.Shortcut(
            trigger=Gtk.KeyvalTrigger.new(
                Gdk.KEY_w,
                Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK
            ),
            action=Gtk.CallbackAction.new(
                lambda *a: self._close_tab(self.active_tab_index) or True
            )
        )
        ctrl.add_shortcut(close_tab)

        # Ctrl+Shift+C — Copiar
        copy_sc = Gtk.Shortcut(
            trigger=Gtk.KeyvalTrigger.new(
                Gdk.KEY_c,
                Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK
            ),
            action=Gtk.CallbackAction.new(
                lambda *a: self._active_term().copy() or True
            )
        )
        ctrl.add_shortcut(copy_sc)

        # Ctrl+Shift+V — Colar
        paste_sc = Gtk.Shortcut(
            trigger=Gtk.KeyvalTrigger.new(
                Gdk.KEY_v,
                Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK
            ),
            action=Gtk.CallbackAction.new(
                lambda *a: self._active_term().paste() or True
            )
        )
        ctrl.add_shortcut(paste_sc)

        self.add_controller(ctrl)

    def _add_tab(self, cwd=None):
        idx = len(self.tabs)
        term_widget = TerminalWidget(cwd)

        # Botão da aba
        tab_btn = Gtk.Button(label=f"Terminal {idx + 1}")
        tab_btn.add_css_class("rjos-tab-btn")
        tab_btn.connect("clicked", self._on_tab_clicked, idx)

        self.tab_bar.append(tab_btn)

        # Adiciona ao stack
        name = f"tab-{idx}"
        self.stack.add_named(term_widget, name)

        self.tabs.append({
            "widget":  term_widget,
            "btn":     tab_btn,
            "name":    name,
        })

        # Callback de título
        term_widget.on_title_changed(
            lambda title, i=idx: self._on_tab_title_changed(i, title)
        )

        # Callback de saída
        term_widget.on_exit(lambda i=idx: self._close_tab(i))

        self._switch_to_tab(idx)
        return term_widget

    def _active_term(self):
        if self.active_tab_index < len(self.tabs):
            return self.tabs[self.active_tab_index]["widget"]
        return None

    def _switch_to_tab(self, idx):
        if idx < 0 or idx >= len(self.tabs):
            return

        # Desativa aba anterior
        if self.active_tab_index < len(self.tabs):
            self.tabs[self.active_tab_index]["btn"].remove_css_class("active")

        self.active_tab_index = idx
        self.stack.set_visible_child_name(self.tabs[idx]["name"])
        self.tabs[idx]["btn"].add_css_class("active")

        # Foco no terminal
        GLib.idle_add(self.tabs[idx]["widget"].grab_focus)

    def _on_tab_clicked(self, btn, idx):
        self._switch_to_tab(idx)

    def _on_tab_title_changed(self, idx, title):
        if idx < len(self.tabs):
            label = title[:20] if title else f"Terminal {idx + 1}"
            self.tabs[idx]["btn"].set_label(label)
            if idx == self.active_tab_index:
                self.title_label.set_text(f"{title} — RJOS Terminal")

    def _close_tab(self, idx):
        if len(self.tabs) <= 1:
            self.close()
            return

        tab = self.tabs.pop(idx)
        self.tab_bar.remove(tab["btn"])
        self.stack.remove(tab["widget"])

        # Atualiza índice
        if self.active_tab_index >= len(self.tabs):
            self.active_tab_index = len(self.tabs) - 1
        self._switch_to_tab(self.active_tab_index)


# ─── Aplicação ───────────────────────────────────────────────────────────────

class RjosTerminalApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="org.rjos.terminal",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        provider = Gtk.CssProvider()
        provider.load_from_string(RJOS_TERM_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        win = RjosTerminalWindow(application=self)
        win.present()


def main():
    app = RjosTerminalApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
