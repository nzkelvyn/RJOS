import os
import pathlib

ROOT = pathlib.Path(r"c:\Users\kelvyna\RJOS")
SYSTEM = ROOT / "system"
DESKTOP = ROOT / "desktop"

FILES = {
    SYSTEM / "update" / "__init__.py": "",
    SYSTEM / "update" / "version.py": '''"""Version definitions for RJOS."""
import re

RJOS_VERSION = "0.1.1"

def compare_versions(v1, v2):
    """Compares semantic versions. Returns -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2."""
    def parse_version(v):
        return tuple(map(int, re.findall(r'\\d+', v)))
    
    p1 = parse_version(v1)
    p2 = parse_version(v2)
    if p1 < p2: return -1
    if p1 > p2: return 1
    return 0
''',
    SYSTEM / "update" / "source.py": '''"""Update sources abstraction."""
from abc import ABC, abstractmethod

class UpdateSource(ABC):
    @abstractmethod
    def get_latest(self, channel="stable"):
        pass

    @abstractmethod
    def get_release(self, channel, version):
        pass
''',
    SYSTEM / "update" / "github_pages.py": '''"""GitHub Pages Update Source implementation."""
import urllib.request
import json
import yaml
from .source import UpdateSource

class GitHubPagesSource(UpdateSource):
    def __init__(self, base_url="https://raw.githubusercontent.com/rjos/rjos-updates/main/updates"):
        self.base_url = base_url

    def _fetch_yaml(self, url):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'RJOS-Update'})
            with urllib.request.urlopen(req) as response:
                return yaml.safe_load(response.read().decode('utf-8'))
        except Exception as e:
            return None

    def get_latest(self, channel="stable"):
        return self._fetch_yaml(f"{self.base_url}/{channel}/latest.yaml")

    def get_release(self, channel, version):
        return self._fetch_yaml(f"{self.base_url}/{channel}/releases/{version}.yaml")
''',
    SYSTEM / "update" / "cache.py": '''"""Cache for update metadata."""
import os
import json
import yaml
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "rjos-update"

class UpdateCache:
    def __init__(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.latest_file = CACHE_DIR / "latest.json"

    def save_latest(self, data):
        with open(self.latest_file, "w") as f:
            json.dump(data, f)

    def get_latest(self):
        if self.latest_file.exists():
            with open(self.latest_file, "r") as f:
                return json.load(f)
        return None
''',
    SYSTEM / "update" / "manager.py": '''"""Main Update Manager."""
from .source import UpdateSource
from .github_pages import GitHubPagesSource
from .cache import UpdateCache
from .version import RJOS_VERSION, compare_versions

class UpdateManager:
    def __init__(self, source: UpdateSource = None):
        self.source = source or GitHubPagesSource()
        self.cache = UpdateCache()

    def check_for_updates(self, channel="stable"):
        latest = self.source.get_latest(channel)
        if latest:
            self.cache.save_latest(latest)
            avail_version = latest.get("version")
            if compare_versions(RJOS_VERSION, avail_version) < 0:
                return latest
        return None
    
    def get_release_info(self, channel="stable", version=None):
        if not version:
            latest = self.cache.get_latest()
            if not latest: return None
            version = latest["version"]
        return self.source.get_release(channel, version)
''',
    SYSTEM / "update" / "history.py": '''"""Update History."""
import json
import datetime
from pathlib import Path

HISTORY_FILE = Path.home() / ".config" / "rjos" / "update_history.json"

class UpdateHistory:
    def __init__(self):
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not HISTORY_FILE.exists():
            with open(HISTORY_FILE, "w") as f:
                json.dump([], f)

    def add_entry(self, version, status, packages=None, error=None):
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
        
        entry = {
            "version": version,
            "date": datetime.datetime.now().isoformat(),
            "status": status,
            "packages": packages or [],
            "error": error
        }
        history.append(entry)
        
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
''',
    SYSTEM / "update" / "rjpm.py": '''"""RJPM Wrapper abstraction."""
import subprocess

class RjpmWrapper:
    """Wrapper to interact with the system package manager (rjpm -> apt)."""
    
    @staticmethod
    def update_package(package_name):
        # Emulating an rjpm call. In real RJOS, this calls `rjpm update <pkg>`
        # For now, it will just be a simulated stub or pass-through.
        # rjpm usually would wrap apt/dpkg.
        print(f"[rjpm] Updating {package_name}...")
        try:
            # We use sudo apt-get install --only-upgrade as a fallback/example
            return subprocess.call(["sudo", "apt-get", "install", "--only-upgrade", "-y", package_name])
        except FileNotFoundError:
            print("[rjpm] apt not found. Simulation mode.")
            return 0
''',
    SYSTEM / "cli" / "rjos-update": '''#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

# Add system dir to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from update.manager import UpdateManager
from update.version import RJOS_VERSION
from update.rjpm import RjpmWrapper
from update.history import UpdateHistory

def main():
    parser = argparse.ArgumentParser(description="RJOS Update CLI")
    parser.add_argument("command", choices=["check", "status", "info", "install", "history"])
    args = parser.parse_args()

    manager = UpdateManager()

    if args.command == "check":
        print(f"RJOS Update Manager")
        print(f"Versão instalada: {RJOS_VERSION}")
        print("Verificando atualizações...")
        latest = manager.check_for_updates()
        if latest:
            print(f"Nova versão disponível: {latest['version']}")
            print("Execute 'rjos-update info' para mais detalhes.")
        else:
            print("Sistema já está atualizado.")
            
    elif args.command == "info":
        info = manager.get_release_info()
        if info:
            print(f"Informações da atualização {info.get('version')}:")
            print(f"Tipo: {info.get('type')}")
            print(f"Descrição: {info.get('description')}")
            print(f"Changelog:")
            for c in info.get('changes', []):
                print(f" - {c}")
        else:
            print("Nenhuma informação disponível. Execute 'rjos-update check' primeiro.")

    elif args.command == "install":
        info = manager.get_release_info()
        if not info:
            print("Nenhuma atualização pendente.")
            return
            
        print(f"Instalando atualização {info['version']}...")
        history = UpdateHistory()
        success = True
        
        for pkg in info.get('packages', []):
            name = pkg['name']
            if RjpmWrapper.update_package(name) != 0:
                success = False
                break
                
        if success:
            print("Atualização concluída com sucesso.")
            history.add_entry(info['version'], "Atualização concluída", info.get('packages'))
        else:
            print("Erro ao atualizar.")
            history.add_entry(info['version'], "Erro", error="Falha ao instalar pacotes")

    elif args.command == "history":
        history = UpdateHistory()
        import json
        with open(history.HISTORY_FILE, "r") as f:
            data = json.load(f)
            for entry in reversed(data):
                print(f"{entry['version']} - {entry['date'][:10]} - {entry['status']}")

if __name__ == "__main__":
    main()
''',
    SYSTEM / "daemon" / "rjos-update-daemon": '''#!/usr/bin/env python3
import sys
import time
import subprocess
from pathlib import Path

# Add system dir to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from update.manager import UpdateManager

def notify(title, message):
    try:
        subprocess.run(["notify-send", "-a", "RJOS Update", title, message])
    except FileNotFoundError:
        pass

def main():
    manager = UpdateManager()
    latest = manager.check_for_updates()
    
    if latest:
        v = latest["version"]
        notify("Atualização disponível", f"RJOS {v} está disponível.\\nAbra o Update Center para instalar.")

if __name__ == "__main__":
    main()
''',
    DESKTOP / "update" / "update_center.py": '''#!/usr/bin/env python3
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
                changes = "\\n".join([f" ✓ {c}" for c in info.get("changes", [])])
                self.info_label.set_text(f"{desc}\\n\\nEsta atualização contém:\\n{changes}")
            
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
''',
}

for path, content in FILES.items():
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

print("Created all files successfully.")
