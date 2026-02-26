import os
import yaml
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QPushButton, QLabel, QLineEdit, QFormLayout,
    QCheckBox, QComboBox, QGroupBox
)
from core.config_paths import ROBOTS_FILE, CONFIG_FILE
from core.secure_storage import RobotManager, BookmakerManager


class RobotsTab(QWidget):
    def __init__(self, logger, controller):
        super().__init__()
        self.logger = logger
        self.controller = controller
        self.manager = RobotManager()
        self.current_idx = -1

        layout = QHBoxLayout(self)

        # =========================
        # PANNELLO SINISTRO
        # =========================
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("🤖 ROBOTS ATTIVI:"))

        self.list = QListWidget()
        self.list.currentRowChanged.connect(self.select_item)
        left_panel.addWidget(self.list)

        btn_del = QPushButton("❌ Elimina Robot")
        btn_del.setStyleSheet("background-color: #c0392b; color: white;")
        btn_del.clicked.connect(self.delete_selected)
        left_panel.addWidget(btn_del)

        # =========================
        # PANNELLO DESTRO
        # =========================
        right_group = QGroupBox("Configurazione Strategia")
        right_layout = QVBoxLayout()
        form = QFormLayout()

        # Start / Stop robot
        self.robot_active_btn = QPushButton("🟢 Robot ATTIVO")
        self.robot_active_btn.setCheckable(True)
        self.robot_active_btn.setChecked(True)
        self.robot_active_btn.setStyleSheet("""
            QPushButton:checked { background-color: #2e7d32; color: white; font-weight: bold; padding: 10px;}
            QPushButton:!checked { background-color: #f57c00; color: white; font-weight: bold; padding: 10px;}
        """)
        self.robot_active_btn.toggled.connect(self.on_robot_toggle)

        self.in_name = QLineEdit()
        self.in_name.textChanged.connect(self.update_data)

        self.in_book = QComboBox()
        self.in_book.addItems([b.get("id") for b in BookmakerManager().all()])
        self.in_book.currentTextChanged.connect(self.update_data)

        self.in_triggers = QLineEdit()
        self.in_triggers.textChanged.connect(self.update_data)

        self.in_exclude = QLineEdit()
        self.in_exclude.textChanged.connect(self.update_data)

        # modalità MM
        self.in_mm_mode = QComboBox()
        self.in_mm_mode.addItems(["Stake Fisso", "Roserpina (Progressione)"])
        self.in_mm_mode.currentTextChanged.connect(self.update_data)

        self.in_stake = QLineEdit()
        self.in_stake.textChanged.connect(self.update_data)

        form.addRow("Stato Robot:", self.robot_active_btn)
        form.addRow("Nome Robot:", self.in_name)
        form.addRow("Collega a Account:", self.in_book)
        form.addRow("Trigger Words:", self.in_triggers)
        form.addRow("Exclude Words:", self.in_exclude)
        form.addRow("Gestione Cassa:", self.in_mm_mode)
        form.addRow("Stake Fisso (€):", self.in_stake)

        right_layout.addLayout(form)

        btn_add = QPushButton("➕ Crea Nuovo Robot")
        btn_add.setStyleSheet(
            "background-color: #27ae60; color: white; font-weight: bold; padding: 8px;"
        )
        btn_add.clicked.connect(self.add_robot)
        right_layout.addWidget(btn_add)

        right_group.setLayout(right_layout)

        layout.addLayout(left_panel, 1)
        layout.addWidget(right_group, 2)

        self.refresh()

    # =========================
    # REFRESH LISTA
    # =========================
    def refresh(self):
        self.list.clear()

        self.in_book.blockSignals(True)
        self.in_book.clear()
        self.in_book.addItems([b.get("id") for b in BookmakerManager().all()])
        self.in_book.blockSignals(False)

        for r in self.manager.all():
            status_icon = "🟢" if r.get("is_active", True) else "⏸️"
            self.list.addItem(f"{status_icon} {r['name']} ➔ {r.get('bookmaker_id', 'Nessuno')}")

    # =========================
    # SELECT ROBOT
    # =========================
    def select_item(self, idx):
        if idx < 0:
            return

        self.current_idx = idx
        d = self.manager.all()[idx]

        self.in_name.blockSignals(True)
        self.in_book.blockSignals(True)
        self.in_triggers.blockSignals(True)
        self.in_exclude.blockSignals(True)
        self.in_mm_mode.blockSignals(True)
        self.in_stake.blockSignals(True)
        self.robot_active_btn.blockSignals(True)

        self.in_name.setText(d.get("name", ""))
        self.in_book.setCurrentText(d.get("bookmaker_id", ""))
        self.in_triggers.setText(", ".join(d.get("trigger_words", [])))
        self.in_exclude.setText(", ".join(d.get("exclude_words", [])))

        mm_mode = d.get("mm_mode", "Stake Fisso")
        if self.in_mm_mode.findText(mm_mode) >= 0:
            self.in_mm_mode.setCurrentText(mm_mode)
        else:
            self.in_mm_mode.setCurrentIndex(0)

        self.in_stake.setText(str(d.get("stake", "2.0")))

        is_active = d.get("is_active", True)
        self.robot_active_btn.setChecked(is_active)
        self.robot_active_btn.setText("🟢 Robot ATTIVO" if is_active else "⏸️ Robot IN PAUSA")

        self.in_name.blockSignals(False)
        self.in_book.blockSignals(False)
        self.in_triggers.blockSignals(False)
        self.in_exclude.blockSignals(False)
        self.in_mm_mode.blockSignals(False)
        self.in_stake.blockSignals(False)
        self.robot_active_btn.blockSignals(False)

    # =========================
    # TOGGLE
    # =========================
    def on_robot_toggle(self, checked):
        self.robot_active_btn.setText("🟢 Robot ATTIVO" if checked else "⏸️ Robot IN PAUSA")
        self.update_data()

    # =========================
    # UPDATE DATA
    # =========================
    def update_data(self):
        if self.current_idx < 0:
            return

        data = self.manager.all()
        d = data[self.current_idx]

        d["name"] = self.in_name.text()
        d["bookmaker_id"] = self.in_book.currentText()
        d["trigger_words"] = [w.strip() for w in self.in_triggers.text().split(",") if w.strip()]
        d["exclude_words"] = [w.strip() for w in self.in_exclude.text().split(",") if w.strip()]
        d["mm_mode"] = self.in_mm_mode.currentText()
        d["stake"] = self.in_stake.text()
        d["is_active"] = self.robot_active_btn.isChecked()

        self.manager.save_all(data)

        status_icon = "🟢" if d["is_active"] else "⏸️"
        self.list.item(self.current_idx).setText(
            f"{status_icon} {d['name']} ➔ {d['bookmaker_id']}"
        )

    # =========================
    # ADD ROBOT
    # =========================
    def add_robot(self):
        data = self.manager.all()
        new_id = f"robot_{len(data)+1}"

        data.append({
            "id": new_id,
            "name": "Nuovo Robot",
            "bookmaker_id": "",
            "trigger_words": [],
            "exclude_words": [],
            "mm_mode": "Stake Fisso",
            "stake": "2.0",
            "is_active": True
        })

        self.manager.save_all(data)
        self.refresh()
        self.list.setCurrentRow(len(self.manager.all()) - 1)

    # =========================
    # DELETE
    # =========================
    def delete_selected(self):
        row = self.list.currentRow()
        if row < 0:
            return

        data = self.manager.all()
        self.manager.delete(data[row]["id"])
        self.refresh()
