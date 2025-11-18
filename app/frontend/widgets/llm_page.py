from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class LLMManagementPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        header = QHBoxLayout()
        info = QVBoxLayout()
        title = QLabel("Language Model Management")
        title.setStyleSheet("font-size:20px; font-weight:600;")
        subtitle = QLabel(
            "Configure en beheer de AI taalmodellen voor het Loci Scientia systeem"
        )
        subtitle.setStyleSheet("color:#9ca3af;")
        info.addWidget(title)
        info.addWidget(subtitle)
        header.addLayout(info, 1)
        add_btn = QPushButton("Model Toevoegen")
        add_btn.setStyleSheet(
            "background:#2563eb; color:white; border-radius:8px; padding:8px 16px;"
        )
        header.addWidget(add_btn, 0)
        layout.addLayout(header)

        models = [
            {
                "name": "GPT-4 Turbo",
                "provider": "OpenAI",
                "version": "gpt-4-turbo-preview",
                "default": True,
                "metrics": {"Prestaties": 95, "Nauwkeurigheid": 98, "Snelheid": 85},
                "context": "128.000 tokens",
                "max_tokens": "4.096",
            },
            {
                "name": "Claude 3 Opus",
                "provider": "Anthropic",
                "version": "claude-3-opus-20240229",
                "default": False,
                "metrics": {"Prestaties": 93, "Nauwkeurigheid": 96, "Snelheid": 80},
                "context": "200.000 tokens",
                "max_tokens": "4.096",
            },
            {
                "name": "Llama 3 70B",
                "provider": "Meta",
                "version": "llama-3-70b-instruct",
                "default": False,
                "metrics": {"Prestaties": 88, "Nauwkeurigheid": 90, "Snelheid": 92},
                "context": "8.192 tokens",
                "max_tokens": "2.048",
            },
        ]

        grid = QGridLayout()
        grid.setSpacing(12)
        for idx, model in enumerate(models):
            grid.addWidget(self._model_card(model), idx // 2, idx % 2)
        layout.addLayout(grid)

    def _model_card(self, data: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel(f"{data['name']} • {data['provider']}")
        title.setStyleSheet("font-weight:600;")
        header.addWidget(title)
        if data.get("default"):
            badge = QLabel("Default")
            badge.setStyleSheet(
                "background:#2563eb; color:white; border-radius:6px; padding:2px 8px;"
            )
            header.addWidget(badge, 0, Qt.AlignVCenter)
        header.addStretch(1)
        toggle = QPushButton("Actief" if data.get("default") else "Inschakelen")
        toggle.setCheckable(True)
        toggle.setChecked(bool(data.get("default")))
        toggle.setStyleSheet(
            "border:1px solid #374151; border-radius:8px; padding:4px 12px;"
        )
        header.addWidget(toggle)
        card_layout.addLayout(header)

        version = QLabel(data["version"])
        version.setStyleSheet("color:#9ca3af;")
        card_layout.addWidget(version)

        metrics_layout = QGridLayout()
        metrics_layout.setSpacing(8)
        for idx, (label, value) in enumerate(data["metrics"].items()):
            metrics_layout.addWidget(QLabel(label), idx, 0)
            metrics_layout.addWidget(QLabel(f"{value}%"), idx, 1)
        card_layout.addLayout(metrics_layout)

        token_grid = QGridLayout()
        token_grid.addWidget(QLabel("Context Window"), 0, 0)
        token_grid.addWidget(QLabel(data["context"]), 0, 1)
        token_grid.addWidget(QLabel("Max Tokens"), 1, 0)
        token_grid.addWidget(QLabel(data["max_tokens"]), 1, 1)
        card_layout.addLayout(token_grid)

        actions = QHBoxLayout()
        configure = QPushButton("Configureren")
        configure.setStyleSheet(
            "border:1px solid #374151; border-radius:8px; padding:4px 12px;"
        )
        set_default = QPushButton("Set Default")
        set_default.setStyleSheet("border-radius:8px; padding:4px 12px;")
        delete = QPushButton("Verwijderen")
        delete.setStyleSheet(
            "border:1px solid #ef4444; color:#ef4444; border-radius:8px; padding:4px 12px;"
        )
        actions.addWidget(configure)
        actions.addWidget(set_default)
        actions.addWidget(delete)
        card_layout.addLayout(actions)
        return card
