#!/usr/bin/env python3
# =============================================================================
# RJOS Quick Settings — quick_settings.py
# Painel de configurações rápidas do RJOS
#
# Abre ao clicar nos ícones de status no painel superior.
# Controles: Wi-Fi, Bluetooth, Volume, Brilho, Modo noturno, Não perturbe
#
# Dependências:
#   python3-gi (PyGObject), gir1.2-gtk-4.0, gir1.2-adw-1
#   gtk4-layer-shell (libgtk4-layer-shell)
# =============================================================================

import gi
import os
import subprocess
import threading
from pathlib import Path

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

QUICK_SETTINGS_CSS = """
/* ══════════════════════════════════════════════════════════════════
   RJOS Quick Settings — Estilos Oficiais RJOS
   ══════════════════════════════════════════════════════════════════ */

.rjos-qs-panel {
    background-color: #1E1E1E;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.8);
    padding: 16px;
    min-width: 360px;
}

/* Header com info do usuário */
.rjos-qs-header {
    padding: 4px 0 12px 0;
}

.rjos-qs-username {
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 600;
}

.rjos-qs-hostname {
    color: #B8B8B8;
    font-size: 11px;
    font-weight: 400;
}

.rjos-qs-avatar {
    background: #005B96;
    border-radius: 50%;
    min-width: 36px;
    min-height: 36px;
    color: #FFFFFF;
    font-size: 16px;
    font-weight: 700;
}

/* Grid de toggles rápidos */
.rjos-qs-toggle-grid {
    padding: 0;
}

/* Toggle Desativado (Superfície escura) */
.rjos-qs-toggle {
    background-color: #292929;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    padding: 12px;
    min-width: 100px;
    min-height: 60px;
    transition: all 120ms ease;
}

.rjos-qs-toggle:hover {
    background-color: #333333;
    border-color: rgba(255, 255, 255, 0.14);
}

/* Toggle Ativo em Azul Oceano (Wi-Fi, Bluetooth) */
.rjos-qs-toggle-active {
    background-color: rgba(0, 91, 150, 0.22);
    border-color: #005B96;
}

.rjos-qs-toggle-active:hover {
    background-color: rgba(0, 91, 150, 0.32);
}

/* Toggle Ativo em Verde Tropical (Modo Economia / Sucesso) */
.rjos-qs-toggle-green {
    background-color: rgba(0, 168, 107, 0.22);
    border-color: #00A86B;
}

.rjos-qs-toggle-green:hover {
    background-color: rgba(0, 168, 107, 0.32);
}

/* Toggle Ativo em Amarelo Sol (Avisos / Atenção / DND) */
.rjos-qs-toggle-yellow {
    background-color: rgba(242, 201, 76, 0.22);
    border-color: #F2C94C;
}

.rjos-qs-toggle-yellow:hover {
    background-color: rgba(242, 201, 76, 0.32);
}

.rjos-qs-toggle-icon {
    font-size: 20px;
    margin-bottom: 4px;
}

.rjos-qs-toggle-label {
    color: #B8B8B8;
    font-size: 10px;
    font-weight: 500;
}

.rjos-qs-toggle-active .rjos-qs-toggle-label {
    color: #FFFFFF;
    font-weight: 600;
}

.rjos-qs-toggle-green .rjos-qs-toggle-label {
    color: #FFFFFF;
    font-weight: 600;
}

.rjos-qs-toggle-yellow .rjos-qs-toggle-label {
    color: #FFFFFF;
    font-weight: 600;
}

/* Sliders (volume, brilho) */
.rjos-qs-slider-row {
    background-color: #161616;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 10px;
    padding: 10px 14px;
    margin-top: 8px;
}

.rjos-qs-slider-icon {
    color: #B8B8B8;
    font-size: 18px;
    min-width: 24px;
}

.rjos-qs-slider-value {
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 500;
    min-width: 36px;
}

/* Rodapé com botões */
.rjos-qs-footer {
    padding-top: 8px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    margin-top: 12px;
}

.rjos-qs-footer-btn {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 8px;
    color: #B8B8B8;
    font-size: 18px;
    min-width: 40px;
    min-height: 40px;
    transition: all 120ms ease;
}

.rjos-qs-footer-btn:hover {
    background-color: #292929;
    color: #FFFFFF;
}
"""


class RjosQuickSettings(Gtk.Window):
    """Painel de Quick Settings do RJOS"""

    def __init__(self, parent_panel):
        super().__init__()
        self.parent_panel = parent_panel

        # Estado dos toggles
        self.wifi_on = True
        self.bluetooth_on = False
        self.dnd_on = False
        self.nightlight_on = False
        self.airplane_on = False
        self.hotspot_on = False

        self._setup_window()
        self._build_ui()
        self._detect_states()

    def _setup_window(self):
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_transient_for(self.parent_panel)
        self.set_modal(True)

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 42)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 12)
            GtkLayerShell.set_keyboard_mode(
                self, GtkLayerShell.KeyboardMode.EXCLUSIVE
            )

        # Fecha com Escape
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_key)
        self.add_controller(key_ctrl)

    def _build_ui(self):
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        panel.add_css_class("rjos-qs-panel")

        # ── Header: Avatar + Nome + Hostname ──
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.add_css_class("rjos-qs-header")

        # Avatar
        avatar = Gtk.Label(label="👤")
        avatar.add_css_class("rjos-qs-avatar")
        avatar.set_halign(Gtk.Align.CENTER)
        avatar.set_valign(Gtk.Align.CENTER)
        header.append(avatar)

        # Info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_valign(Gtk.Align.CENTER)

        username = os.environ.get("USER", "rjos")
        hostname = ""
        try:
            hostname = subprocess.run(
                ["hostname"], capture_output=True, text=True, timeout=1
            ).stdout.strip()
        except Exception:
            hostname = "rjos"

        name_label = Gtk.Label(label=username.capitalize())
        name_label.add_css_class("rjos-qs-username")
        name_label.set_halign(Gtk.Align.START)
        info_box.append(name_label)

        host_label = Gtk.Label(label=f"{username}@{hostname}")
        host_label.add_css_class("rjos-qs-hostname")
        host_label.set_halign(Gtk.Align.START)
        info_box.append(host_label)

        header.append(info_box)
        panel.append(header)

        # ── Grid de toggles (2x3) ──
        grid = Gtk.Grid()
        grid.set_column_spacing(8)
        grid.set_row_spacing(8)
        grid.set_column_homogeneous(True)
        grid.add_css_class("rjos-qs-toggle-grid")

        toggles = [
            ("📶", "Wi-Fi", "wifi", self.wifi_on),
            ("🔵", "Bluetooth", "bluetooth", self.bluetooth_on),
            ("🔕", "Não Perturbe", "dnd", self.dnd_on),
            ("🌙", "Modo Noturno", "nightlight", self.nightlight_on),
            ("✈️", "Modo Avião", "airplane", self.airplane_on),
            ("📡", "Hotspot", "hotspot", self.hotspot_on),
        ]

        self.toggle_buttons = {}

        for idx, (icon, label, key, active) in enumerate(toggles):
            row = idx // 3
            col = idx % 3

            btn = Gtk.Button()
            btn.add_css_class("rjos-qs-toggle")
            if active:
                btn.add_css_class("rjos-qs-toggle-active")

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            vbox.set_halign(Gtk.Align.CENTER)
            vbox.set_valign(Gtk.Align.CENTER)

            icon_lbl = Gtk.Label(label=icon)
            icon_lbl.add_css_class("rjos-qs-toggle-icon")
            vbox.append(icon_lbl)

            text_lbl = Gtk.Label(label=label)
            text_lbl.add_css_class("rjos-qs-toggle-label")
            vbox.append(text_lbl)

            btn.set_child(vbox)
            btn.connect("clicked", self._on_toggle_clicked, key)

            self.toggle_buttons[key] = btn
            grid.attach(btn, col, row, 1, 1)

        panel.append(grid)

        # ── Slider de Volume ──
        vol_row = self._build_slider_row(
            "🔊", "Volume", 0, 100, 75, self._on_volume_changed
        )
        self.volume_slider = vol_row["scale"]
        self.volume_value = vol_row["value_label"]
        panel.append(vol_row["widget"])

        # ── Slider de Brilho ──
        brt_row = self._build_slider_row(
            "☀️", "Brilho", 5, 100, 80, self._on_brightness_changed
        )
        self.brightness_slider = brt_row["scale"]
        self.brightness_value = brt_row["value_label"]
        panel.append(brt_row["widget"])

        # ── Footer: Configurações, Bloquear, Encerrar ──
        footer = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=4
        )
        footer.add_css_class("rjos-qs-footer")
        footer.set_halign(Gtk.Align.END)

        footer_items = [
            ("⚙️", "Configurações", self._on_settings),
            ("🔒", "Bloquear", self._on_lock),
            ("⏻", "Encerrar sessão", self._on_logout),
        ]

        for icon, tooltip, callback in footer_items:
            btn = Gtk.Button(label=icon)
            btn.add_css_class("rjos-qs-footer-btn")
            btn.set_tooltip_text(tooltip)
            btn.connect("clicked", callback)
            footer.append(btn)

        panel.append(footer)
        self.set_child(panel)

    def _build_slider_row(self, icon, label, min_val, max_val, default, callback):
        """Cria uma linha de slider (volume/brilho)"""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.add_css_class("rjos-qs-slider-row")

        icon_lbl = Gtk.Label(label=icon)
        icon_lbl.add_css_class("rjos-qs-slider-icon")
        row.append(icon_lbl)

        adj = Gtk.Adjustment(
            value=default, lower=min_val, upper=max_val,
            step_increment=5, page_increment=10
        )
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        scale.set_draw_value(False)
        scale.set_hexpand(True)
        scale.connect("value-changed", callback)
        row.append(scale)

        value_label = Gtk.Label(label=f"{default}%")
        value_label.add_css_class("rjos-qs-slider-value")
        row.append(value_label)

        return {
            "widget": row,
            "scale": scale,
            "value_label": value_label,
        }

    # ── Detecção de estados ──

    def _detect_states(self):
        """Detecta estados atuais de rede, bluetooth, volume, brilho"""
        threading.Thread(target=self._detect_wifi, daemon=True).start()
        threading.Thread(target=self._detect_volume, daemon=True).start()
        threading.Thread(target=self._detect_brightness, daemon=True).start()

    def _detect_wifi(self):
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "WIFI", "general"],
                capture_output=True, text=True, timeout=3
            )
            enabled = "enabled" in result.stdout.lower()
            GLib.idle_add(self._update_toggle, "wifi", enabled)
        except Exception:
            pass

    def _detect_volume(self):
        try:
            result = subprocess.run(
                ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
                capture_output=True, text=True, timeout=3
            )
            # Output: "Volume: 0.75" ou "Volume: 0.75 [MUTED]"
            parts = result.stdout.strip().split()
            if len(parts) >= 2:
                vol = int(float(parts[1]) * 100)
                GLib.idle_add(self.volume_slider.set_value, vol)
                GLib.idle_add(self.volume_value.set_text, f"{vol}%")
        except Exception:
            pass

    def _detect_brightness(self):
        try:
            # Tenta brightnessctl primeiro
            result = subprocess.run(
                ["brightnessctl", "-m"],
                capture_output=True, text=True, timeout=3
            )
            # Output: "device,class,cur,max,percent%"
            parts = result.stdout.strip().split(",")
            if len(parts) >= 5:
                pct = int(parts[3].replace("%", ""))
                GLib.idle_add(self.brightness_slider.set_value, pct)
                GLib.idle_add(self.brightness_value.set_text, f"{pct}%")
        except Exception:
            pass

    # ── Toggle handlers ──

    def _on_toggle_clicked(self, btn, key):
        """Alterna um toggle on/off"""
        active = btn.has_css_class("rjos-qs-toggle-active")

        if active:
            btn.remove_css_class("rjos-qs-toggle-active")
        else:
            btn.add_css_class("rjos-qs-toggle-active")

        new_state = not active

        # Executa ação correspondente
        actions = {
            "wifi": lambda on: subprocess.Popen(
                ["nmcli", "radio", "wifi", "on" if on else "off"]
            ),
            "bluetooth": lambda on: subprocess.Popen(
                ["bluetoothctl", "power", "on" if on else "off"]
            ),
            "nightlight": lambda on: subprocess.Popen(
                ["wlsunset", "-t", "3500", "-T", "6500"]
                if on else ["pkill", "wlsunset"]
            ),
            "airplane": self._toggle_airplane,
        }

        action = actions.get(key)
        if action:
            try:
                action(new_state)
            except Exception as e:
                print(f"[qs] Erro ao alternar {key}: {e}")

    def _toggle_airplane(self, on):
        """Modo avião: desliga Wi-Fi e Bluetooth"""
        if on:
            subprocess.Popen(["nmcli", "radio", "wifi", "off"])
            subprocess.Popen(["bluetoothctl", "power", "off"])
            self._update_toggle("wifi", False)
            self._update_toggle("bluetooth", False)
        else:
            subprocess.Popen(["nmcli", "radio", "wifi", "on"])
            self._update_toggle("wifi", True)

    def _update_toggle(self, key, active):
        """Atualiza visual de um toggle"""
        btn = self.toggle_buttons.get(key)
        if btn:
            if active:
                btn.add_css_class("rjos-qs-toggle-active")
            else:
                btn.remove_css_class("rjos-qs-toggle-active")

    # ── Slider handlers ──

    def _on_volume_changed(self, scale):
        vol = int(scale.get_value())
        self.volume_value.set_text(f"{vol}%")
        # Define volume via WirePlumber
        subprocess.Popen([
            "wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@",
            f"{vol / 100:.2f}"
        ])

    def _on_brightness_changed(self, scale):
        brt = int(scale.get_value())
        self.brightness_value.set_text(f"{brt}%")
        # Define brilho via brightnessctl
        subprocess.Popen(["brightnessctl", "set", f"{brt}%"])

    # ── Footer handlers ──

    def _on_settings(self, btn):
        self.close()
        subprocess.Popen(
            ["/bin/sh", "-c", "rjos-settings"],
            start_new_session=True
        )

    def _on_lock(self, btn):
        self.close()
        subprocess.Popen(["loginctl", "lock-session"])

    def _on_logout(self, btn):
        self.close()
        subprocess.Popen(
            ["loginctl", "terminate-user", os.environ.get("USER", "")]
        )

    # ── Key handler ──

    def _on_key(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False
