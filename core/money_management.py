import uuid
import threading
import logging
import math
import requests
import json
import time
import os
import yaml
import hashlib
from pathlib import Path

def norm_teams(t):
    # 🔴 FIX 5.2: Normalizzazione e Hash per Anti-Duplicazione esatta
    return hashlib.sha1(''.join(sorted(str(t).lower().replace(' ','').split('-'))).encode()).hexdigest()

class MoneyManager:
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger("Quant-Risk-Engine")
        self._lock = threading.RLock()
        self.tx_memory = {}
        self.drift_count = 0 # 🔴 FIX 5.3: Hysteresis
        
        self.config_path = os.path.join(str(Path.home()), ".superagent_data", "roserpina_settings.yaml")
        self.api_key_path = os.path.join(str(Path.home()), ".superagent_data", "openrouter_key.dat")
        
        try:
            for p in self.db.pending():
                self.tx_memory[p["tx_id"]] = {"table_id": p.get("table_id", 1), "amount": p["amount"], "teams": p.get("teams", "")}
        except: pass

    def _get_live_settings(self):
        s = {"ai_active": True, "base_target": 3.0, "absolute_max_stake": 18.0, "risk_mode": "BALANCED", "max_exposure": 35.0, "max_tables": 5}
        try:
            if os.path.exists(self.config_path): s.update(yaml.safe_load(open(self.config_path)) or {})
        except: pass
        return s

    def get_bankroll_and_peak(self):
        with self._lock:
            bal, peak = self.db.get_balance()
            return float(bal), float(peak)

    def bankroll(self): return self.get_bankroll_and_peak()[0]

    def pending(self):
        with self._lock: return self.db.pending()

    def get_stake_and_reserve(self, odds: float, teams: str = "") -> dict:
        """🔴 FIX 5.1: Transazione Atomica Singola per calcolo stake e lock database"""
        settings = self._get_live_settings()
        if odds < 1.15: return {"stake": 0.0, "table_id": 0, "tx_id": None} # 🔴 FIX 5.4: Low odds drop
        
        # Fuori lock per AI API (lenta)
        br, peak = self.get_bankroll_and_peak()
        strategy = {"max_exposure_pct": settings["max_exposure"]/100.0, "max_tables": settings["max_tables"], "stake_multiplier": 1.0}
        
        with self._lock:
            tables = self.db.get_roserpina_tables()
            pending_list = self.db.pending()
            
            if br <= 0: return {"stake": 0.0, "table_id": 0, "tx_id": None}
            
            target_hash = norm_teams(teams) if teams else ""
            for p in pending_list:
                if p.get("teams") and p["teams"] == target_hash:
                    return {"stake": 0.0, "table_id": 0, "tx_id": None}

            pending_exposure = sum(float(p["amount"]) for p in pending_list)
            max_allowed = br * strategy["max_exposure_pct"]
            if pending_exposure >= max_allowed: return {"stake": 0.0, "table_id": 0, "tx_id": None}
            
            active_ids = set(p.get("table_id") for p in pending_list if p.get("table_id"))
            if len(active_ids) >= strategy["max_tables"]: return {"stake": 0.0, "table_id": 0, "tx_id": None}
            
            free = [t for t in tables if t["table_id"] not in active_ids and t["table_id"] <= settings["max_tables"]]
            if not free: return {"stake": 0.0, "table_id": 0, "tx_id": None}
            
            rec = [t for t in free if t["in_recovery"] == 1]
            t_id = (rec[0] if rec else min(free, key=lambda x: x["loss"]))["table_id"]
            
            missing = (br * (settings["base_target"]/100.0)) - sum(t["profit"]-t["loss"] for t in tables)
            if missing <= 0: missing = br * 0.01
            
            stake = min((missing / (odds - 1.0)) * strategy["stake_multiplier"], max_allowed - pending_exposure, br * (settings["absolute_max_stake"]/100.0))
            if math.isnan(stake) or stake < 0 or stake > (br * 0.25): return {"stake": 0.0, "table_id": 0, "tx_id": None}
            
            stake = round(stake, 2)
            tx = str(uuid.uuid4())
            
            # 🔴 PATCH 1: Iniezione Hash per DB-Level Lock
            self.db.reserve(tx, stake, table_id=t_id, teams=teams, match_hash=target_hash)
            self.tx_memory[tx] = {"table_id": t_id, "amount": stake, "teams": target_hash}
            
            return {"stake": stake, "table_id": t_id, "tx_id": tx}

    # Helper wrapper compatibilità
    def get_stake(self, odds, teams=""): return self.get_stake_and_reserve(odds, teams)
    
    def reserve(self, amount, table_id=1, teams=""):
        """Gestisce le scritture dirette per la modalità Stake Fisso in thread-safety"""
        with self._lock:
            tx = str(uuid.uuid4())
            target_hash = norm_teams(teams) if teams else ""
            
            # 🔴 PATCH 1: Iniezione Hash per DB-Level Lock
            self.db.reserve(tx, amount, table_id=table_id, teams=teams, match_hash=target_hash)
            self.tx_memory[tx] = {"table_id": table_id, "amount": amount, "teams": target_hash}
            return tx

    def refund(self, tx_id: str):
        with self._lock:
            self.db.rollback(tx_id)
            self.tx_memory.pop(tx_id, None)

    def win(self, tx_id: str, payout: float):
        with self._lock:
            self.db.commit(tx_id, payout)
            mem = self.tx_memory.pop(tx_id, None)
            if mem:
                t_id, profit = mem["table_id"], float(payout) - float(mem["amount"])
                current_loss = next((t["loss"] for t in self.db.get_roserpina_tables() if t["table_id"] == t_id), 0.0)
                if profit > 0: self.db.update_roserpina_table(t_id, profit, -current_loss, 0)
                elif profit < 0 and payout > 0: self.db.update_roserpina_table(t_id, 0, abs(profit), 1)

    def loss(self, tx_id: str):
        with self._lock:
            self.db.commit(tx_id, 0.0)
            mem = self.tx_memory.pop(tx_id, None)
            if mem: self.db.update_roserpina_table(mem["table_id"], 0, float(mem["amount"]), 1)

    def reconcile_balances(self, real_balance: float):
        with self._lock:
            if self.pending(): return
            db_bal, _ = self.get_bankroll_and_peak()
            
            # 🔴 FIX 5.3: Hysteresis
            if abs(db_bal - real_balance) > 1.0:
                self.drift_count += 1
                if self.drift_count >= 3:
                    self.db.update_bankroll(real_balance)
                    self.logger.info(f"🔄 Reconciled: {real_balance:.2f}")
                    self.drift_count = 0
            else:
                self.drift_count = 0
