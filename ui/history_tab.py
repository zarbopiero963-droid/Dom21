import sqlite3
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QTableWidget, QTableWidgetItem, QPushButton, 
                             QLabel, QHeaderView, QGroupBox)
from PySide6.QtCore import QTimer, Qt

class HistoryTab(QWidget):
    def __init__(self, logger, controller):
        super().__init__()
        self.logger = logger
        self.controller = controller
        self.db = controller.db
        
        self.setup_ui()
        self.refresh_data()
        
        # Auto-refresh ogni 5 secondi per monitoraggio in tempo reale
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(5000)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # --- TOP: STATISTICHE BANKROLL ---
        top_layout = QHBoxLayout()
        self.lbl_bankroll = QLabel("Bankroll: €0.00")
        self.lbl_bankroll.setStyleSheet("font-size: 20px; font-weight: bold; color: #2ecc71;")
        self.lbl_peak = QLabel("Picco Max: €0.00")
        self.lbl_peak.setStyleSheet("font-size: 16px; font-weight: bold; color: #f1c40f;")
        self.lbl_drawdown = QLabel("Drawdown: 0.00%")
        self.lbl_drawdown.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c;")
        
        btn_refresh = QPushButton("🔄 Aggiorna Cruscotto")
        btn_refresh.setStyleSheet("padding: 8px; font-weight: bold; background-color: #34495e; color: white;")
        btn_refresh.clicked.connect(self.refresh_data)
        
        top_layout.addWidget(self.lbl_bankroll)
        top_layout.addWidget(self.lbl_peak)
        top_layout.addWidget(self.lbl_drawdown)
        top_layout.addStretch()
        top_layout.addWidget(btn_refresh)
        
        layout.addLayout(top_layout)
        
        # --- MIDDLE: I 5 TAVOLI ROSERPINA ---
        tables_group = QGroupBox("🧠 Stato Tavoli Paralleli (Risk Engine)")
        tables_layout = QHBoxLayout()
        
        self.lbl_tables = []
        for i in range(5):
            lbl = QLabel(f"Tavolo {i+1}\nInattivo")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("background-color: #2c3e50; color: white; padding: 10px; border-radius: 5px;")
            tables_layout.addWidget(lbl)
            self.lbl_tables.append(lbl)
            
        tables_group.setLayout(tables_layout)
        layout.addWidget(tables_group)
        
        # --- BOTTOM: CRONOLOGIA SCOMMESSE ---
        history_group = QGroupBox("📜 Cronologia Operazioni (Ultime 100 transazioni)")
        history_layout = QVBoxLayout()
        
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Data", "Tavolo", "Stato", "Stake (€)", "Esito (€)", "TX ID"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        
        history_layout.addWidget(self.table)
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)

    def refresh_data(self):
        try:
            # 1. Aggiorna Bankroll Globale
            bal, peak = self.db.get_balance()
            drawdown = ((bal - peak) / peak * 100) if peak > 0 else 0.0
            
            self.lbl_bankroll.setText(f"Bankroll: €{bal:.2f}")
            self.lbl_peak.setText(f"Picco Max: €{peak:.2f}")
            self.lbl_drawdown.setText(f"Drawdown: {drawdown:.2f}%")
            
            if drawdown < -10:
                self.lbl_drawdown.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c;") # Rosso Allarme
            else:
                self.lbl_drawdown.setStyleSheet("font-size: 16px; font-weight: bold; color: #2ecc71;") # Verde Sicuro

            # 2. Aggiorna Stato dei 5 Tavoli
            tables = self.db.get_roserpina_tables()
            active_pending = self.db.pending()
            active_table_ids = [p.get("table_id") for p in active_pending]
            
            for i, t in enumerate(tables):
                if i >= len(self.lbl_tables): break
                t_id = t["table_id"]
                profit = t["profit"]
                loss = t["loss"]
                in_rec = t["in_recovery"]
                
                status_text = ""
                bg_color = "#2c3e50" # Grigio Inattivo
                
                if t_id in active_table_ids:
                    status_text = "🔄 OCCUPATO (Bet Aperta)"
                    bg_color = "#2980b9" # Blu
                elif in_rec == 1:
                    status_text = "⚠️ IN RECOVERY"
                    bg_color = "#d35400" # Arancione
                else:
                    status_text = "✅ LIBERO"
                    bg_color = "#27ae60" # Verde
                    
                info = f"Tavolo {t_id}\n{status_text}\nProfitto: €{profit:.2f}\nLoss: €{loss:.2f}"
                self.lbl_tables[i].setText(info)
                self.lbl_tables[i].setStyleSheet(f"background-color: {bg_color}; color: white; padding: 15px; border-radius: 6px; font-weight: bold;")

            # 3. Aggiorna Cronologia Scommesse
            with self.db._lock:
                cur = self.db.conn.execute("SELECT * FROM journal ORDER BY timestamp DESC LIMIT 100")
                rows = cur.fetchall()
            
            self.table.setRowCount(0)
            for row_data in rows:
                r = dict(row_data)
                row_idx = self.table.rowCount()
                self.table.insertRow(row_idx)
                
                # Formattazione Data
                dt = datetime.fromtimestamp(r.get("timestamp", 0)).strftime('%d/%m/%Y %H:%M:%S')
                
                # Calcolo Profitto Netto
                payout = r.get("payout", 0.0)
                amount = r.get("amount", 0.0)
                status = r.get("status", "")
                
                if status == 'SETTLED':
                    if payout > 0:
                        profit_netto = payout - amount
                        esito_str = f"+€{profit_netto:.2f}"
                        color = Qt.green
                    else:
                        esito_str = f"-€{amount:.2f}"
                        color = Qt.red
                elif status == 'VOID':
                    esito_str = "RIMBORSATA"
                    color = Qt.yellow
                else:
                    esito_str = "In Attesa ⏳"
                    color = Qt.white
                
                # Inserimento in tabella
                self.table.setItem(row_idx, 0, QTableWidgetItem(dt))
                self.table.setItem(row_idx, 1, QTableWidgetItem(f"Tavolo {r.get('table_id', 1)}"))
                self.table.setItem(row_idx, 2, QTableWidgetItem(status))
                self.table.setItem(row_idx, 3, QTableWidgetItem(f"€{amount:.2f}"))
                
                item_esito = QTableWidgetItem(esito_str)
                item_esito.setForeground(color)
                self.table.setItem(row_idx, 4, item_esito)
                
                self.table.setItem(row_idx, 5, QTableWidgetItem(r.get("tx_id", "")[:8]))
                
        except Exception as e:
            self.logger.error(f"Errore aggiornamento cruscotto: {e}")
