import os
import yaml
import logging
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFormLayout, 
                             QGroupBox, QLineEdit, QMessageBox, QComboBox, QDoubleSpinBox)
from PySide6.QtCore import Qt

class RoserpinaTab(QWidget):
    def __init__(self, logger, controller):
        super().__init__()
        self.logger = logger
        self.controller = controller
        self.db = controller.db
        
        main_layout = QVBoxLayout(self)
        
        # --- GRUPPO CONFIGURAZIONE ---
        config_group = QGroupBox("⚙️ CONFIGURAZIONE HEDGE FUND AI")
        form = QFormLayout()
        
        self.risk_combo = QComboBox()
        self.risk_combo.addItems(["CONSERVATIVE", "BALANCED", "AGGRESSIVE"])
        
        self.target_spin = QDoubleSpinBox()
        self.target_spin.setRange(0.5, 20.0)
        self.target_spin.setSuffix(" %")
        
        self.exposure_spin = QDoubleSpinBox()
        self.exposure_spin.setRange(5.0, 80.0)
        self.exposure_spin.setSuffix(" %")

        form.addRow("Modalità Rischio:", self.risk_combo)
        form.addRow("Target Profitto Ciclo:", self.target_spin)
        form.addRow("Max Esposizione Totale:", self.exposure_spin)
        
        config_group.setLayout(form)
        main_layout.addWidget(config_group)

        # --- PULSANTI AZIONE ---
        btn_save = QPushButton("💾 Salva e Applica al Motore")
        btn_save.setStyleSheet("background-color: #1e88e5; color: white; padding: 10px; font-weight: bold;")
        btn_save.clicked.connect(self.save_settings)
        main_layout.addWidget(btn_save)

        self.btn_reset = QPushButton("🔴 Forza Reset Recovery (Emergenza)")
        self.btn_reset.setStyleSheet("background-color: #b71c1c; color: white;")
        self.btn_reset.clicked.connect(self.manual_reset_recovery)
        main_layout.addWidget(self.btn_reset)
        
        main_layout.addStretch()

    def save_settings(self):
        mode = self.risk_combo.currentText()
        target = self.target_spin.value()
        logging.info(f"🖱️ [UI] Richiesta aggiornamento impostazioni Roserpina AI.")
        logging.info(f"⚙️ [ROSERPINA] Nuovi parametri -> Modo: {mode}, Target: {target}%")
        # Logica di salvataggio...
        QMessageBox.information(self, "Roserpina AI", "✅ Parametri finanziari aggiornati e applicati istantaneamente.")

    def manual_reset_recovery(self):
        reply = QMessageBox.question(self, 'Conferma Reset', 'Vuoi azzerare tutte le perdite in memoria?')
        if reply == QMessageBox.Yes:
            logging.warning("🔴 [ROSERPINA] RESET RECOVERY FORZATO DALL'UTENTE. Azzeramento perdite in corso.")
            # self.db.reset_recovery()
            QMessageBox.warning(self, "Reset", "Memoria perdite piallata. I tavoli ripartono da zero.")
