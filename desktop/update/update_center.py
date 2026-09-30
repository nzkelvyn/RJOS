#!/usr/bin/env python3
import gi
import sys
import os
import subprocess
from pathlib import Path

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

sys.path.append(str(Path(__file__).resolve().parent.parent.parent / "system"))

from update.manager import UpdateManager
from update.version import RJOS_VERSION

try:
    sys.path.append(str(Path(__file__).resolve().parent.parent / "shell"))
    from rjos_theme import apply_rjos_theme_provider
except ImportError:
    apply_rjos_theme_provider = None


class RjosUpdateCenter(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Atualizações do RJOS")
        self.set_default_size(500, 400)
        
        if apply_rjos_theme_provider:
            apply_rjos_theme_provider("")
            
        self.manager = UpdateManager()
        
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.box.set_margin_top(24)
        self.box.set_margin_bottom(24)
        self.box.set_margin_start(24)
        self.box.set_margin_end(24)
        self.set_child(self.box)

        self.title_label = Gtk.Label(label="Verificando atualizações...")
        self.title_label.add_css_class("title-1")
        self.box.append(self.title_label)

        self.spinner = Gtk.Spinner()
        self.spinner.start()
        self.box.append(self.spinner)
        
        self.info_label = Gtk.Label()
        self.info_label.set_wrap(True)
        self.box.append(self.info_label)

        self.btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.btn_box.set_halign(Gtk.Align.CENTER)
        
        self.update_btn = Gtk.Button(label="Atualizar agora")
        self.update_btn.add_css_class("suggested-action")
        self.update_btn.connect("clicked", self.on_update_clicked)
        self.update_btn.set_visible(False)
        self.btn_box.append(self.update_btn)

        self.later_btn = Gtk.Button(label="Mais tarde")
        self.later_btn.connect("clicked", lambda x: self.close())
        self.later_btn.set_visible(False)
        self.btn_box.append(self.later_btn)
        
        self.box.append(self.btn_box)

        # Check async
        GLib.idle_add(self.check_updates)

    def check_updates(self):
        latest = self.manager.check_for_updates()
        self.spinner.stop()
        self.spinner.set_visible(False)
        
        if latest:
            v = latest["version"]
            self.title_label.set_text(f"RJOS {v} disponível")
            
            info = self.manager.get_release_info(version=v)
            if info:
                desc = info.get("description", "")
                changes = "\n".join([f" ✓ {c}" for c in info.get("changes", [])])
                self.info_label.set_text(f"{desc}\n\nEsta atualização contém:\n{changes}")
            
            self.update_btn.set_visible(True)
            self.later_btn.set_visible(True)
        else:
            self.title_label.set_text("Nenhuma atualização disponível")
            self.info_label.set_text(f"O RJOS (versão {RJOS_VERSION}) já está atualizado.")
            self.later_btn.set_label("Fechar")
            self.later_btn.set_visible(True)
        return False
        
    def on_update_clicked(self, btn):
        self.update_btn.set_sensitive(False)
        self.later_btn.set_sensitive(False)
        
        ok, errors = self.manager.run_preflight()
        if not ok:
            self.title_label.set_text("Requisitos não atendidos")
            err_text = "\\n".join(errors)
            self.info_label.set_text(f"Não é possível atualizar agora:\\n\\n{err_text}")
            self.later_btn.set_label("Fechar")
            self.later_btn.set_sensitive(True)
            self.update_btn.set_visible(False)
            return

        self.title_label.set_text("Instalando...")
        self.info_label.set_text("Isso pode levar alguns minutos. Não desligue o computador.")
        self.spinner.start()
        self.spinner.set_visible(True)
        
        # Trigger install in background (simple approach)
        GLib.timeout_add(100, self._do_install)
        
    def _do_install(self):
        # We call the CLI to do the actual install
        result = subprocess.run([sys.executable, str(Path(__file__).resolve().parent.parent.parent / "system" / "cli" / "rjos-update"), "install"])
        self.spinner.stop()
        self.spinner.set_visible(False)
        
        if result.returncode == 0:
            self.title_label.set_text("Atualização concluída")
            self.info_label.set_text("O sistema foi atualizado com sucesso.")
        else:
            self.title_label.set_text("Erro ao atualizar")
            self.info_label.set_text("Houve um problema durante a instalação.")
            
        self.later_btn.set_label("Fechar")
        self.later_btn.set_sensitive(True)
        return False

class RjosUpdateApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.rjos.update-center")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        win = RjosUpdateCenter(self)
        win.present()

if __name__ == "__main__":
    app = RjosUpdateApp()
    app.run(sys.argv)
