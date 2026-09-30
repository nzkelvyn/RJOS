#!/usr/bin/env python3
# =============================================================================
# RJOS App Launcher — app_launcher.py
# Menu Iniciar / Lançador de Aplicativos
#
# Exibe um grid com os aplicativos instalados e uma barra de pesquisa.
# Usa Gio.AppInfo para ler os aplicativos do sistema.
# =============================================================================

import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gdk, Gio, GLib

try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except (ValueError, ImportError):
    HAS_LAYER_SHELL = False

# Importa o provedor de tema oficial do RJOS
try:
    from rjos_theme import apply_rjos_theme_provider, RJOS_SHARED_CSS_VARS
except ImportError:
    apply_rjos_theme_provider = None


APP_LAUNCHER_CSS = """
/* ══════════════════════════════════════════════════════════════════
   RJOS App Launcher
   ══════════════════════════════════════════════════════════════════ */

.rjos-launcher-window {
    background-color: alpha(@rjos-bg, 0.85);
    border: 1px solid @rjos-surface-border;
    border-radius: var(--rjos-radius-xl);
    box-shadow: var(--rjos-shadow-xl);
}

.rjos-launcher-search {
    margin: 16px;
    padding: 8px 16px;
    font-size: 16px;
    border-radius: var(--rjos-radius-pill);
    background-color: @rjos-surface;
    color: @rjos-text;
    border: 1px solid @rjos-surface-border;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.2);
}

.rjos-launcher-search:focus {
    border-color: @rjos-blue;
    box-shadow: 0 0 0 2px @rjos-blue-dim;
}

.rjos-launcher-flowbox {
    padding: 0 16px 16px 16px;
}

.rjos-app-item {
    padding: 12px 8px;
    border-radius: var(--rjos-radius-md);
    transition: var(--rjos-transition-fast);
    background-color: transparent;
}

.rjos-app-item:hover {
    background-color: @rjos-surface-hover;
    transform: scale(1.05);
}

.rjos-app-item:active {
    background-color: @rjos-surface-active;
    transform: scale(0.95);
}

.rjos-app-icon {
    margin-bottom: 8px;
}

.rjos-app-label {
    color: @rjos-text;
    font-size: 13px;
    font-weight: 500;
}
"""

class RjosAppLauncher(Gtk.Window):
    def __init__(self, app=None):
        super().__init__(application=app)
        
        self.set_title("RJOS Launcher")
        self.set_default_size(700, 500)
        self.set_decorated(False)
        self.add_css_class("rjos-launcher-window")

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, False)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, False)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, False)

        # Container Principal
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        # Barra de Pesquisa
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Pesquisar aplicativos...")
        self.search_entry.add_css_class("rjos-launcher-search")
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.main_box.append(self.search_entry)

        # Scrolled Window para o Grid de Apps
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.set_vexpand(True)
        
        # Grid (FlowBox) de Aplicativos
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(6)
        self.flowbox.set_min_children_per_line(4)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.add_css_class("rjos-launcher-flowbox")
        
        self.scrolled_window.set_child(self.flowbox)
        self.main_box.append(self.scrolled_window)

        self.set_child(self.main_box)

        # Carregar Apps
        self.apps = []
        self.load_apps()
        self.populate_grid()

    def load_apps(self):
        """Usa Gio.AppInfo para carregar os apps do sistema"""
        all_apps = Gio.AppInfo.get_all()
        for app in all_apps:
            if app.should_show():
                self.apps.append(app)
        
        # Ordena alfabeticamente
        self.apps.sort(key=lambda a: a.get_display_name().lower() if a.get_display_name() else "")

    def create_app_widget(self, app_info):
        """Cria o widget (Ícone + Texto) para um aplicativo"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_size_request(96, 96)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        
        # Ícone
        icon = Gtk.Image()
        icon.set_pixel_size(48)
        icon.add_css_class("rjos-app-icon")
        
        gicon = app_info.get_icon()
        if gicon:
            icon.set_from_gicon(gicon)
        else:
            icon.set_from_icon_name("application-x-executable")
            
        box.append(icon)

        # Texto
        name = app_info.get_display_name()
        label = Gtk.Label(label=name)
        label.add_css_class("rjos-app-label")
        label.set_ellipsize(Pango.EllipsizeMode.END if hasattr(gi.repository, 'Pango') else 3) # 3 is END
        label.set_max_width_chars(12)
        label.set_justify(Gtk.Justification.CENTER)
        box.append(label)

        # Botão interativo
        btn = Gtk.Button()
        btn.set_child(box)
        btn.add_css_class("rjos-app-item")
        btn.connect("clicked", self.on_app_clicked, app_info)
        
        return btn

    def populate_grid(self, filter_text=""):
        """Preenche o FlowBox com os apps (filtrados ou todos)"""
        # Limpar grid atual
        while child := self.flowbox.get_first_child():
            self.flowbox.remove(child)

        filter_text = filter_text.lower().strip()
        
        for app in self.apps:
            name = app.get_display_name()
            if not name:
                continue
                
            if filter_text and filter_text not in name.lower():
                continue
                
            widget = self.create_app_widget(app)
            self.flowbox.append(widget)

    def on_search_changed(self, search_entry):
        """Atualiza os apps quando a pesquisa muda"""
        text = search_entry.get_text()
        self.populate_grid(text)

    def on_app_clicked(self, button, app_info):
        """Lança o aplicativo ao ser clicado"""
        print(f"[Launcher] Iniciando: {app_info.get_display_name()}")
        try:
            # Lança o app usando Gio
            context = Gdk.Display.get_default().get_app_launch_context()
            app_info.launch([], context)
        except Exception as e:
            print(f"[Launcher] Erro ao iniciar {app_info.get_display_name()}: {e}")
        
        # Fecha o launcher após iniciar o app
        self.close()

class RjosLauncherApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="org.rjos.launcher",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        # Aplica o tema
        if apply_rjos_theme_provider:
            apply_rjos_theme_provider(APP_LAUNCHER_CSS)
        else:
            provider = Gtk.CssProvider()
            provider.load_from_string(APP_LAUNCHER_CSS)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

        # Workaround para importar Pango, usado no ellipsize
        global Pango
        try:
            gi.require_version('Pango', '1.0')
            from gi.repository import Pango
        except ImportError:
            pass

        win = RjosAppLauncher(app)
        win.present()

def main():
    app = RjosLauncherApp()
    return app.run(sys.argv if 'sys' in dir() else [])

if __name__ == "__main__":
    sys.exit(main())
