import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLabel, QLineEdit, QPushButton, QListWidget, QGroupBox)
from core.secure_storage import BookmakerManager

class BookmakerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.manager = BookmakerManager()

        layout = QHBoxLayout(self)
        
        # --- PANNELLO SINISTRO (Lista) ---
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("🏦 ACCOUNT BOOKMAKERS:"))
        
        self.list = QListWidget()
        left_panel.addWidget(self.list)

        btn_del = QPushButton("❌ Elimina Selezionato")
        btn_del.setStyleSheet("background-color: #c0392b; color: white; padding: 5px;")
        btn_del.clicked.connect(self.delete_selected)
        left_panel.addWidget(btn_del)
        
        # --- PANNELLO DESTRO (Form) ---
        right_group = QGroupBox("Aggiungi Nuovo Account")
        right_layout = QVBoxLayout()
        form = QFormLayout()

        self.name = QLineEdit()
        self.name.setPlaceholderText("Es: Bet365_Principale")
        self.user = QLineEdit()
        self.pwd = QLineEdit()
        self.pwd.setEchoMode(QLineEdit.Password)

        form.addRow("Nome Bookmaker:", self.name)
        form.addRow("Username:", self.user)
        form.addRow("Password:", self.pwd)
        
        right_layout.addLayout(form)

        btn_add = QPushButton("➕ Salva Bookmaker")
        btn_add.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px;")
        btn_add.clicked.connect(self.add_bookmaker)
        right_layout.addWidget(btn_add)
        
        right_group.setLayout(right_layout)

        layout.addLayout(left_panel, 1)
        layout.addWidget(right_group, 2)
        
        self.refresh()

    def refresh(self):
        self.list.clear()
        for b in self.manager.all():
            self.list.addItem(f"{b['name']} | User: {b['username']}")

    def add_bookmaker(self):
        b_name = self.name.text()
        b_user = self.user.text()
        b_pwd = self.pwd.text()
        
        if b_name and b_user and b_pwd:
            logging.info(f"🖱️ [UI] Tentativo di salvataggio credenziali per il bookmaker: {b_name}")
            self.manager.add(b_name, b_user, b_pwd)
            self.name.clear()
            self.user.clear()
            self.pwd.clear()
            self.refresh()
            logging.info(f"✅ [VAULT] Credenziali per '{b_name}' salvate e criptate con successo.")
        else:
            logging.warning("⚠️ [UI] Tentativo di salvataggio fallito: campi incompleti.")

    def delete_selected(self):
        items = self.list.selectedItems()
        if not items:
            return
        for item in items:
            name = item.text().split(" | ")[0]
            logging.warning(f"🖱️ [UI] Richiesta eliminazione account dal Vault: {name}")
            self.manager.delete(name)
            self.list.takeItem(self.list.row(item))
            logging.info(f"🗑️ [VAULT] Account '{name}' eliminato definitivamente.")
