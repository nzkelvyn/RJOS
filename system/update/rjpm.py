"""RJPM Wrapper abstraction."""
import subprocess

class RjpmWrapper:
    """Wrapper to interact with the system package manager (rjpm -> apt/flatpak)."""
    
    @staticmethod
    def update_package(package_name, is_user_app=False, use_delta=True):
        if is_user_app:
            print(f"[rjpm/flatpak] Atualizando App de Usuário: {package_name}...")
            try:
                return subprocess.call(["flatpak", "update", "-y", package_name])
            except FileNotFoundError:
                print("[rjpm/flatpak] flatpak não encontrado. Simulação mode.")
                return 0
                
        # Para pacotes core do sistema
        print(f"[rjpm/apt] Preparando para atualizar {package_name}...")
        
        if use_delta:
            print(f"[rjpm/delta] Procurando patch diferencial (casync/zchunk) para {package_name}...")
            # Lógica real verificaria se existe um patch .casync correspondente
            print(f"[rjpm/delta] (Simulação) Delta obtido. Reduzindo payload.")
            
        try:
            # We use sudo apt-get install --only-upgrade as a fallback/example
            return subprocess.call(["sudo", "apt-get", "install", "--only-upgrade", "-y", package_name])
        except FileNotFoundError:
            print("[rjpm/apt] apt não encontrado. Simulação mode.")
            return 0
