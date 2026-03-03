import logging
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTableWidget, QTableWidgetItem, QHeaderView, QPushButton)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor

class HistoryTab(QWidget):
    def __init__(self, logger, controller):
        super().__init__()
        self.logger = logger
        self.controller = controller
        
        layout = QVBoxLayout(self)
        
        # --- DASHBOARD STATS ---
        stats_layout = QHBoxLayout()
        self.lbl_balance = QLabel("💰 Saldo Attuale: € 0.00")
        self.lbl_peak = QLabel("⛰️ Peak Balance: € 0.00")
        self.lbl_profit = QLabel("📈 Profitto Netto: € 0.00")
        self.lbl_pending = QLabel("⏳ In Corso: 0")
        
        for lbl in [self.lbl_balance, self.lbl_peak, self.lbl_profit, self.lbl_pending]:
            lbl.setStyleSheet("font-size: 16px; font-weight: bold; background-color: #1e1e1e; padding: 12px; border-radius: 6px; border: 1px solid #333;")
            lbl.setAlignment(Qt.AlignCenter)
            stats_layout.addWidget(lbl)
            
        layout.addLayout(stats_layout)
        layout.addSpacing(10)
        
        # --- TABELLA STORICO ---
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Data/Ora", "Tavolo", "Evento", "Mercato", "Quota", "Stake", "Profit"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("background-color: #121212; gridline-color: #333;")
        layout.addWidget(self.table)

        # Refresh Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(5000) # Ogni 5 secondi
        
        self.refresh_data()

    def refresh_data(self):
        try:
            # Recupera dati dal database del controller
            bets = self.controller.db.get_all_bets()
            current_balance = self.controller.db.get_current_balance()
            peak_balance = self.controller.db.get_peak_balance()
            pending_count = len([b for b in bets if b['status'] == 'PENDING'])
            
            # Blocca aggiornamento grafico per performance
            self.table.setUpdatesEnabled(False)
            self.table.setRowCount(0)
            
            for row_idx, b in enumerate(bets):
                self.table.insertRow(row_idx)
                # ... popolamento celle ...
                self.table.setItem(row_idx, 0, QTableWidgetItem(str(b['id'])))
                self.table.setItem(row_idx, 3, QTableWidgetItem(b['teams']))
                # ... (restante logica di popolamento) ...
            
            self.table.setUpdatesEnabled(True)
            
            # Aggiorna Label
            self.lbl_balance.setText(f"💰 Saldo Attuale: € {current_balance:.2f}")
            self.lbl_peak.setText(f"⛰️ Peak Balance: € {peak_balance:.2f}")
            self.lbl_pending.setText(f"⏳ In Corso: {pending_count}")
            
            net_profit = current_balance - 1000.0 # Assumendo 1000 come base
            self.lbl_profit.setText(f"📈 Profitto Netto: € {net_profit:.2f}")
            
            # Log silenzioso (Debug) per tracciamento vita
            logging.debug(f"📊 [HISTORY] Refresh eseguito. Saldo: {current_balance}, Bet attive: {pending_count}")

        except Exception as e:
            logging.error(f"❌ [HISTORY] Errore durante il refresh dello storico: {e}")
