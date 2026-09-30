#!/usr/bin/env python3
# =============================================================================
# RJOS Wallpaper Manager — wallpaper_manager.py
# Gerenciador de wallpapers do RJOS
#
# Permite selecionar wallpapers inclusos, carregar imagens personalizadas,
# com preview em tempo real e suporte a slideshow.
#
# Dependências:
#   python3-gi (PyGObject), gir1.2-gtk-4.0, gir1.2-adw-1
#   swaybg (para definir wallpaper no Wayland)
# =============================================================================

import gi
import os
import subprocess
import json
import shutil
from pathlib import Path

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gdk, GdkPixbuf, Gio

# ─── Constantes ───────────────────────────────────────────────────────────────

WALLPAPER_DIR_SYSTEM  = Path("/usr/share/rjos/wallpapers")
WALLPAPER_DIR_PROJECT = Path(__file__).resolve().parent.parent / "wallpapers"
WALLPAPER_DIR_USER    = Path.home() / ".config" / "rjos" / "wallpapers"
WALLPAPER_CONFIG      = Path.home() / ".config" / "rjos" / "wallpaper.json"
THUMBNAIL_SIZE        = 200

# ─── CSS ──────────────────────────────────────────────────────────────────────

try:
    from rjos_theme import apply_rjos_theme_provider
except ImportError:
    apply_rjos_theme_provider = None

WALLPAPER_CSS = """
/* ══════════════════════════════════════════════════════════════════
   RJOS Wallpaper Manager — Estilos Oficiais RJOS
   ══════════════════════════════════════════════════════════════════ */

.rjos-wm-window {
    background-color: @rjos-bg;
}

.rjos-wm-header {
    background-color: @rjos-surface;
    border-bottom: 1px solid @rjos-surface-border;
    padding: 12px 16px;
}

.rjos-wm-title {
    color: @rjos-text;
    font-size: 16px;
    font-weight: 600;
}

.rjos-wm-subtitle {
    color: @rjos-text-secondary;
    font-size: 12px;
    font-weight: 400;
}

.rjos-wm-grid {
    padding: 16px;
}

.rjos-wm-thumb {
    background-color: @rjos-surface;
    border: 2px solid @rjos-surface-border;
    border-radius: var(--rjos-radius-md);
    padding: 4px;
    min-width: 180px;
    min-height: 110px;
    transition: var(--rjos-transition-fast);
}

.rjos-wm-thumb:hover {
    background-color: @rjos-surface-hover;
    border-color: @rjos-blue-dim;
    box-shadow: var(--rjos-shadow-md);
}

.rjos-wm-thumb-active {
    border-color: @rjos-blue;
    box-shadow: 0 0 10px @rjos-blue-dim;
}

.rjos-wm-thumb-label {
    color: @rjos-text-secondary;
    font-size: 11px;
    font-weight: 500;
    margin-top: 4px;
}

/* Preview grande */
.rjos-wm-preview {
    background-color: @rjos-surface;
    border: 1px solid @rjos-surface-border;
    border-radius: var(--rjos-radius-lg);
    padding: 8px;
    margin: 12px 16px;
}

/* Opções de exibição */
.rjos-wm-options {
    background-color: @rjos-surface;
    border: 1px solid @rjos-surface-border;
    border-radius: var(--rjos-radius-lg);
    padding: 12px 16px;
    margin: 0 16px;
}

.rjos-wm-option-label {
    color: @rjos-text;
    font-size: 13px;
    font-weight: 500;
}

.rjos-wm-option-desc {
    color: @rjos-text-secondary;
    font-size: 11px;
}

/* Barra de ações */
.rjos-wm-actions {
    padding: 12px 16px;
    border-top: 1px solid @rjos-surface-border;
    background-color: @rjos-surface;
}

.rjos-wm-btn-apply {
    background-color: @rjos-blue;
    color: @rjos-text;
    border: none;
    border-radius: var(--rjos-radius-md);
    padding: 8px 24px;
    font-weight: 600;
    font-size: 13px;
    transition: var(--rjos-transition-fast);
}

.rjos-wm-btn-apply:hover {
    background-color: @rjos-blue-hover;
}

.rjos-wm-btn-apply:active {
    background-color: @rjos-blue-active;
}

.rjos-wm-btn-add {
    background-color: @rjos-surface;
    border: 1px dashed rgba(255, 255, 255, 0.16);
    border-radius: var(--rjos-radius-md);
    color: @rjos-text-secondary;
    font-size: 24px;
    min-width: 180px;
    min-height: 110px;
    transition: var(--rjos-transition-fast);
}

.rjos-wm-btn-add:hover {
    border-color: @rjos-blue;
    color: @rjos-blue;
    background-color: @rjos-surface-hover;
}

/* Slideshow */
.rjos-wm-slideshow-row {
    background-color: @rjos-surface;
    border: 1px solid @rjos-surface-border;
    border-radius: var(--rjos-radius-lg);
    padding: 12px 16px;
    margin: 8px 16px;
}
"""

# Wallpapers temáticos do Rio de Janeiro
BUILTIN_WALLPAPERS = [
    {"name": "Pão de Açúcar (Padrão)", "color": "#121212",
     "gradient": "linear-gradient(135deg, #0a0a0a, #121212 50%, #005B96 100%)"},
    {"name": "Morro Dois Irmãos",     "color": "#121212",
     "gradient": "linear-gradient(180deg, #121212 60%, #005B96 100%)"},
    {"name": "Baía de Guanabara",     "color": "#005B96",
     "gradient": "linear-gradient(135deg, #121212, #00385c, #005B96)"},
    {"name": "Calçadão Copacabana",   "color": "#1E1E1E",
     "gradient": "linear-gradient(135deg, #121212, #1E1E1E 60%, #292929)"},
    {"name": "Azul Oceano",           "color": "#005B96",
     "gradient": "linear-gradient(135deg, #002844, #005B96, #004370)"},
    {"name": "Verde Floresta Tijuca", "color": "#00A86B",
     "gradient": "linear-gradient(135deg, #0c1f15, #004d31, #00A86B)"},
    {"name": "Carvão Minimalista",    "color": "#121212",
     "gradient": "linear-gradient(135deg, #0d0d0d, #121212, #1a1a1a)"},
]


class RjosWallpaperManager(Gtk.Window):
    """Gerenciador de Wallpapers do RJOS"""

    def __init__(self, app=None):
        super().__init__()
        self.app = app
        self.wallpapers = []
        self.selected_wallpaper = None
        self.current_wallpaper = None
        self.fill_mode = "fill"  # fill, fit, center, stretch, tile

        self.set_decorated(True)
        self.set_resizable(True)
        self.set_default_size(680, 560)
        self.set_title("Wallpaper — RJOS")
        self.add_css_class("rjos-wm-window")

        self._load_config()
        self._scan_wallpapers()
        self._build_ui()

    def _load_config(self):
        """Carrega configuração atual do wallpaper"""
        try:
            if WALLPAPER_CONFIG.exists():
                with open(WALLPAPER_CONFIG, "r") as f:
                    data = json.load(f)
                    self.current_wallpaper = data.get("path")
                    self.fill_mode = data.get("mode", "fill")
        except Exception:
            pass

    def _save_config(self):
        """Salva configuração do wallpaper"""
        try:
            WALLPAPER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "path": self.selected_wallpaper,
                "mode": self.fill_mode,
            }
            with open(WALLPAPER_CONFIG, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[wallpaper] Erro ao salvar config: {e}")

    def _scan_wallpapers(self):
        """Escaneia wallpapers disponíveis"""
        self.wallpapers = []

        # Wallpapers do sistema e do projeto
        search_dirs = [WALLPAPER_DIR_PROJECT, WALLPAPER_DIR_SYSTEM, WALLPAPER_DIR_USER]
        seen_paths = set()
        for wdir in search_dirs:
            if wdir.exists():
                for f in sorted(wdir.glob("*")):
                    if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".svg") and str(f) not in seen_paths:
                        seen_paths.add(str(f))
                        self.wallpapers.append({
                            "name": f.stem.replace("-", " ").replace("_", " ").title(),
                            "path": str(f),
                            "type": "image",
                        })
        WALLPAPER_DIR_USER.mkdir(parents=True, exist_ok=True)
        if WALLPAPER_DIR_USER.exists():
            for f in sorted(WALLPAPER_DIR_USER.glob("*")):
                if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                    self.wallpapers.append({
                        "name": f.stem.replace("-", " ").replace("_", " ").title(),
                        "path": str(f),
                        "type": "image",
                    })

        # Adiciona wallpapers sólidos/gradientes como fallback
        for wp in BUILTIN_WALLPAPERS:
            self.wallpapers.append({
                "name": wp["name"],
                "color": wp["color"],
                "type": "color",
            })

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # ── Header ──
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.add_css_class("rjos-wm-header")

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title = Gtk.Label(label="🖼️  Wallpaper")
        title.add_css_class("rjos-wm-title")
        title.set_halign(Gtk.Align.START)
        title_box.append(title)

        subtitle = Gtk.Label(
            label=f"{len(self.wallpapers)} wallpapers disponíveis"
        )
        subtitle.add_css_class("rjos-wm-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        title_box.append(subtitle)

        header.append(title_box)
        main_box.append(header)

        # ── Grid de wallpapers (scrollável) ──
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(4)
        flow.set_min_children_per_line(2)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_homogeneous(True)
        flow.add_css_class("rjos-wm-grid")

        for wp in self.wallpapers:
            widget = self._create_wallpaper_thumb(wp)
            flow.append(widget)

        # Botão de adicionar
        add_btn = Gtk.Button(label="＋")
        add_btn.add_css_class("rjos-wm-btn-add")
        add_btn.set_tooltip_text("Adicionar wallpaper")
        add_btn.connect("clicked", self._on_add_wallpaper)
        flow.append(add_btn)

        scroll.set_child(flow)
        main_box.append(scroll)

        # ── Opções de modo ──
        options = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        options.add_css_class("rjos-wm-options")

        opt_label = Gtk.Label(label="Modo de exibição:")
        opt_label.add_css_class("rjos-wm-option-label")
        options.append(opt_label)

        modes = ["Preencher", "Ajustar", "Centralizar", "Esticar", "Lado a lado"]
        mode_keys = ["fill", "fit", "center", "stretch", "tile"]

        self.mode_combo = Gtk.DropDown.new_from_strings(modes)
        try:
            idx = mode_keys.index(self.fill_mode)
            self.mode_combo.set_selected(idx)
        except ValueError:
            self.mode_combo.set_selected(0)
        self.mode_combo.connect("notify::selected", self._on_mode_changed)
        options.append(self.mode_combo)

        main_box.append(options)

        # ── Barra de ações ──
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.add_css_class("rjos-wm-actions")
        actions.set_halign(Gtk.Align.END)

        cancel_btn = Gtk.Button(label="Cancelar")
        cancel_btn.add_css_class("rjos-ctx-item")
        cancel_btn.connect("clicked", lambda b: self.close())
        actions.append(cancel_btn)

        apply_btn = Gtk.Button(label="Aplicar")
        apply_btn.add_css_class("rjos-wm-btn-apply")
        apply_btn.connect("clicked", self._on_apply)
        actions.append(apply_btn)

        main_box.append(actions)
        self.set_child(main_box)

    def _create_wallpaper_thumb(self, wp):
        """Cria thumbnail de um wallpaper"""
        btn = Gtk.Button()
        btn.add_css_class("rjos-wm-thumb")

        if self.current_wallpaper and wp.get("path") == self.current_wallpaper:
            btn.add_css_class("rjos-wm-thumb-active")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_halign(Gtk.Align.CENTER)

        if wp["type"] == "image" and os.path.exists(wp["path"]):
            # Thumbnail da imagem
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    wp["path"], THUMBNAIL_SIZE, THUMBNAIL_SIZE // 2, True
                )
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                image = Gtk.Picture.new_for_paintable(texture)
                image.set_content_fit(Gtk.ContentFit.COVER)
                image.set_size_request(THUMBNAIL_SIZE, THUMBNAIL_SIZE // 2)
                vbox.append(image)
            except Exception:
                # Fallback para label
                placeholder = Gtk.Label(label="🖼️")
                placeholder.set_size_request(THUMBNAIL_SIZE, THUMBNAIL_SIZE // 2)
                vbox.append(placeholder)
        else:
            # Cor sólida / gradiente
            color_box = Gtk.Box()
            color_box.set_size_request(THUMBNAIL_SIZE, THUMBNAIL_SIZE // 2)

            # Aplica cor via CSS
            color = wp.get("color", "#0D1B2A")
            provider = Gtk.CssProvider()
            provider.load_from_string(
                f"box {{ background-color: {color}; border-radius: 6px; }}"
            )
            color_box.get_style_context().add_provider(
                provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            vbox.append(color_box)

        # Nome
        name_lbl = Gtk.Label(label=wp["name"][:20])
        name_lbl.add_css_class("rjos-wm-thumb-label")
        vbox.append(name_lbl)

        btn.set_child(vbox)
        btn.connect("clicked", self._on_wallpaper_selected, wp)
        return btn

    # ── Handlers ──

    def _on_wallpaper_selected(self, btn, wp):
        """Seleciona um wallpaper"""
        if wp["type"] == "image":
            self.selected_wallpaper = wp["path"]
        else:
            self.selected_wallpaper = wp.get("color", "#0D1B2A")
        print(f"[wallpaper] Selecionado: {wp['name']}")

    def _on_mode_changed(self, dropdown, pspec):
        modes = ["fill", "fit", "center", "stretch", "tile"]
        idx = dropdown.get_selected()
        if 0 <= idx < len(modes):
            self.fill_mode = modes[idx]

    def _on_add_wallpaper(self, btn):
        """Abre seletor de arquivo para adicionar wallpaper"""
        dialog = Gtk.FileDialog()
        dialog.set_title("Selecionar Wallpaper")

        # Filtro de imagens
        filter_images = Gtk.FileFilter()
        filter_images.set_name("Imagens")
        filter_images.add_mime_type("image/jpeg")
        filter_images.add_mime_type("image/png")
        filter_images.add_mime_type("image/webp")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_images)
        dialog.set_filters(filters)

        dialog.open(self, None, self._on_file_selected)

    def _on_file_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                src = file.get_path()
                # Copia para pasta do usuário
                WALLPAPER_DIR_USER.mkdir(parents=True, exist_ok=True)
                dst = WALLPAPER_DIR_USER / Path(src).name
                shutil.copy2(src, dst)
                print(f"[wallpaper] Copiado: {src} → {dst}")

                self.selected_wallpaper = str(dst)
                self._scan_wallpapers()
                # TODO: Rebuild UI
        except Exception as e:
            print(f"[wallpaper] Erro ao adicionar: {e}")

    def _on_apply(self, btn):
        """Aplica o wallpaper selecionado"""
        if not self.selected_wallpaper:
            return

        self._save_config()

        # Mata swaybg anterior
        subprocess.run(["pkill", "swaybg"], capture_output=True)

        if self.selected_wallpaper.startswith("#"):
            # Cor sólida
            subprocess.Popen(
                ["swaybg", "-c", self.selected_wallpaper],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            # Imagem
            subprocess.Popen(
                ["swaybg", "-i", self.selected_wallpaper, "-m", self.fill_mode],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        print(f"[wallpaper] Aplicado: {self.selected_wallpaper} (modo: {self.fill_mode})")
        self.close()


# ─── Executável standalone ────────────────────────────────────────────────────

class RjosWallpaperApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="org.rjos.wallpaper-manager",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        if apply_rjos_theme_provider:
            apply_rjos_theme_provider(WALLPAPER_CSS)
        else:
            provider = Gtk.CssProvider()
            provider.load_from_string(WALLPAPER_CSS)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

        win = RjosWallpaperManager(app)
        win.set_application(app)
        win.present()


def main():
    app = RjosWallpaperApp()
    return app.run(sys.argv if 'sys' in dir() else [])


if __name__ == "__main__":
    import sys
    sys.exit(main())
