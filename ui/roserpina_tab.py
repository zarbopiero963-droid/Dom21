import os
import yaml
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFormLayout, 
                             QCheckBox, QComboBox, QDoubleSpinBox, QSpinBox,
                             QGroupBox, QLineEdit, QMessageBox)
from PySide6.QtCore import Qt

CONFIG_DIR = os.path.join(str(Path.home()), ".superagent_data")
ROSERPINA_CONF = os.path.join(CONFIG_DIR, "roserpina_settings.yaml")

class RoserpinaTab(QWidget):
    def __init__(self, logger, controller):
        super().__init__()
        self.logger = logger
        self.controller = controller
        self.db = controller.db
        
        # Default config
        self.settings = {
            "ai_active": True,
            "base_target": 3.0,
            "absolute_max_stake": 18.0,
            "risk_mode": "BALANCED",
            "max_exposure": 35.0,
            "max_tables": 5,
            "auto_reset_dd": False,
            "auto_reset_dd_val": 10.0
        }
        
        self.setup_ui()
        self.load_settings()
        
        # 🔒 All'avvio, blocca tutto in modalità "Sola Lettura"
        self.set_edit_mode(False)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- SEZIONE 1: PARAMETRI MOTORE ---
        engine_group = QGroupBox("⚙️ Configurazione Motore Risk Engine")
        engine_layout = QFormLayout()
        
        self.in_ai_active = QCheckBox("Cervello AI Attivo (Adattivo)")
        
        self.in_risk_mode = QComboBox()
        self.in_risk_mode.addItems(["ULTRA SAFE", "SAFE", "BALANCED", "AGGRESSIVE"])
        
        self.in_target = QDoubleSpinBox()
        self.in_target.setRange(1.0, 5.0)
        self.in_target.setSingleStep(0.5)
        self.in_target.setSuffix("%")
        
        self.in_max_stake = QDoubleSpinBox()
        self.in_max_stake.setRange(5.0, 25.0)
        self.in_max_stake.setSuffix("%")
        
        self.in_max_exp = QDoubleSpinBox()
        self.in_max_exp.setRange(20.0, 60.0)
        self.in_max_exp.setSuffix("%")
        
        self.in_tables = QSpinBox()
        self.in_tables.setRange(1, 5)

        # 🎛️ PULSANTI MODIFICA / SALVA
        btn_layout = QHBoxLayout()
        self.btn_edit = QPushButton("✏️ Modifica Impostazioni")
        self.btn_edit.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold; padding: 8px;")
        self.btn_edit.clicked.connect(lambda: self.set_edit_mode(True))

        self.btn_save = QPushButton("💾 Salva e Applica al Motore")
        self.btn_save.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px;")
        self.btn_save.clicked.connect(self.save_settings)
        
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_save)

        engine_layout.addRow(btn_layout)
        engine_layout.addRow(QLabel("")) # Spazio
        engine_layout.addRow("Stato AI:", self.in_ai_active)
        engine_layout.addRow("Profilo Rischio Base AI:", self.in_risk_mode)
        engine_layout.addRow("Target Profitto Ciclo:", self.in_target)
        engine_layout.addRow("Max Stake Singola Bet:", self.in_max_stake)
        engine_layout.addRow("Max Capitale Esposto:", self.in_max_exp)
        engine_layout.addRow("Numero Tavoli Paralleli:", self.in_tables)
        
        engine_group.setLayout(engine_layout)
        main_layout.addWidget(engine_group)
        
        # --- SEZIONE 2: RECOVERY E BANKROLL ---
        recovery_group = QGroupBox("🛡️ Recovery & Bankroll Management")
        recovery_layout = QVBoxLayout()
        
        # Reset Auto
        auto_layout = QHBoxLayout()
        self.in_auto_reset = QCheckBox("Auto-Reset Recovery se Drawdown peggiore di:")
        self.in_auto_dd = QDoubleSpinBox()
        self.in_auto_dd.setRange(5.0, 50.0)
        self.in_auto_dd.setSuffix("%")
        auto_layout.addWidget(self.in_auto_reset)
        auto_layout.addWidget(self.in_auto_dd)
        auto_layout.addStretch()
        recovery_layout.addLayout(auto_layout)
        
        # Pulsanti Manuali (Sempre attivi)
        manual_btn_layout = QHBoxLayout()
        
        # Override Bankroll
        self.in_bankroll = QLineEdit()
        self.in_bankroll.setPlaceholderText("Es. 500.00")
        btn_update_br = QPushButton("💰 Aggiorna Bankroll Manualmente")
        btn_update_br.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 8px;")
        btn_update_br.clicked.connect(self.manual_update_bankroll)
        
        # Reset Recovery Manuale
        btn_reset_rec = QPushButton("🔴 FORZA RESET RECOVERY (Tutti i Tavoli)")
        btn_reset_rec.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; padding: 8px;")
        btn_reset_rec.clicked.connect(self.manual_reset_recovery)
        
        manual_btn_layout.addWidget(QLabel("Bankroll €:"))
        manual_btn_layout.addWidget(self.in_bankroll)
        manual_btn_layout.addWidget(btn_update_br)
        manual_btn_layout.addStretch()
        manual_btn_layout.addWidget(btn_reset_rec)
        
        recovery_layout.addLayout(manual_btn_layout)
        recovery_group.setLayout(recovery_layout)
        
        main_layout.addWidget(recovery_group)
        main_layout.addStretch()

    def set_edit_mode(self, enabled):
        """Attiva o disattiva i campi di testo. Gestisce i pulsanti Edit/Save."""
        self.in_ai_active.setEnabled(enabled)
        self.in_risk_mode.setEnabled(enabled)
        self.in_target.setEnabled(enabled)
        self.in_max_stake.setEnabled(enabled)
        self.in_max_exp.setEnabled(enabled)
        self.in_tables.setEnabled(enabled)
        self.in_auto_reset.setEnabled(enabled)
        self.in_auto_dd.setEnabled(enabled)
        
        # Scambia la visibilità dei pulsanti
        self.btn_edit.setVisible(not enabled)
        self.btn_save.setVisible(enabled)

    def load_settings(self):
        """Carica le impostazioni dal file YAML."""
        try:
            if os.path.exists(ROSERPINA_CONF):
                with open(ROSERPINA_CONF, 'r') as f:
                    loaded = yaml.safe_load(f) or {}
                    self.settings.update(loaded)
        except Exception as e:
            self.logger.error(f"Errore caricamento settings Roserpina: {e}")

        self.in_ai_active.setChecked(self.settings.get("ai_active", True))
        self.in_risk_mode.setCurrentText(self.settings.get("risk_mode", "BALANCED"))
        self.in_target.setValue(self.settings.get("base_target", 3.0))
        self.in_max_stake.setValue(self.settings.get("absolute_max_stake", 18.0))
        self.in_max_exp.setValue(self.settings.get("max_exposure", 35.0))
        self.in_tables.setValue(self.settings.get("max_tables", 5))
        self.in_auto_reset.setChecked(self.settings.get("auto_reset_dd", False))
        self.in_auto_dd.setValue(self.settings.get("auto_reset_dd_val", 10.0))

    def save_settings(self):
        """Salva le impostazioni modificate e rimette in sola lettura."""
        self.settings["ai_active"] = self.in_ai_active.isChecked()
        self.settings["risk_mode"] = self.in_risk_mode.currentText()
        self.settings["base_target"] = self.in_target.value()
        self.settings["absolute_max_stake"] = self.in_max_stake.value()
        self.settings["max_exposure"] = self.in_max_exp.value()
        self.settings["max_tables"] = self.in_tables.value()
        self.settings["auto_reset_dd"] = self.in_auto_reset.isChecked()
        self.settings["auto_reset_dd_val"] = self.in_auto_dd.value()
        
        try:
            with open(ROSERPINA_CONF, 'w') as f:
                yaml.dump(self.settings, f)
            self.logger.info("⚙️ Parametri Roserpina salvati e applicati al motore.")
            QMessageBox.information(self, "Salvato", "Impostazioni applicate correttamente al Risk Engine.")
        except Exception as e:
            self.logger.error(f"Errore salvataggio settings Roserpina: {e}")
            QMessageBox.warning(self, "Errore", "Impossibile salvare le impostazioni.")
            
        # Ritorna in modalità protetta (Sola Lettura)
        self.set_edit_mode(False)

    def manual_update_bankroll(self):
        val = self.in_bankroll.text().replace(',', '.')
        try:
            amount = float(val)
            if amount < 0: raise ValueError
            self.db.update_bankroll(amount)
            QMessageBox.information(self, "Successo", f"Bankroll aggiornato a €{amount:.2f}")
            self.in_bankroll.clear()
            self.logger.info(f"💰 Bankroll aggiornato manualmente a €{amount:.2f}")
        except ValueError:
            QMessageBox.warning(self, "Errore", "Inserisci un importo numerico valido.")

    def manual_reset_recovery(self):
        reply = QMessageBox.question(self, 'Conferma Reset', 
                                     'Vuoi azzerare TUTTE le perdite in memoria? I tavoli ripartiranno da zero.',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            with self.db._lock:
                self.db.conn.execute("UPDATE roserpina_tables SET loss = 0, in_recovery = 0")
            self.logger.warning("🔴 RESET RECOVERY FORZATO ESEGUITO SU TUTTI I TAVOLI.")
            QMessageBox.information(self, "Reset Eseguito", "Tutti i tavoli sono stati resettati (Loss azzerato).")
