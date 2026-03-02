import os
import sys
import io
import contextlib
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                               QTextEdit, QLabel, QHBoxLayout)
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QFont

# Importiamo direttamente la funzione
from GOD_CERTIFICATION import run_god_certification

class StreamInterceptor(io.StringIO):
    """Intercetta gli output di 'print' e li emette come segnali riga per riga."""
    def __init__(self, signal):
        super().__init__()
        self.signal = signal

    def write(self, text):
        super().write(text)
        if text.strip():
            self._emit_colored(text.strip())
            
    def _emit_colored(self, line):
        color = "white"
        if "VERIFIED" in line or "PASSA" in line or "OK" in line or "✅" in line or "🟢" in line:
            color = "#00ff00" # Verde
        elif "FAIL" in line or "🔴" in line or "❌" in line:
            color = "#ff3333" # Rosso
        elif "🔹" in line or "🚀" in line or "👑" in line:
            color = "#00ccff" # Azzurro
        elif "⚠️" in line:
            color = "yellow"

        self.signal.emit(line, color)


class GodWorker(QThread):
    """
    Esegue la certificazione internamente, dirottando stdout verso la UI.
    """
    log_signal = Signal(str, str) # text, color
    finished_signal = Signal(bool)

    def run(self):
        self.log_signal.emit("🧠 INIZIALIZZAZIONE VALIDAZIONE ARCHITETTURA (GOD CERTIFICATION)...", "cyan")
        self.log_signal.emit("Esecuzione dei test in ambiente isolato.\n", "white")

        success = False
        
        # Dirottiamo temporaneamente l'output standard
        interceptor = StreamInterceptor(self.log_signal)
        with contextlib.redirect_stdout(interceptor):
            try:
                # Eseguiamo la funzione direttamente
                success = run_god_certification()
            except Exception as e:
                self.log_signal.emit(f"🚨 Errore fatale di esecuzione: {e}", "red")
                success = False

        self.finished_signal.emit(success)


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
