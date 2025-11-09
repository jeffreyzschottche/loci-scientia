import psutil
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QFrame


class SSDMonitor(QFrame):
    def __init__(self, mount: str = "/"):
        super().__init__()
        self.setObjectName("Card")
        self.mount = mount
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.title = QLabel("SSD Monitor")
        self.info = QLabel("")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)

        layout.addWidget(self.title)
        layout.addWidget(self.info)
        layout.addWidget(self.bar)

        timer = QTimer(self)
        timer.timeout.connect(self.refresh)
        timer.start(2000)
        self.refresh()

    def refresh(self):
        usage = psutil.disk_usage(self.mount)
        self.info.setText(
            f"{self.mount}: {usage.used // (1024**3)} / {usage.total // (1024**3)} GB gebruikt"
        )
        self.bar.setValue(int(usage.percent))
