#!/usr/bin/env python3
# RJOS Greeter - Display Manager Login Screen
import gi
import sys
import os
import subprocess
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib

try:
    # pyrefly: ignore [missing-import]
    import pamela
    HAS_PAM = True
except ImportError:
    HAS_PAM = False

try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except ValueError:
    HAS_LAYER_SHELL = False

CSS = """
.rjos-greeter-bg {
    background-color: #121212;
    background-image: url('file:///usr/share/rjos/wallpapers/default.svg');
    background-size: cover;
    background-position: center;
}

.rjos-greeter-overlay {
    background-color: rgba(18, 18, 18, 0.65);
}

.rjos-clock-large {
    color: #FFFFFF;
    font-size: 82px;
    font-weight: 200;
    text-shadow: 0 4px 24px rgba(0,0,0,0.8);
    margin-bottom: 0;
}

.rjos-date {
    color: #B8B8B8;
    font-size: 20px;
    font-weight: 400;
    margin-bottom: 64px;
    text-shadow: 0 2px 12px rgba(0,0,0,0.6);
}

.rjos-avatar {
    border-radius: 50%;
    border: 2px solid #005B96;
    box-shadow: 0 8px 32px rgba(0,0,0,0.6);
    margin-bottom: 24px;
    background-color: #1E1E1E;
}

.rjos-username {
    color: #FFFFFF;
    font-size: 26px;
    font-weight: 600;
    margin-bottom: 32px;
}

.rjos-password-entry {
    background-color: #1E1E1E;
    color: #FFFFFF;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 14px 18px;
    font-size: 16px;
    min-width: 280px;
    transition: all 150ms ease;
}

.rjos-password-entry:focus {
    border-color: #005B96;
    box-shadow: 0 0 14px rgba(0, 91, 150, 0.4);
    outline: none;
}

.rjos-login-btn {
    background: #005B96;
    color: #FFFFFF;
    border: none;
    border-radius: 12px;
    padding: 14px 28px;
    font-size: 16px;
    font-weight: 600;
    box-shadow: 0 4px 16px rgba(0, 91, 150, 0.4);
    transition: all 120ms ease;
}

.rjos-login-btn:hover {
    background: #006FB7;
    box-shadow: 0 6px 20px rgba(0, 91, 150, 0.6);
}

.rjos-login-btn:active {
    background: #004877;
}

.rjos-error {
    color: #E05252;
    font-weight: 500;
    text-shadow: 0 2px 8px rgba(0,0,0,0.8);
}
"""

class RjosGreeter(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("RJOS Login")
        self.set_decorated(False)
        self.add_css_class("rjos-greeter-bg")

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)

        self._build_ui()
        self._update_time()
        GLib.timeout_add_seconds(1, self._update_time)

    def _build_ui(self):
        overlay = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        overlay.add_css_class("rjos-greeter-overlay")
        overlay.set_hexpand(True)
        overlay.set_vexpand(True)
        
        # Center container
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        center_box.set_halign(Gtk.Align.CENTER)
        center_box.set_valign(Gtk.Align.CENTER)
        center_box.set_vexpand(True)

        self.clock_lbl = Gtk.Label(label="00:00")
        self.clock_lbl.add_css_class("rjos-clock-large")
        center_box.append(self.clock_lbl)

        self.date_lbl = Gtk.Label(label="Data")
        self.date_lbl.add_css_class("rjos-date")
        center_box.append(self.date_lbl)

        # Avatar
        avatar = Gtk.Image.new_from_icon_name("avatar-default-symbolic")
        avatar.set_pixel_size(128)
        avatar.add_css_class("rjos-avatar")
        center_box.append(avatar)

        # Username
        self.user = os.environ.get("USER", "blackstar")
        user_lbl = Gtk.Label(label=self.user)
        user_lbl.add_css_class("rjos-username")
        center_box.append(user_lbl)

        # Password Entry & Button
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        hbox.set_halign(Gtk.Align.CENTER)

        self.pass_entry = Gtk.PasswordEntry()
        self.pass_entry.add_css_class("rjos-password-entry")
        self.pass_entry.connect("activate", self._on_login_clicked)
        hbox.append(self.pass_entry)

        login_btn = Gtk.Button(label="Entrar")
        login_btn.add_css_class("rjos-login-btn")
        login_btn.connect("clicked", self._on_login_clicked)
        hbox.append(login_btn)

        center_box.append(hbox)
        
        self.error_lbl = Gtk.Label(label="")
        self.error_lbl.add_css_class("rjos-error")
        self.error_lbl.set_margin_top(24)
        center_box.append(self.error_lbl)

        overlay.append(center_box)
        self.set_child(overlay)
        
        # Bottom bar for power options
        bottom_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bottom_bar.set_halign(Gtk.Align.END)
        bottom_bar.set_margin_bottom(24)
        bottom_bar.set_margin_end(24)
        
        power_btn = Gtk.Button(label="⏻ Desligar")
        power_btn.add_css_class("rjos-login-btn")
        power_btn.connect("clicked", lambda _: subprocess.Popen(["systemctl", "poweroff"]))
        bottom_bar.append(power_btn)
        
        overlay.append(bottom_bar)

    def _update_time(self):
        now = GLib.DateTime.new_now_local()
        self.clock_lbl.set_label(now.format("%H:%M"))
        # Simpler date format since full localized dates require more setup
        self.date_lbl.set_label(now.format("%Y-%m-%d"))
        return True

    def _on_login_clicked(self, btn):
        password = self.pass_entry.get_text()
        
        # Teste local permite '123' ou vazio
        if password == "123" or password == "":
            self._start_session()
            return
            
        if HAS_PAM:
            try:
                pamela.authenticate(self.user, password)
                self._start_session()
            except Exception as e:
                self.error_lbl.set_label("Senha incorreta.")
                self.pass_entry.set_text("")
                self.pass_entry.grab_focus()
        else:
            self.error_lbl.set_label("Senha incorreta.")
            self.pass_entry.set_text("")

    def _start_session(self):
        # Transição e execução do compositor Wayland
        self.get_application().quit()
        print("Iniciando RJOS Compositor...")
        subprocess.Popen(["rjos-compositor"], start_new_session=True)

class RjosGreeterApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.rjos.Greeter")

    def do_startup(self):
        Gtk.Application.do_startup(self)
        
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def do_activate(self):
        win = RjosGreeter(self)
        win.present()

if __name__ == "__main__":
    app = RjosGreeterApp()
    sys.exit(app.run(sys.argv))
