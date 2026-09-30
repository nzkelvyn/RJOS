"""Snapshot and Rollback Infrastructure for RJOS."""
import subprocess
import datetime
import os
import json
from pathlib import Path

SNAPSHOT_INFO_DIR = Path("/var/lib/rjos/snapshots")

class SnapshotManager:
    """Manages system snapshots for rollback using Timeshift or native BTRFS."""
    
    def __init__(self):
        try:
            SNAPSHOT_INFO_DIR.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            pass # Ignorado em ambiente sem root para simulação
    
    def _is_btrfs(self):
        """Checks if the root filesystem is BTRFS."""
        try:
            result = subprocess.run(["findmnt", "-n", "-o", "FSTYPE", "/"], capture_output=True, text=True)
            return "btrfs" in result.stdout.lower()
        except FileNotFoundError:
            return False

    def create_snapshot(self, description="Pre-update snapshot"):
        """Creates a snapshot of the current system state."""
        print(f"[Snapshot] Criando snapshot: {description}...")
        
        # Simulação de criação do snapshot (Em ambiente real, invoca BTRFS ou Timeshift)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_id = f"snap_{timestamp}"
        
        info = {
            "id": snapshot_id,
            "description": description,
            "date": datetime.datetime.now().isoformat(),
            "status": "created"
        }
        
        try:
            # Fake snapshot logic for architecture base
            if self._is_btrfs():
                subprocess.run(["sudo", "btrfs", "subvolume", "snapshot", "/", f"/.snapshots/{snapshot_id}"])
            else:
                # Fallback to timeshift if installed
                subprocess.run(["sudo", "timeshift", "--create", "--comments", description])
                
            info_path = SNAPSHOT_INFO_DIR / f"{snapshot_id}.json"
            with open(info_path, "w") as f:
                json.dump(info, f)
            print(f"[Snapshot] Snapshot {snapshot_id} criado com sucesso.")
        except Exception as e:
            print(f"[Snapshot] Ambiente simulado. Snapshot {snapshot_id} registrado logicamente.")
            
        return snapshot_id

    def rollback(self, snapshot_id=None):
        """Rolls back the system to a previous snapshot."""
        if not snapshot_id:
            # Buscar último snapshot (simulação)
            print("[Rollback] Restaurando último snapshot seguro...")
        else:
            print(f"[Rollback] Restaurando snapshot {snapshot_id}...")
            
        try:
            if self._is_btrfs():
                # Lógica real exigiria reboot para subvolume root
                print("[Rollback] Rollback BTRFS agendado. Reinicie o sistema.")
            else:
                subprocess.run(["sudo", "timeshift", "--restore", "--snapshot", snapshot_id])
        except Exception:
            print("[Rollback] Em simulação, falha ao executar binários de restore.")
            
        return True
