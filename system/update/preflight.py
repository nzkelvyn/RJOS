"""Pre-flight checks for RJOS Update System."""
import subprocess
import shutil

class PreflightChecks:
    @staticmethod
    def check_disk_space(required_mb=1024):
        """Checks if there is enough disk space in /."""
        total, used, free = shutil.disk_usage("/")
        free_mb = free // (1024 * 1024)
        return free_mb >= required_mb, free_mb

    @staticmethod
    def check_battery():
        """Checks if battery is above 20% or plugged in."""
        try:
            # Emulando chamada ao upower ou leitura do sysfs
            with open("/sys/class/power_supply/AC/online", "r") as f:
                ac_online = f.read().strip() == "1"
            if ac_online:
                return True, "AC Plugged In"
                
            with open("/sys/class/power_supply/BAT0/capacity", "r") as f:
                capacity = int(f.read().strip())
                return capacity >= 20, f"{capacity}%"
        except FileNotFoundError:
            # Em Desktop (sem bateria) ou ambiente simulado, assumimos ok
            return True, "No Battery / Simulated"

    @staticmethod
    def check_network():
        """Checks if the network is metered (e.g. mobile hotspot)."""
        try:
            # NetworkManager nmcli check
            res = subprocess.run(["nmcli", "-t", "-f", "GENERAL.METERED", "dev", "show"], capture_output=True, text=True)
            if "yes" in res.stdout:
                return False, "Metered Connection"
            return True, "Unmetered"
        except FileNotFoundError:
            return True, "nmcli not found"

    @classmethod
    def run_all(cls):
        """Runs all preflight checks."""
        disk_ok, disk_free = cls.check_disk_space()
        bat_ok, bat_status = cls.check_battery()
        net_ok, net_status = cls.check_network()
        
        errors = []
        if not disk_ok:
            errors.append(f"Espaço em disco insuficiente. Necessário 1GB, disponível: {disk_free}MB")
        if not bat_ok:
            errors.append(f"Bateria muito baixa ({bat_status}). Conecte à energia.")
        if not net_ok:
            errors.append("Conexão de rede limitada (Metered). Conecte-se ao Wi-Fi ou Ethernet.")
            
        return len(errors) == 0, errors
