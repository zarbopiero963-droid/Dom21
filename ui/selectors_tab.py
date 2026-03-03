import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLabel, QLineEdit, QPushButton, QListWidget, QGroupBox)
from core.secure_storage import SelectorManager

class SelectorsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.manager = SelectorManager()

        layout = QHBoxLayout(self)
        
        # --- PANNELLO SINISTRO (Lista) ---
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("🧩 SELETTORI DOM:"))
        
        self.list = QListWidget()
        left_panel.addWidget(self.list)

        btn_del = QPushButton("❌ Elimina Selezionato")
        btn_del.setStyleSheet("background-color: #c0392b; color: white; padding: 5px;")
        btn_del.clicked.connect(self.delete_selected)
        left_panel.addWidget(btn_del)
        
        # --- PANNELLO DESTRO (Form) ---
        right_group = QGroupBox("Aggiungi Nuovo Selettore")
        right_layout = QVBoxLayout()
        form = QFormLayout()

        self.name = QLineEdit()
        self.name.setPlaceholderText("Es: pulsante_quota")
        self.book = QLineEdit()
        self.book.setPlaceholderText("Es: Bet365")
        self.value = QLineEdit()
        self.value.setPlaceholderText("Es: .gl-Participant_Odds")

        form.addRow("Nome selettore:", self.name)
        form.addRow("Bookmaker target:", self.book)
        form.addRow("Valore (CSS/XPath):", self.value)
        
        right_layout.addLayout(form)

        btn_add = QPushButton("➕ Salva Selettore")
        btn_add.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 8px;")
        btn_add.clicked.connect(self.add_selector)
        right_layout.addWidget(btn_add)
        
        right_group.setLayout(right_layout)

        layout.addLayout(left_panel, 1)
        layout.addWidget(right_group, 2)
        
        self.refresh()

    def refresh(self):
        self.list.clear()
        for s in self.manager.all():
            self.list.addItem(f"{s['name']} | Book: {s['bookmaker']} | {s['value']}")

    def add_selector(self):
        s_name = self.name.text()
        s_book = self.book.text()
        s_val = self.value.text()
        
        if s_name and s_val:
            logging.info(f"🖱️ [UI] Aggiornamento selettore DOM '{s_name}' per {s_book} -> {s_val}")
            self.manager.add(s_name, s_book, s_val)
            self.name.clear()
            self.book.clear()
            self.value.clear()
            self.refresh()
            logging.info(f"✅ [DOM] Selettore '{s_name}' salvato. Verrà usato al prossimo avvio/scommessa.")
        else:
            logging.warning("⚠️ [UI] Impossibile salvare selettore: campi vuoti.")

    def delete_selected(self):
        items = self.list.selectedItems()
        if not items:
            return
        for item in items:
            name = item.text().split(" | ")[0]
            logging.warning(f"🖱️ [UI] Eliminazione selettore DOM: {name}")
            self.manager.delete(name)
            self.list.takeItem(self.list.row(item))
            logging.info(f"🗑️ [DOM] Selettore '{name}' rimosso dal database.")
