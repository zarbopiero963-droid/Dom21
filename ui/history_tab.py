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
        
        # =========================================================
        # 📊 DASHBOARD STATS (CRUSCOTTO SUPERIORE)
        # =========================================================
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
        
        # =========================================================
        # 🗃️ TABELLA TRANSAZIONI (LEDGER)
        # =========================================================
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["ID TX", "Data", "Squadre", "Tavolo", "Stato", "Puntata (€)", "Vincita (€)", "Profitto (€)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #121212; color: white; gridline-color: #333; border-radius: 5px; }
            QHeaderView::section { background-color: #2c2c2c; color: #00ccff; font-weight: bold; padding: 5px; border: 1px solid #444; }
        """)
        layout.addWidget(self.table)
        
        # =========================================================
        # 🔄 CONTROLLI E TIMER
        # =========================================================
        btn_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄 Aggiorna Dati Database")
        self.btn_refresh.setMinimumHeight(40)
        self.btn_refresh.setStyleSheet("background-color: #1976d2; color: white; font-weight: bold; border-radius: 5px;")
        self.btn_refresh.clicked.connect(self.refresh_data)
        btn_layout.addWidget(self.btn_refresh)
        layout.addLayout(btn_layout)
        
        # Auto-refresh ogni 2 secondi per tenere la UI reattiva senza sovraccaricare il DB
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(2000)
        
    def refresh_data(self):
        """Motore di rendering del Cruscotto. Non crasherà mai più per colonne DB mancanti."""
        if not self.controller or not hasattr(self.controller, 'db'):
            return
            
        try:
            # 1. Lettura Saldi (Bilancio Corrente e Bilancio Massimo)
            current_balance, peak_balance = self.controller.db.get_balance()
            
            # 2. Lettura ultime transazioni (Lock per sicurezza in lettura)
            with self.controller.db._lock:
                # Usiamo try/except in caso il DB non sia ancora perfettamente inizializzato
                try:
                    rows = self.controller.db.conn.execute("SELECT * FROM journal ORDER BY id DESC LIMIT 100").fetchall()
                except Exception:
                    rows = []
                
            pending_count = 0
            
            # Congela la tabella per aggiornarla senza sfarfallii grafici
            self.table.setUpdatesEnabled(False)
            self.table.setRowCount(0)
            
            for row in rows:
                tx = dict(row)
                
                # 🛠️ LA PATCH: Calcolo sicuro dei valori finanziari 🛠️
                amount = float(tx.get('amount', 0.0) or 0.0)
                payout = float(tx.get('payout', 0.0) or 0.0)
                status = str(tx.get('status', ''))
                
                # Calcolo Profitto (Al volo, non dal DB!)
                if status == 'SETTLED':
                    profitto = payout - amount
                elif status == 'VOID':
                    profitto = 0.0
                else:
                    profitto = 0.0
                    pending_count += 1
                    
                # Inserimento riga
                row_idx = self.table.rowCount()
                self.table.insertRow(row_idx)
                
                # Formattazione Timestamp
                ts = tx.get('timestamp', 0)
                date_str = datetime.fromtimestamp(ts).strftime('%H:%M:%S | %d/%m') if ts else "N/A"
                
                # Compilazione Colonne Base
                self.table.setItem(row_idx, 0, QTableWidgetItem(str(tx.get('tx_id', ''))[:8] + "..."))
                self.table.setItem(row_idx, 1, QTableWidgetItem(date_str))
                self.table.setItem(row_idx, 2, QTableWidgetItem(str(tx.get('teams', ''))))
                self.table.setItem(row_idx, 3, QTableWidgetItem(str(tx.get('table_id', '1'))))
                
                # Colonna Stato (Colorata)
                item_status = QTableWidgetItem(status)
                item_status.setFont(self.table.font())
                if status == 'SETTLED': item_status.setForeground(QColor("#00ff00")) # Verde
                elif status == 'VOID': item_status.setForeground(QColor("#aaaaaa")) # Grigio
                elif status == 'RESERVED' or status == 'PLACED': item_status.setForeground(QColor("#ffb300")) # Arancio
                self.table.setItem(row_idx, 4, item_status)
                
                # Colonne Finanziarie
                self.table.setItem(row_idx, 5, QTableWidgetItem(f"€ {amount:.2f}"))
                self.table.setItem(row_idx, 6, QTableWidgetItem(f"€ {payout:.2f}"))
                
                # Colonna Profitto (Colorata Dinamicamente)
                item_profit = QTableWidgetItem(f"€ {profitto:.2f}")
                if profitto > 0:
                    item_profit.setForeground(QColor("#00ff00"))
                elif profitto < 0:
                    item_profit.setForeground(QColor("#ff3333"))
                self.table.setItem(row_idx, 7, item_profit)
                
                # Allinea tutte le celle al centro
                for col in range(8):
                    if self.table.item(row_idx, col):
                        self.table.item(row_idx, col).setTextAlignment(Qt.AlignCenter)
            
            # Sblocca l'aggiornamento grafico
            self.table.setUpdatesEnabled(True)
            
            # 3. Aggiornamento Label Cruscotto
            self.lbl_balance.setText(f"💰 Saldo Attuale: € {current_balance:.2f}")
            self.lbl_peak.setText(f"⛰️ Peak Balance: € {peak_balance:.2f}")
            self.lbl_pending.setText(f"⏳ In Corso: {pending_count}")
            
            # Profitto Netto Totale (Saldo Attuale - Capitale Iniziale 1000)
            net_profit = current_balance - 1000.0
            self.lbl_profit.setText(f"📈 Profitto Netto: € {net_profit:.2f}")
            
            if net_profit >= 0:
                self.lbl_profit.setStyleSheet("font-size: 16px; font-weight: bold; background-color: #1b5e20; padding: 12px; border-radius: 6px; border: 1px solid #00ff00;")
            else:
                self.lbl_profit.setStyleSheet("font-size: 16px; font-weight: bold; background-color: #b71c1c; padding: 12px; border-radius: 6px; border: 1px solid #ff0000;")

        except Exception as e:
            # Ripristina aggiornamenti grafici in caso di errore
            self.table.setUpdatesEnabled(True)
            self.logger.error(f"Errore aggiornamento cruscotto Risk Desk: {e}")
