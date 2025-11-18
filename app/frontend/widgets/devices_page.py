from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DevicesPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        header = QVBoxLayout()
        title = QLabel("Connected Devices & Gebruikersbeheer")
        title.setStyleSheet("font-size:20px; font-weight:600;")
        subtitle = QLabel(
            "Beheer verbonden apparaten en gebruikersaccounts voor het systeem"
        )
        subtitle.setStyleSheet("color:#9ca3af;")
        header.addWidget(title)
        header.addWidget(subtitle)
        layout.addLayout(header)

        top_actions = QHBoxLayout()
        top_actions.addWidget(QLabel("2 actief • 1 inactief • 1 geblokkeerd"))
        top_actions.addStretch(1)
        add_btn = QPushButton("Apparaat toevoegen")
        add_btn.setStyleSheet(
            "background:#2563eb; color:white; border-radius:8px; padding:6px 12px;"
        )
        top_actions.addWidget(add_btn)
        layout.addLayout(top_actions)

        devices = [
            {
                "name": "iPhone 14 Pro",
                "owner": "Jan de Vries",
                "ip": "192.168.1.105",
                "mac": "00:1B:44:11:3A:B7",
                "status": "Online",
                "rights": ["read", "write", "chat"],
            },
            {
                "name": "MacBook Pro",
                "owner": "Anna Jansen",
                "ip": "192.168.1.102",
                "mac": "00:1B:44:11:3A:C8",
                "status": "Online",
                "rights": ["read", "write", "chat", "admin"],
            },
            {
                "name": "iPad Air",
                "owner": "Pieter Smit",
                "ip": "192.168.1.108",
                "mac": "00:1B:44:11:3A:D9",
                "status": "Offline",
                "rights": ["read", "chat"],
            },
            {
                "name": "Windows Desktop",
                "owner": "Lisa de Boer",
                "ip": "192.168.1.110",
                "mac": "00:1B:44:11:3A:E2",
                "status": "Geblokkeerd",
                "rights": [],
            },
        ]

        grid = QGridLayout()
        grid.setSpacing(12)
        for idx, device in enumerate(devices):
            grid.addWidget(self._device_card(device), idx // 2, idx % 2)
        layout.addLayout(grid)

    def _device_card(self, device: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        header = QHBoxLayout()
        name = QLabel(device["name"])
        name.setStyleSheet("font-weight:600;")
        header.addWidget(name)
        status = QLabel(device["status"])
        color = "#10b981" if device["status"] == "Online" else "#f59e0b"
        if device["status"] == "Geblokkeerd":
            color = "#ef4444"
        status.setStyleSheet(f"color:{color}; border:1px solid {color}; border-radius:6px; padding:2px 8px;")
        header.addWidget(status, 0)
        layout.addLayout(header)

        layout.addWidget(QLabel(f"Gebruiker: {device['owner']}"))
        layout.addWidget(QLabel(f"IP: {device['ip']}"))
        layout.addWidget(QLabel(f"MAC: {device['mac']}"))

        rights = QLabel("Rechten: " + (", ".join(device["rights"]) or "geen"))
        rights.setStyleSheet("color:#9ca3af;")
        layout.addWidget(rights)

        actions = QHBoxLayout()
        block = QPushButton("Blokkeren")
        block.setStyleSheet("border:1px solid #374151; border-radius:8px; padding:4px 12px;")
        remove = QPushButton("Verwijderen")
        remove.setStyleSheet("border:1px solid #ef4444; color:#ef4444; border-radius:8px; padding:4px 12px;")
        actions.addWidget(block)
        actions.addWidget(remove)
        layout.addLayout(actions)
        return card
