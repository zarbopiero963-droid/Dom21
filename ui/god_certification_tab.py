import os
import sys
import subprocess
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                               QTextEdit, QLabel, QHBoxLayout)
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QFont

class GodWorker(QThread):
    """
    Esegue GOD_CERTIFICATION.py come processo separato e ne cattura 
    l'output (stdout/stderr) in tempo reale per stamparlo nella UI.
    """
    log_signal = Signal(str, str) # text, color
    finished_signal = Signal(bool)

    def run(self):
        # Percorso assoluto della root del progetto
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        script_path = os.path.join(root_dir, "GOD_CERTIFICATION.py")

        if not os.path.exists(script_path):
            self.log_signal.emit(f"❌ Errore: File non trovato in {script_path}", "red")
            self.finished_signal.emit(False)
            return

        self.log_signal.emit("🧠 INIZIALIZZAZIONE VALIDAZIONE ARCHITETTURA (GOD CERTIFICATION)...", "cyan")
        self.log_signal.emit("Esecuzione dei test in ambiente isolato.\n", "white")

        # Forziamo Python a non usare il buffer, così l'output arriva riga per riga in tempo reale
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        try:
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                cwd=root_dir # Eseguiamo dalla cartella principale
            )

            # Leggiamo l'output del terminale in diretta
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue

                # Colorazione intelligente basata sul testo
                color = "white"
                if "PASSED" in line or "CERTIFICATO PRODUZIONE" in line or "🟢" in line:
                    color = "#00ff00" # Verde
                elif "FAILED" in line or "NON CERTIFICATO" in line or "🔴" in line or "❌" in line:
                    color = "#ff3333" # Rosso
                elif "Running:" in line or "🚀" in line:
                    color = "#00ccff" # Azzurro
                elif "⚠️" in line:
                    color = "yellow"

                self.log_signal.emit(line, color)

            process.stdout.close()
            process.wait()

            success = process.returncode == 0
            self.finished_signal.emit(success)

        except Exception as e:
            self.log_signal.emit(f"🚨 Errore fatale di esecuzione: {e}", "red")
            self.finished_signal.emit(False)


class GodCertificationTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # Header Info
        header_layout = QHBoxLayout()
        info_label = QLabel("🧠 <b>GOD CERTIFICATION:</b> Valida l'intera architettura (Core, DB, Anti-Detect, UI) con un singolo click.")
        header_layout.addWidget(info_label)
        
        self.start_btn = QPushButton("🏆 AVVIA GOD CERTIFICATION")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet("background-color: #1a1a1a; color: #00ccff; font-weight: bold; border: 1px solid #00ccff; border-radius: 5px;")
        self.start_btn.clicked.connect(self.start_audit)
        header_layout.addWidget(self.start_btn)
        
        layout.addLayout(header_layout)

        # Console Log
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("background-color: #0d0d0d; color: #ffffff; padding: 10px; border-radius: 5px;")
        font = QFont("Courier", 10)
        self.console.setFont(font)
        layout.addWidget(self.console)

        self.worker = None

    def start_audit(self):
        self.start_btn.setEnabled(False)
        self.start_btn.setText("⏳ CERTIFICAZIONE IN CORSO... ATTENDI")
        self.start_btn.setStyleSheet("background-color: #333333; color: yellow; font-weight: bold; border: 1px solid yellow; border-radius: 5px;")
        self.console.clear()
        
        self.worker = GodWorker()
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.audit_finished)
        self.worker.start()

    def append_log(self, text, color):
        html_text = f"<span style='color:{color};'>{text}</span>"
        self.console.append(html_text)
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def audit_finished(self, success):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("🏆 RIPETI GOD CERTIFICATION")
        if success:
            self.start_btn.setStyleSheet("background-color: #1b5e20; color: white; font-weight: bold; border: 1px solid #00ff00; border-radius: 5px;")
        else:
            self.start_btn.setStyleSheet("background-color: #b71c1c; color: white; font-weight: bold; border: 1px solid #ff0000; border-radius: 5px;")
