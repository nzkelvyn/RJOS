#!/usr/bin/env python3
# =============================================================================
# RJOS Settings — rjos-settings.py
# Central de Configurações do RJOS
#
# Categorias:
#   Sistema, Aparência, Rede, Tela, Som, Teclado, Mouse, Energia,
#   Armazenamento, Usuários, Privacidade, Segurança, Aplicativos, Atualizações
# =============================================================================

import gi
import os
import sys
import signal
import subprocess
import json
from pathlib import Path

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Gio

RJOS_SETTINGS_CSS = """
.rjos-settings-sidebar {
    background-color: #1E1E1E;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
    min-width: 220px;
}
.rjos-settings-nav-item {
    border-radius: 8px;
    margin: 2px 8px;
    padding: 10px 14px;
    color: #B8B8B8;
    font-size: 13px;
    transition: all 120ms ease;
}
.rjos-settings-nav-item:hover {
    background-color: #292929;
    color: #FFFFFF;
}
.rjos-settings-nav-item.active {
    background-color: rgba(0, 91, 150, 0.22);
    color: #FFFFFF;
    border-left: 3px solid #005B96;
    font-weight: 600;
}
.rjos-settings-section-title {
    color: #757575;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 12px 16px 4px 16px;
    text-transform: uppercase;
}
.rjos-settings-content {
    background-color: #121212;
}
.rjos-settings-page-title {
    color: #FFFFFF;
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 16px;
}
.rjos-settings-group {
    background-color: #1E1E1E;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    margin-bottom: 16px;
    overflow: hidden;
}
.rjos-settings-row {
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    padding: 14px 16px;
    transition: background-color 100ms ease;
}
.rjos-settings-row:last-child {
    border-bottom: none;
}
.rjos-settings-row:hover {
    background-color: #292929;
}
.rjos-settings-row-title {
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 500;
}
.rjos-settings-row-subtitle {
    color: #B8B8B8;
    font-size: 11px;
    margin-top: 2px;
}
.rjos-toggle {
    margin: 0;
}
"""

# ─── Páginas de configuração ──────────────────────────────────────────────────

CATEGORIES = [
    ("Sistema",      "💻", "system"),
    ("Aparência",    "🎨", "appearance"),
    ("Rede e Wi-Fi", "🌐", "network"),
    ("Tela",         "🖥️", "display"),
    ("Som",          "🔊", "sound"),
    ("Teclado",      "⌨️", "keyboard"),
    ("Mouse",        "🖱️", "mouse"),
    ("Energia",      "⚡", "power"),
    ("Armazenamento","💾", "storage"),
    ("Usuários",     "👤", "users"),
    ("Privacidade",  "🔐", "privacy"),
    ("Segurança",    "🛡️", "security"),
    ("Aplicativos",  "📦", "apps"),
    ("Atualizações", "🔄", "updates"),
]


class SettingsRow(Gtk.Box):
    """Uma linha de configuração com título, subtítulo e widget de controle."""
    def __init__(self, title, subtitle=None, control=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.add_css_class("rjos-settings-row")
        self.set_hexpand(True)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_hexpand(True)
        text_box.set_valign(Gtk.Align.CENTER)

        title_label = Gtk.Label(label=title)
        title_label.add_css_class("rjos-settings-row-title")
        title_label.set_halign(Gtk.Align.START)
        text_box.append(title_label)

        if subtitle:
            sub_label = Gtk.Label(label=subtitle)
            sub_label.add_css_class("rjos-settings-row-subtitle")
            sub_label.set_halign(Gtk.Align.START)
            text_box.append(sub_label)

        self.append(text_box)

        if control:
            control.set_valign(Gtk.Align.CENTER)
            self.append(control)


def make_group(*rows):
    """Cria um grupo de configurações."""
    group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    group.add_css_class("rjos-settings-group")
    for row in rows:
        group.append(row)
    return group


def make_toggle(active=False, callback=None):
    sw = Gtk.Switch()
    sw.add_css_class("rjos-toggle")
    sw.set_active(active)
    if callback:
        sw.connect("state-set", callback)
    return sw


def make_spin(value, min_val, max_val, step=1):
    adj = Gtk.Adjustment(value=value, lower=min_val, upper=max_val,
                         step_increment=step)
    spin = Gtk.SpinButton(adjustment=adj, climb_rate=1, digits=0)
    return spin


def make_combo(options, active_idx=0, callback=None):
    combo = Gtk.DropDown()
    model = Gtk.StringList(strings=options)
    combo.set_model(model)
    combo.set_selected(active_idx)
    if callback:
        combo.connect("notify::selected", callback)
    return combo


# ─── Páginas individuais ──────────────────────────────────────────────────────

def build_system_page():
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_vexpand(True)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.set_margin_start(32)
    box.set_margin_end(32)
    box.set_margin_top(24)
    box.set_margin_bottom(24)

    title = Gtk.Label(label="Sistema")
    title.add_css_class("rjos-settings-page-title")
    title.set_halign(Gtk.Align.START)
    box.append(title)

    # Info do sistema
    try:
        import platform
        kernel = platform.release()
        arch   = platform.machine()
        hostname = platform.node()
    except Exception:
        kernel = hostname = arch = "N/A"

    info_group = make_group(
        SettingsRow("Distribuição",   "RJOS 1.0 (Debian base)"),
        SettingsRow("Kernel",         kernel),
        SettingsRow("Arquitetura",    arch),
        SettingsRow("Hostname",       hostname),
    )
    box.append(info_group)

    # Hardware
    cpu_info = "N/A"
    ram_info = "N/A"
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "model name" in line:
                    cpu_info = line.split(":")[1].strip()
                    break
        with open("/proc/meminfo") as f:
            for line in f:
                if "MemTotal" in line:
                    kb = int(line.split()[1])
                    ram_info = f"{kb // 1024} MB"
                    break
    except Exception:
        pass

    hw_group = make_group(
        SettingsRow("Processador",  cpu_info),
        SettingsRow("Memória RAM",  ram_info),
    )
    box.append(hw_group)

    # Configurações gerais
    general_group = make_group(
        SettingsRow("Login automático",
                    "Entrar sem digitar senha",
                    make_toggle(False)),
        SettingsRow("Inicialização rápida",
                    "Reduz o tempo de boot",
                    make_toggle(True)),
    )
    box.append(general_group)

    scroll.set_child(box)
    return scroll


# ─── Constantes de tema ───────────────────────────────────────────────────────

ACCENT_OPTIONS = [
    # (label exibido, nome interno para rjos-theme, cor hex)
    ("Azul Oceano (Oficial) #005B96", "ocean",  "#005B96"),
    ("Verde Tropical #00A86B",        "green",  "#00A86B"),
    ("Amarelo Sol    #F2C94C",        "yellow", "#F2C94C"),
    ("Azul Royal     #2979FF",        "blue",   "#2979FF"),
    ("Ciano          #00D4FF",        "cyan",   "#00D4FF"),
    ("Roxo           #7B2FBE",        "purple", "#7B2FBE"),
]

STYLE_OPTIONS = [
    ("RJOS Dark (padrão)", "dark"),
    ("RJOS Light",         "light"),
    ("RJOS OLED",          "oled"),
]


def _rjos_theme(*args):
    """Chama rjos-theme com os argumentos dados."""
    try:
        cmd = ["rjos-theme"] + list(args)
        subprocess.Popen(cmd, start_new_session=True)
    except FileNotFoundError:
        # Fallback: executa o script diretamente do repositório
        script = Path(__file__).parent.parent.parent / "system" / "rjos-theme" / "rjos-theme"
        if script.exists():
            cmd = ["bash", str(script)] + list(args)
            subprocess.Popen(cmd, start_new_session=True)


def _load_theme_config() -> dict:
    """Lê ~/.config/rjos/theme.json e retorna o dicionário."""
    config_path = Path.home() / ".config" / "rjos" / "theme.json"
    defaults = {
        "accent": "cyan",
        "style": "dark",
        "font": "Inter 13",
        "mono_font": "JetBrains Mono 12",
        "transparency": True,
        "animations": True,
    }
    if config_path.exists():
        try:
            with open(config_path) as f:
                data = json.load(f)
            defaults.update(data)
        except Exception:
            pass
    return defaults


def _save_theme_config(key: str, value):
    """Salva uma chave no theme.json diretamente (sem depender do daemon)."""
    config_dir  = Path.home() / ".config" / "rjos"
    config_path = config_dir / "theme.json"
    config_dir.mkdir(parents=True, exist_ok=True)
    cfg = _load_theme_config()
    cfg[key] = value
    with open(config_path, "w") as f:
        json.dump(cfg, f, indent=2)


def _preview_color(hex_color: str) -> Gtk.Widget:
    """Cria um pequeno círculo colorido para pré-visualização."""
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    swatch = Gtk.DrawingArea()
    swatch.set_size_request(18, 18)
    swatch.set_valign(Gtk.Align.CENTER)
    # Adiciona CSS inline para a cor
    provider = Gtk.CssProvider()
    provider.load_from_string(
        f".rjos-swatch-{hex_color[1:]} {{ background:{hex_color}; border-radius:50%; "
        f"border:2px solid rgba(255,255,255,0.2); }}"
    )
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
    swatch.add_css_class(f"rjos-swatch-{hex_color[1:]}")
    return swatch


def build_appearance_page():
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_vexpand(True)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.set_margin_start(32); box.set_margin_end(32)
    box.set_margin_top(24);   box.set_margin_bottom(24)

    title = Gtk.Label(label="Aparência")
    title.add_css_class("rjos-settings-page-title")
    title.set_halign(Gtk.Align.START)
    box.append(title)

    # ── Carrega config atual ──────────────────────────────────────────────────
    cfg = _load_theme_config()

    # ── Estilo (dark / light / oled) ─────────────────────────────────────────
    style_labels  = [s[0] for s in STYLE_OPTIONS]
    style_names   = [s[1] for s in STYLE_OPTIONS]
    style_idx     = style_names.index(cfg.get("style", "dark")) \
                    if cfg.get("style", "dark") in style_names else 0

    style_combo = make_combo(style_labels, active_idx=style_idx)

    def on_style_changed(combo, _param):
        idx  = combo.get_selected()
        name = style_names[idx]
        _save_theme_config("style", name)
        _rjos_theme("set-style", name)

    style_combo.connect("notify::selected", on_style_changed)

    # ── Cor de destaque ───────────────────────────────────────────────────────
    accent_labels = [a[0] for a in ACCENT_OPTIONS]
    accent_names  = [a[1] for a in ACCENT_OPTIONS]
    accent_hexes  = [a[2] for a in ACCENT_OPTIONS]
    current_accent = cfg.get("accent", "cyan")
    accent_idx     = accent_names.index(current_accent) \
                     if current_accent in accent_names else 0

    accent_combo = make_combo(accent_labels, active_idx=accent_idx)

    # Label de preview que mostra a cor atual
    accent_preview_label = Gtk.Label(label=accent_hexes[accent_idx])
    accent_preview_label.add_css_class("rjos-settings-row-subtitle")

    # Caixa com combo + preview
    accent_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    accent_box.set_valign(Gtk.Align.CENTER)
    accent_box.append(accent_combo)
    accent_box.append(accent_preview_label)

    def on_accent_changed(combo, _param):
        idx      = combo.get_selected()
        name     = accent_names[idx]
        hex_col  = accent_hexes[idx]
        # Atualiza preview label
        accent_preview_label.set_text(hex_col)
        # Salva + aplica
        _save_theme_config("accent", name)
        _rjos_theme("set-accent", name)

    accent_combo.connect("notify::selected", on_accent_changed)

    # ── Transparência ──────────────────────────────────────────────────────────
    def on_transparency_changed(sw, state):
        _save_theme_config("transparency", state)
        _rjos_theme("set-transparency", "true" if state else "false")
        return False

    transparency_toggle = make_toggle(
        active=cfg.get("transparency", True),
        callback=on_transparency_changed
    )

    # ── Animações ─────────────────────────────────────────────────────────────
    def on_animations_changed(sw, state):
        _save_theme_config("animations", state)
        # Aplica via gsettings (GTK respeita gtk-enable-animations)
        try:
            subprocess.Popen(
                ["gsettings", "set", "org.gnome.desktop.interface",
                 "enable-animations", "true" if state else "false"],
                start_new_session=True
            )
        except FileNotFoundError:
            pass
        return False

    animations_toggle = make_toggle(
        active=cfg.get("animations", True),
        callback=on_animations_changed
    )

    theme_group = make_group(
        SettingsRow("Estilo",         "Tema da interface",                style_combo),
        SettingsRow("Cor de destaque", "Cor principal da interface",       accent_box),
        SettingsRow("Transparência",   "Efeito glassmorphism nos painéis", transparency_toggle),
        SettingsRow("Animações",       "Transições de janela e elementos", animations_toggle),
    )
    box.append(theme_group)

    # ── Botão de cor personalizada ─────────────────────────────────────────────
    custom_color_btn = Gtk.ColorButton()
    custom_color_btn.set_title("Cor de destaque personalizada")
    custom_color_btn.set_tooltip_text("Escolha uma cor personalizada")
    custom_color_btn.set_valign(Gtk.Align.CENTER)

    # Define a cor atual no seletor
    try:
        current_hex = accent_hexes[accent_idx]
        r = int(current_hex[1:3], 16) / 255
        g = int(current_hex[3:5], 16) / 255
        b = int(current_hex[5:7], 16) / 255
        rgba = Gdk.RGBA()
        rgba.red = r; rgba.green = g; rgba.blue = b; rgba.alpha = 1.0
        custom_color_btn.set_rgba(rgba)
    except Exception:
        pass

    def on_custom_color_set(btn):
        rgba = btn.get_rgba()
        r = int(rgba.red   * 255)
        g = int(rgba.green * 255)
        b = int(rgba.blue  * 255)
        hex_color = f"#{r:02X}{g:02X}{b:02X}"
        _save_theme_config("accent", hex_color)
        _rjos_theme("set-accent", hex_color)
        accent_preview_label.set_text(hex_color)

    custom_color_btn.connect("color-set", on_custom_color_set)

    custom_group = make_group(
        SettingsRow("Cor personalizada",
                    "Escolha qualquer cor de destaque",
                    custom_color_btn)
    )
    box.append(custom_group)

    # ── Fonte da interface ─────────────────────────────────────────────────────
    font_btn = Gtk.FontButton()
    font_btn.set_font(cfg.get("font", "Inter 13"))
    font_btn.set_valign(Gtk.Align.CENTER)

    def on_font_set(btn):
        font = btn.get_font()
        _save_theme_config("font", font)
        _rjos_theme("set-font", font)
        # gsettings direto
        try:
            subprocess.Popen(
                ["gsettings", "set", "org.gnome.desktop.interface",
                 "font-name", font],
                start_new_session=True
            )
        except FileNotFoundError:
            pass

    font_btn.connect("font-set", on_font_set)

    mono_btn = Gtk.FontButton()
    mono_btn.set_font(cfg.get("mono_font", "JetBrains Mono 12"))
    mono_btn.set_valign(Gtk.Align.CENTER)

    def on_mono_set(btn):
        font = btn.get_font()
        _save_theme_config("mono_font", font)
        _rjos_theme("set-mono", font)
        try:
            subprocess.Popen(
                ["gsettings", "set", "org.gnome.desktop.interface",
                 "monospace-font-name", font],
                start_new_session=True
            )
        except FileNotFoundError:
            pass

    mono_btn.connect("font-set", on_mono_set)

    font_group = make_group(
        SettingsRow("Fonte da interface", cfg.get("font", "Inter 13"),           font_btn),
        SettingsRow("Fonte do terminal",  cfg.get("mono_font", "JetBrains Mono 12"), mono_btn),
    )
    box.append(font_group)

    # ── Papel de parede ───────────────────────────────────────────────────────
    wallpaper_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    wallpaper_box.add_css_class("rjos-settings-row")

    wp_title = Gtk.Label(label="Papel de Parede")
    wp_title.add_css_class("rjos-settings-row-title")
    wp_title.set_halign(Gtk.Align.START)
    wallpaper_box.append(wp_title)

    wp_sub = Gtk.Label(label="Imagem exibida no desktop (via swaybg)")
    wp_sub.add_css_class("rjos-settings-row-subtitle")
    wp_sub.set_halign(Gtk.Align.START)
    wallpaper_box.append(wp_sub)

    wp_btn = Gtk.Button(label="📁 Escolher imagem...")
    wp_btn.set_halign(Gtk.Align.START)
    wp_btn.set_margin_top(8)

    def on_wp_choose(b):
        dialog = Gtk.FileDialog()
        dialog.set_title("Escolher papel de parede")
        filter_images = Gtk.FileFilter()
        filter_images.set_name("Imagens")
        for pat in ["*.jpg", "*.jpeg", "*.png", "*.webp", "*.gif", "*.svg"]:
            filter_images.add_pattern(pat)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_images)
        dialog.set_filters(filters)
        dialog.open(None, None, _on_wp_file_chosen, None)

    def _on_wp_file_chosen(dialog, result, data):
        try:
            f    = dialog.open_finish(result)
            path = f.get_path()
            # Mata swaybg anterior
            subprocess.Popen(["pkill", "-f", "swaybg"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import time; time.sleep(0.2)
            # Inicia swaybg com a nova imagem
            subprocess.Popen(
                ["swaybg", "-i", path, "-m", "fill"],
                start_new_session=True
            )
            # Salva no config
            _save_theme_config("wallpaper", path)
        except Exception:
            pass

    wp_btn.connect("clicked", on_wp_choose)
    wallpaper_box.append(wp_btn)

    wp_group = make_group(wallpaper_box)
    box.append(wp_group)

    # ── Botão "Aplicar tudo" ──────────────────────────────────────────────────
    apply_btn = Gtk.Button(label="✅ Aplicar todas as configurações")
    apply_btn.add_css_class("suggested-action")
    apply_btn.set_margin_top(12)
    apply_btn.connect("clicked", lambda _: _rjos_theme("apply"))
    box.append(apply_btn)

    # ── Botão de reset ────────────────────────────────────────────────────────
    reset_btn = Gtk.Button(label="↩️ Restaurar padrão")
    reset_btn.set_margin_top(6)
    reset_btn.connect("clicked", lambda _: _rjos_theme("reset"))
    box.append(reset_btn)

    scroll.set_child(box)
    return scroll


def build_network_page():
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_vexpand(True)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.set_margin_start(32); box.set_margin_end(32)
    box.set_margin_top(24);   box.set_margin_bottom(24)

    title = Gtk.Label(label="Rede e Wi-Fi")
    title.add_css_class("rjos-settings-page-title")
    title.set_halign(Gtk.Align.START)
    box.append(title)

    # Status atual
    status_group = make_group(
        SettingsRow("Wi-Fi",
                    "Ativar ou desativar Wi-Fi",
                    make_toggle(True, lambda sw, state:
                        subprocess.Popen(["nmcli", "radio", "wifi",
                                          "on" if state else "off"]))),
        SettingsRow("Bluetooth",
                    "Ativar ou desativar Bluetooth",
                    make_toggle(False, lambda sw, state:
                        subprocess.Popen(["rfkill",
                                          "unblock" if state else "block",
                                          "bluetooth"]))),
        SettingsRow("Modo avião",
                    "Desativa todas as conexões sem fio",
                    make_toggle(False)),
    )
    box.append(status_group)

    # Redes disponíveis
    networks_title = Gtk.Label(label="Redes Wi-Fi disponíveis")
    networks_title.add_css_class("rjos-settings-section-title")
    networks_title.set_halign(Gtk.Align.START)
    box.append(networks_title)

    networks_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    networks_box.add_css_class("rjos-settings-group")

    # Carrega redes via nmcli
    def load_networks():
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,IN-USE",
                 "device", "wifi", "list"],
                capture_output=True, text=True, timeout=10
            )
            networks = []
            seen = set()
            for line in result.stdout.strip().split("\n"):
                parts = line.split(":")
                if len(parts) >= 4 and parts[0] and parts[0] not in seen:
                    seen.add(parts[0])
                    networks.append({
                        "ssid":     parts[0],
                        "signal":   int(parts[1]) if parts[1].isdigit() else 0,
                        "security": parts[2],
                        "active":   parts[3] == "*",
                    })
            return networks[:10]
        except Exception:
            return []

    def signal_icon(s):
        if s >= 75: return "📶"
        if s >= 50: return "📶"
        if s >= 25: return "📶"
        return "📶"

    networks = load_networks()
    if networks:
        for net in networks:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            row.add_css_class("rjos-settings-row")

            info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            info_box.set_hexpand(True)

            ssid_label = Gtk.Label(label=f"{signal_icon(net['signal'])} {net['ssid']}")
            ssid_label.add_css_class("rjos-settings-row-title")
            ssid_label.set_halign(Gtk.Align.START)
            info_box.append(ssid_label)

            sub = f"Sinal: {net['signal']}%"
            if net['security']:
                sub += f" • 🔒 {net['security']}"
            if net['active']:
                sub = "✅ Conectado • " + sub
            sub_label = Gtk.Label(label=sub)
            sub_label.add_css_class("rjos-settings-row-subtitle")
            sub_label.set_halign(Gtk.Align.START)
            info_box.append(sub_label)

            row.append(info_box)

            if not net["active"]:
                conn_btn = Gtk.Button(label="Conectar")
                conn_btn.set_valign(Gtk.Align.CENTER)
                conn_btn._ssid = net["ssid"]
                conn_btn.connect("clicked", lambda b:
                    subprocess.Popen(["nmcli", "device", "wifi",
                                      "connect", b._ssid]))
                row.append(conn_btn)
            else:
                disc_btn = Gtk.Button(label="Desconectar")
                disc_btn.set_valign(Gtk.Align.CENTER)
                disc_btn.connect("clicked", lambda b:
                    subprocess.Popen(["nmcli", "device", "disconnect", "wlan0"]))
                row.append(disc_btn)

            networks_box.append(row)
    else:
        no_net = Gtk.Label(label="Nenhuma rede encontrada\n(verifique se o Wi-Fi está ativado)")
        no_net.add_css_class("rjos-settings-row-subtitle")
        no_net.set_margin_top(12)
        no_net.set_margin_bottom(12)
        networks_box.append(no_net)

    box.append(networks_box)

    # Botão avançado
    adv_btn = Gtk.Button(label="⚙️ Configurações avançadas de rede")
    adv_btn.connect("clicked", lambda _:
        subprocess.Popen(["nm-connection-editor"], start_new_session=True))
    adv_btn.set_margin_top(8)
    box.append(adv_btn)

    scroll.set_child(box)
    return scroll


def build_display_page():
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_vexpand(True)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.set_margin_start(32); box.set_margin_end(32)
    box.set_margin_top(24);   box.set_margin_bottom(24)

    title = Gtk.Label(label="Tela")
    title.add_css_class("rjos-settings-page-title")
    title.set_halign(Gtk.Align.START)
    box.append(title)

    displays_group = make_group(
        SettingsRow("Resolução",
                    "Resolução do monitor principal",
                    make_combo(["1920×1080 (recomendado)", "2560×1440", "3840×2160",
                                "1280×720", "1366×768"])),
        SettingsRow("Taxa de atualização",
                    "Frames por segundo",
                    make_combo(["60 Hz", "75 Hz", "120 Hz", "144 Hz", "240 Hz"])),
        SettingsRow("Escala",
                    "Zoom da interface (HiDPI)",
                    make_combo(["100%", "125%", "150%", "200%"])),
        SettingsRow("Orientação",
                    "Rotação da tela",
                    make_combo(["Normal", "90° (horário)", "180°", "90° (anti-horário)"])),
        SettingsRow("Posição",
                    "Monitors lado a lado (use kanshi ou wlr-randr)",
                    None),
    )
    box.append(displays_group)

    # Botão para aplicar via wlr-randr
    apply_btn = Gtk.Button(label="✅ Aplicar configurações")
    apply_btn.set_margin_top(8)
    box.append(apply_btn)

    scroll.set_child(box)
    return scroll


def build_updates_page():
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_vexpand(True)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.set_margin_start(32); box.set_margin_end(32)
    box.set_margin_top(24);   box.set_margin_bottom(24)

    title = Gtk.Label(label="Atualizações")
    title.add_css_class("rjos-settings-page-title")
    title.set_halign(Gtk.Align.START)
    box.append(title)

    # Status
    status_group = make_group(
        SettingsRow("Última verificação",
                    "Execute 'rjos update' para verificar"),
        SettingsRow("Atualizações automáticas",
                    "Verificar atualizações automaticamente",
                    make_toggle(True)),
        SettingsRow("Atualizações de segurança",
                    "Instalar atualizações de segurança automaticamente",
                    make_toggle(True)),
    )
    box.append(status_group)

    # Botão atualizar
    update_btn = Gtk.Button(label="🔄 Verificar atualizações agora")
    update_btn.set_margin_top(8)

    self_output = Gtk.TextView()
    self_output.set_editable(False)
    self_output.set_monospace(True)
    self_output.set_visible(False)
    self_output.set_margin_top(12)

    def on_check_updates(btn):
        self_output.set_visible(True)
        buf = self_output.get_buffer()
        buf.set_text("Verificando atualizações...\n")
        btn.set_sensitive(False)

        def do_check():
            try:
                result = subprocess.run(
                    ["apt", "list", "--upgradable", "-q"],
                    capture_output=True, text=True, timeout=30
                )
                text = result.stdout or "Sistema atualizado! ✅"
            except Exception as e:
                text = f"Erro: {e}"

            GLib.idle_add(lambda: (
                buf.set_text(text),
                btn.set_sensitive(True),
            ))

        import threading
        threading.Thread(target=do_check, daemon=True).start()

    update_btn.connect("clicked", on_check_updates)
    box.append(update_btn)
    box.append(self_output)

    scroll.set_child(box)
    return scroll


def build_generic_page(name: str):
    """Página placeholder para categorias ainda em desenvolvimento."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.set_vexpand(True)
    box.set_valign(Gtk.Align.CENTER)
    box.set_halign(Gtk.Align.CENTER)
    box.set_spacing(8)

    icon = Gtk.Label(label="🔧")
    icon.set_css_classes(["rjos-settings-page-title"])

    label = Gtk.Label(label=f"Configurações de {name}")
    label.add_css_class("rjos-settings-page-title")

    sub = Gtk.Label(label="Esta seção está em desenvolvimento na Fase 4.")
    sub.add_css_class("rjos-settings-row-subtitle")

    box.append(icon)
    box.append(label)
    box.append(sub)
    return box


PAGE_BUILDERS = {
    "system":     build_system_page,
    "appearance": build_appearance_page,
    "network":    build_network_page,
    "display":    build_display_page,
    "updates":    build_updates_page,
}


# ─── Janela principal ────────────────────────────────────────────────────────

class RjosSettingsWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Configurações — RJOS")
        self.set_default_size(860, 600)
        self._build_ui()
        self._switch_page("system")

    def _build_ui(self):
        header = Adw.HeaderBar()
        header.add_css_class("rjos-titlebar") if hasattr(Gtk, "add_css_class") else None

        title_label = Gtk.Label(label="Configurações")
        header.set_title_widget(title_label)
        self.set_titlebar(header)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(230)

        # ── Sidebar ──
        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar_scroll.add_css_class("rjos-settings-sidebar")

        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar_box.set_margin_top(8)
        sidebar_box.set_margin_bottom(8)

        self._nav_buttons = {}

        for name, icon, page_id in CATEGORIES:
            btn = Gtk.Button(label=f"{icon}  {name}")
            btn.add_css_class("rjos-settings-nav-item")
            btn.set_halign(Gtk.Align.FILL)
            btn.connect("clicked", self._on_nav_clicked, page_id)
            sidebar_box.append(btn)
            self._nav_buttons[page_id] = btn

        sidebar_scroll.set_child(sidebar_box)
        paned.set_start_child(sidebar_scroll)

        # ── Conteúdo ──
        self.content_stack = Gtk.Stack()
        self.content_stack.add_css_class("rjos-settings-content")
        self.content_stack.set_vexpand(True)
        self.content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.content_stack.set_transition_duration(150)

        paned.set_end_child(self.content_stack)
        self.set_content(paned)

    def _switch_page(self, page_id: str):
        # Atualiza destaque da sidebar
        for pid, btn in self._nav_buttons.items():
            if pid == page_id:
                btn.add_css_class("active")
            else:
                btn.remove_css_class("active")

        # Cria página se não existe ainda
        if not self.content_stack.get_child_by_name(page_id):
            builder = PAGE_BUILDERS.get(page_id)
            if builder:
                page = builder()
            else:
                name = next((n for n, _, p in CATEGORIES if p == page_id), page_id)
                page = build_generic_page(name)
            self.content_stack.add_named(page, page_id)

        self.content_stack.set_visible_child_name(page_id)

    def _on_nav_clicked(self, btn, page_id: str):
        self._switch_page(page_id)


# ─── App ─────────────────────────────────────────────────────────────────────

class RjosSettingsApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="org.rjos.settings",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.connect("activate", self.on_activate)
        self._css_provider = None

    def on_activate(self, app):
        # ─ CSS base do settings app ─
        base_provider = Gtk.CssProvider()
        base_provider.load_from_string(RJOS_SETTINGS_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            base_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # ─ CSS override do tema RJOS (gerado por rjos-theme) ─
        self._theme_provider = Gtk.CssProvider()
        self._load_theme_override()
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self._theme_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

        # ─ Garante que rjos-theme aplica a config salva ao iniciar ─
        _rjos_theme("apply")

        # ─ SIGUSR1: recarrega o CSS override quando rjos-theme gera um novo ─
        signal.signal(signal.SIGUSR1, self._on_theme_reload)

        win = RjosSettingsWindow(application=self)
        win.present()

    def _load_theme_override(self):
        """Carrega o arquivo ~/.config/gtk-4.0/gtk.css gerado por rjos-theme."""
        override_path = Path.home() / ".config" / "gtk-4.0" / "gtk.css"
        try:
            if override_path.exists():
                self._theme_provider.load_from_path(str(override_path))
        except Exception:
            pass

    def _on_theme_reload(self, signum, frame):
        """Chamado via SIGUSR1: recarrega o CSS sem reiniciar o app."""
        GLib.idle_add(self._reload_css_idle)

    def _reload_css_idle(self):
        self._load_theme_override()
        return False  # Não repetir


def main():
    app = RjosSettingsApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
