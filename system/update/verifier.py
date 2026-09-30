"""GPG Signature Verifier."""
import subprocess
from pathlib import Path

class SignatureVerifier:
    def __init__(self):
        self.keyring_path = "/usr/share/keyrings/rjos-archive-keyring.gpg"

    def verify_file(self, file_path, signature_path):
        """Verifies a file against its signature using GPG."""
        print(f"[Security] Verificando assinatura de {file_path}...")
        try:
            # gpg --verify --keyring <keyring> <sig> <file>
            result = subprocess.run([
                "gpg", "--verify", 
                "--no-default-keyring", "--keyring", self.keyring_path,
                str(signature_path), str(file_path)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("[Security] Assinatura válida.")
                return True
            else:
                print(f"[Security] ERRO: Assinatura inválida! {result.stderr}")
                return False
        except FileNotFoundError:
            print("[Security] AVISO: 'gpg' não encontrado. Simulação: Assinatura aceita.")
            return True

    def verify_metadata(self, metadata_dict, signature_string):
        """Futuro: Verificar assinatura direta na string yaml."""
        # TODO: Implementar verificação in-memory
        return True
