import os
import asyncio
import sys
from typing import Optional

_boot_video_mode = os.environ.get("LOCI_BOOT_VIDEO", "auto").strip().lower()
_boot_video_enabled = _boot_video_mode in {"1", "true", "yes", "on"}
if _boot_video_mode == "auto":
    _boot_video_enabled = sys.platform not in {"linux", "linux2"}

from PySide6.QtCore import QProcess, Qt, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
)
if _boot_video_enabled:
    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        from PySide6.QtMultimediaWidgets import QVideoWidget
    except Exception:  # pragma: no cover - optional multimedia support
        QAudioOutput = None
        QMediaPlayer = None
        QUrl = None
        QVideoWidget = None
else:  # pragma: no cover - boot video disabled by platform/env
    QAudioOutput = None
    QMediaPlayer = None
    QUrl = None
    QVideoWidget = None
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)
from qasync import QEventLoop

from .config import BACKEND_WS
from .net.ws_client import WSClient
from .theme import AITJE_QSS
from .translations import t, register_language_change_callback
from .widgets.chat_page import ChatPage
from .widgets.devices_page import DevicesPage
from .widgets.headerbar import HeaderBar
from .widgets.knowledge_page import KnowledgePage
from .widgets.network_page import NetworkStatusPage
from .widgets.sidebar import Sidebar
from .widgets.settings_page import SettingsPage


class RoundedProgressBar(QProgressBar):
    """Custom progress bar so rounded corners render consistently on macOS/Qt."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setRange(0, 100)
        self.setFixedHeight(28)

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        outer_rect = self.rect().adjusted(0, 0, -1, -1)
        radius = outer_rect.height() / 2

        track_path = QPainterPath()
        track_path.addRoundedRect(outer_rect, radius, radius)
        painter.fillPath(track_path, QColor("#f5f5f5"))
        painter.setPen(QPen(QColor("#e4e4e7"), 1))
        painter.drawPath(track_path)

        progress = 0 if self.maximum() <= self.minimum() else (
            (self.value() - self.minimum()) / (self.maximum() - self.minimum())
        )

        if progress > 0:
            fill_rect = outer_rect.adjusted(2, 2, -2, -2)
            fill_rect.setWidth(max(fill_rect.height(), int(fill_rect.width() * progress)))
            fill_radius = fill_rect.height() / 2

            fill_path = QPainterPath()
            fill_path.addRoundedRect(fill_rect, fill_radius, fill_radius)
            painter.fillPath(fill_path, QColor("#facc15"))


class BootDotsLoader(QWidget):
    """Triangular three-dot loading indicator next to the boot title."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._phase = 0
        self.setFixedSize(40, 35)
        self._timer = QTimer(self)
        self._timer.setInterval(333)
        self._timer.timeout.connect(self._advance)
        self._timer.start()

    def _advance(self) -> None:
        self._phase = (self._phase + 1) % 3
        self.update()

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        diameter = 12
        positions = [(14, 2), (0, 22), (28, 22)]
        intensity_sets = [
            [1.0, 0.18, 0.45],
            [0.45, 1.0, 0.18],
            [0.18, 0.45, 1.0],
        ]
        painter.setPen(Qt.NoPen)
        for (x, y), intensity in zip(positions, intensity_sets[self._phase]):
            color = QColor("#111111")
            color.setAlphaF(intensity)
            painter.setBrush(color)
            painter.drawEllipse(x, y, diameter, diameter)


class BootScreen(QWidget):
    """Animated splash screen that mimics the AITJE loading state from the Figma design."""

    # Translation keys for status steps
    STATUS_STEP_KEYS = [
        (0, "boot_starting"),
        (20, "boot_loading_neural"),
        (45, "boot_preparing_api"),
        (70, "boot_syncing_devices"),
        (90, "boot_almost_ready"),
        (100, "boot_welcome"),
    ]

    def __init__(
        self,
        logo_path: Optional[str] = None,
        duration_ms: int = 5000,
        on_finished=None,
    ):
        super().__init__()

        self.on_finished = on_finished
        self.duration_ms = duration_ms
        self.progress_value = 0
        self._media_player = None
        self._audio_output = None
        self._hero_stack = None
        self._hero_video = None
        self._hero_placeholder = None
        self._hero_video_shown = False

        self.setObjectName("BootScreenRoot")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.showFullScreen()

        self.setStyleSheet(
            """
            QWidget#BootScreenRoot {
                background: #ffffff;
                color: #111111;
            }
            QLabel#BootTitle {
                font-size: 48pt;
                font-weight: 800;
                letter-spacing: 0.04em;
                color: #111111;
            }
            QLabel#BootSubtitle {
                font-size: 14pt;
                color: #4b5563;
            }
            QLabel#BootPercent {
                font-size: 16pt;
                font-weight: 700;
                color: #111111;
            }
            """
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(80, 80, 80, 80)
        outer.setSpacing(32)
        outer.addStretch(1)

        center = QVBoxLayout()
        center.setSpacing(24)
        center.setAlignment(Qt.AlignCenter)

        hero_widget = self._build_hero_widget(logo_path)
        center.addWidget(hero_widget, 0, Qt.AlignCenter)

        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        title_row.setAlignment(Qt.AlignCenter)

        title = QLabel(t("boot_title"))
        title.setObjectName("BootTitle")
        title_row.addWidget(title, 0, Qt.AlignVCenter)

        self.title_loader = BootDotsLoader()
        title_row.addWidget(self.title_loader, 0, Qt.AlignVCenter)

        center.addLayout(title_row)

        subtitle_text = t("boot_subtitle").strip()
        if subtitle_text:
            subtitle = QLabel(subtitle_text)
            subtitle.setObjectName("BootSubtitle")
            subtitle.setAlignment(Qt.AlignCenter)
            center.addWidget(subtitle)

        outer.addLayout(center)

        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(8)

        self.progress_bar = RoundedProgressBar()
        progress_layout.addWidget(self.progress_bar)

        info_row = QHBoxLayout()
        info_row.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel(t(self.STATUS_STEP_KEYS[0][1]))
        self.status_label.setObjectName("BootSubtitle")
        info_row.addWidget(self.status_label, 1, Qt.AlignLeft)

        self.percent_label = QLabel("0%")
        self.percent_label.setObjectName("BootPercent")
        info_row.addWidget(self.percent_label, 0, Qt.AlignRight)

        progress_layout.addLayout(info_row)
        outer.addLayout(progress_layout)
        outer.addStretch(1)

        self.timer = QTimer(self)
        total_ticks = max(1, duration_ms // 60)
        self.increment = max(1, 100 // total_ticks)
        self.timer.timeout.connect(self._advance)
        self.timer.start(60)

    def _build_egg_pixmap(self, width: int, height: int) -> QPixmap:
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor("#ffffff"))
        gradient.setColorAt(1, QColor("#f7f7f7"))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor("#0a0a0a"), 4))
        painter.drawEllipse(10, 10, width - 20, height - 20)

        # Simple crack lines to mimic the Figma egg
        painter.setPen(QPen(QColor("#0a0a0a"), 2))
        painter.drawLine(width * 0.45, height * 0.35, width * 0.5, height * 0.55)
        painter.drawLine(width * 0.55, height * 0.38, width * 0.5, height * 0.6)
        painter.end()
        return pixmap

    def _build_hero_widget(self, media_path: Optional[str]) -> QWidget:
        if (
            media_path
            and media_path.lower().endswith(".mp4")
            and os.path.exists(media_path)
            and QMediaPlayer is not None
            and QVideoWidget is not None
            and QUrl is not None
        ):
            container = QWidget()
            container.setFixedSize(320, 320)
            stack = QStackedLayout(container)
            stack.setContentsMargins(0, 0, 0, 0)
            stack.setStackingMode(QStackedLayout.StackOne)

            placeholder = QLabel()
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setFixedSize(320, 320)
            placeholder.setStyleSheet("background:#ffffff;")
            poster_path = os.path.splitext(media_path)[0] + "-first-frame.png"
            poster_pixmap = QPixmap(poster_path) if os.path.exists(poster_path) else QPixmap()
            if not poster_pixmap.isNull():
                placeholder.setPixmap(
                    poster_pixmap.scaled(320, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            else:
                placeholder.setPixmap(self._build_egg_pixmap(260, 320))
            stack.addWidget(placeholder)

            video = QVideoWidget()
            video.setFixedSize(320, 320)
            video.setStyleSheet("background: #ffffff;")
            stack.addWidget(video)
            stack.setCurrentWidget(placeholder)

            self._hero_stack = stack
            self._hero_video = video
            self._hero_placeholder = placeholder

            self._media_player = QMediaPlayer(self)
            self._audio_output = QAudioOutput(self)
            self._audio_output.setMuted(True)
            self._media_player.setAudioOutput(self._audio_output)
            self._media_player.setVideoOutput(video)
            self._media_player.setSource(QUrl.fromLocalFile(media_path))
            self._media_player.setLoops(-1)
            self._media_player.positionChanged.connect(self._on_boot_media_position_changed)
            self._media_player.play()
            return container

        hero_pixmap = None
        if media_path and os.path.exists(media_path):
            hero_pixmap = QPixmap(media_path)
        hero_label = QLabel()
        hero_label.setAlignment(Qt.AlignCenter)
        if hero_pixmap and not hero_pixmap.isNull():
            hero_label.setPixmap(
                hero_pixmap.scaled(260, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            hero_label.setPixmap(self._build_egg_pixmap(260, 320))
        return hero_label

    def _show_boot_video(self):
        if self._hero_video_shown or not self._hero_stack or not self._hero_video:
            return
        self._hero_stack.setCurrentWidget(self._hero_video)
        self._hero_video_shown = True

    def _on_boot_media_position_changed(self, position: int):
        if position > 0:
            self._show_boot_video()

    def _advance(self):
        self.progress_value = min(100, self.progress_value + self.increment)
        self.progress_bar.setValue(self.progress_value)
        self.percent_label.setText(f"{self.progress_value}%")

        for threshold, key in reversed(self.STATUS_STEP_KEYS):
            if self.progress_value >= threshold:
                self.status_label.setText(t(key))
                break

        if self.progress_value >= 100:
            self.timer.stop()
            QTimer.singleShot(400, self.finish)

    def finish(self):
        if self._media_player is not None:
            self._media_player.stop()
        if self.on_finished:
            self.on_finished()
        self.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AITJE Dashboard")
        self.resize(1200, 800)

        self.ws_client = WSClient(BACKEND_WS)

        root = QWidget()
        root.setObjectName("RootWidget")
        self.setCentralWidget(root)

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.header = HeaderBar("AITJE", t("subtitle_local_ai_console"))
        self.header.home_requested.connect(self._go_home)
        self.header.shutdown_requested.connect(self._shutdown_app)
        self.header.restart_requested.connect(self._restart_app)
        self.sidebar = Sidebar()
        self.header.set_center_widget(self.sidebar)
        root_layout.addWidget(self.header)
        self._restart_on_close = False

        self.pages = {
            "chat": ChatPage(self.ws_client),
            "kb": KnowledgePage(),
            "net": NetworkStatusPage(),
            "devices": DevicesPage(),
            "settings": SettingsPage(),
        }
        self.pages["chat"].open_settings_tab_requested.connect(self._open_settings_tab)
        self.pages["net"].open_settings_tab_requested.connect(self._open_settings_tab)
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content = QWidget()
        self.content.setObjectName("ContentArea")

        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)

        self.page_intro = QWidget()
        self.page_intro.setObjectName("PageIntro")
        intro_layout = QVBoxLayout(self.page_intro)
        intro_layout.setContentsMargins(8, 0, 8, 0)
        intro_layout.setSpacing(2)

        self.page_title = QLabel()
        self.page_title.setObjectName("PageTitle")
        intro_layout.addWidget(self.page_title)

        self.page_subtitle = QLabel()
        self.page_subtitle.setObjectName("PageSubtitle")
        intro_layout.addWidget(self.page_subtitle)

        content_layout.addWidget(self.page_intro)

        for page in self.pages.values():
            content_layout.addWidget(page)
            page.setObjectName("Card")
            page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.content_scroll.setWidget(self.content)

        root_layout.addWidget(self.content_scroll, 1)

        self.sidebar.navigate.connect(self.show_page)
        self.sidebar.set_current("chat")
        self.show_page("chat")
        self.setMinimumWidth(max(1200, self.header.minimumSizeHint().width() + 32))

        self.setStyleSheet(AITJE_QSS)

        # Register for language changes
        register_language_change_callback(self._on_language_change)
        self.header.language_changed.connect(self._on_language_change)

    def _on_language_change(self, _lang: str = "") -> None:
        """Update all UI elements when language changes."""
        self._update_page_header()

    def show_page(self, key: str):
        for name, page in self.pages.items():
            page.setVisible(name == key)
        self._current_page_key = key
        current_page = self.pages.get(key)
        if current_page is not None and hasattr(current_page, "on_page_shown"):
            current_page.on_page_shown()
        self._update_page_header()

    def _update_page_header(self):
        """Update in-content title and subtitle for current page."""
        key = getattr(self, "_current_page_key", "chat")
        title_keys = {
            "chat": "page_title_chat",
            "kb": "page_title_kb",
            "net": "page_title_net",
            "devices": "page_title_devices",
            "settings": "page_title_settings",
        }
        subtitle_keys = {
            "chat": "page_subtitle_chat",
            "kb": "page_subtitle_kb",
            "net": "page_subtitle_net",
            "devices": "page_subtitle_devices",
            "settings": "page_subtitle_settings",
        }
        self.page_title.setText(t(title_keys.get(key, "page_title_chat")))
        self.page_subtitle.setText(t(subtitle_keys.get(key, "subtitle_local_ai_console")))

    def _go_home(self):
        self.sidebar.set_current("chat")
        self.show_page("chat")

    def _open_settings_tab(self, tab_key: str) -> None:
        self.sidebar.set_current("settings")
        self.show_page("settings")
        settings_page = self.pages["settings"]
        if hasattr(settings_page, "open_tab"):
            settings_page.open_tab(tab_key)

    def _shutdown_app(self) -> None:
        self._restart_on_close = False
        self.close()

    def _restart_app(self) -> None:
        self._restart_on_close = True
        self.close()

    def closeEvent(self, event):
        asyncio.create_task(self.ws_client.close())
        if self._restart_on_close:
            QProcess.startDetached(sys.executable, ["-m", "app.frontend.main"])
        event.accept()


def main():
    if sys.platform == "darwin":
        os.environ.setdefault("QT_FFMPEG_DECODING_HW_DEVICE_TYPES", "")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#ffffff"))
    palette.setColor(QPalette.WindowText, QColor("#111111"))
    palette.setColor(QPalette.Base, QColor("#ffffff"))
    palette.setColor(QPalette.AlternateBase, QColor("#f5f5f5"))
    palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipText, QColor("#111111"))
    palette.setColor(QPalette.Text, QColor("#111111"))
    palette.setColor(QPalette.Button, QColor("#ffffff"))
    palette.setColor(QPalette.ButtonText, QColor("#111111"))
    palette.setColor(QPalette.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.Highlight, QColor("#facc15"))
    palette.setColor(QPalette.HighlightedText, QColor("#111111"))
    palette.setColor(QPalette.Light, QColor("#ffffff"))
    palette.setColor(QPalette.Midlight, QColor("#f3f4f6"))
    palette.setColor(QPalette.Mid, QColor("#e5e7eb"))
    palette.setColor(QPalette.Dark, QColor("#d1d5db"))
    palette.setColor(QPalette.Shadow, QColor("#9ca3af"))
    app.setPalette(palette)

    app_dir = os.path.dirname(__file__)
    app_images_dir = os.path.join(app_dir, "images")
    app_icon_path = os.path.join(app_images_dir, "aitje-nav-logo.png")
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))

    boot_logo_path = os.path.join(app_dir, "assets", "aitje-home-animated-egg-boomerang-white.mp4")

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()

    def on_boot_finished():
        window.showFullScreen()

    boot_screen = BootScreen(
        logo_path=boot_logo_path,
        duration_ms=5000,
        on_finished=on_boot_finished,
    )
    boot_screen.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
