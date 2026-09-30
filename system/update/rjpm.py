"""RJPM Wrapper abstraction."""
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
