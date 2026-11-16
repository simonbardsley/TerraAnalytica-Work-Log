# -*- coding: utf-8 -*-
"""TerraAnalytica visual identity and light/dark theme helpers for Work Log."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from qgis.PyQt.QtCore import QByteArray, QEvent, QObject, QTimer, Qt
from qgis.PyQt.QtGui import QColor, QIcon, QPainter, QPalette, QPixmap
from qgis.PyQt.QtWidgets import QApplication

try:
    from qgis.PyQt.QtSvg import QSvgRenderer
except Exception:  # pragma: no cover - very old/minimal Qt builds
    QSvgRenderer = None

TA_GOLD = "#E8A838"
TA_CHARCOAL = "#202326"
TA_GOLD_SOFT = "#FDF6E3"
TA_GOLD_TINT = "#F8F1E0"


def _palette_role(name):
    if hasattr(QPalette, name):
        return getattr(QPalette, name)
    role_enum = getattr(QPalette, "ColorRole", None)
    if role_enum is not None and hasattr(role_enum, name):
        return getattr(role_enum, name)
    raise AttributeError(f"Cannot resolve QPalette role {name}")


_PALETTE_WINDOW = _palette_role("Window")
_PALETTE_BASE = _palette_role("Base")
_PALETTE_TEXT = _palette_role("Text")
_PALETTE_WINDOW_TEXT = _palette_role("WindowText")
_PALETTE_MID = _palette_role("Mid")

try:
    _PALETTE_CHANGE = QEvent.PaletteChange
    _APP_PALETTE_CHANGE = QEvent.ApplicationPaletteChange
except AttributeError:  # Qt6 scoped enum
    _PALETTE_CHANGE = QEvent.Type.PaletteChange
    _APP_PALETTE_CHANGE = QEvent.Type.ApplicationPaletteChange

try:
    _TRANSPARENT = Qt.transparent
except AttributeError:
    _TRANSPARENT = Qt.GlobalColor.transparent


def _blend(a: QColor, b: QColor, amount: float) -> QColor:
    amount = max(0.0, min(1.0, amount))
    return QColor(
        round(a.red() + (b.red() - a.red()) * amount),
        round(a.green() + (b.green() - a.green()) * amount),
        round(a.blue() + (b.blue() - a.blue()) * amount),
    )


def is_dark(widget=None) -> bool:
    pal = widget.palette() if widget is not None else QApplication.palette()
    c = pal.color(_PALETTE_WINDOW)
    lum = 0.2126 * c.red() + 0.7152 * c.green() + 0.0722 * c.blue()
    return lum < 128


def theme_colours(widget=None) -> dict:
    """Return palette-derived colours matching the TA Toolsearch family.

    TA Gold is the persistent brand accent. In light mode the primary ink is
    TA Charcoal. In dark mode linework/text follows the active QGIS palette so
    controls remain legible while retaining Gold as the visual identifier.
    """
    pal = widget.palette() if widget is not None else QApplication.palette()
    window = pal.color(_PALETTE_WINDOW)
    base = pal.color(_PALETTE_BASE)
    text = pal.color(_PALETTE_TEXT)
    window_text = pal.color(_PALETTE_WINDOW_TEXT)
    mid = pal.color(_PALETTE_MID)
    dark = is_dark(widget)

    primary = text if dark else QColor(TA_CHARCOAL)
    secondary = _blend(primary, window, 0.42 if dark else 0.48)
    border = _blend(primary, window, 0.72 if dark else 0.82)
    hover = _blend(window, primary, 0.08 if dark else 0.035)
    count_bg = _blend(window, primary, 0.12 if dark else 0.055)
    footer_bg = _blend(window, base, 0.45)
    gold_soft = _blend(window, QColor(TA_GOLD), 0.15 if dark else 0.10)
    gold_pressed = _blend(window, QColor(TA_GOLD), 0.23 if dark else 0.16)

    return {
        "window": window.name(),
        "base": base.name(),
        "text": primary.name(),
        "window_text": window_text.name(),
        "muted": secondary.name(),
        "mid": mid.name(),
        "border": border.name(),
        "hover": hover.name(),
        "count_bg": count_bg.name(),
        "footer_bg": footer_bg.name(),
        "gold_soft": gold_soft.name(),
        "gold_pressed": gold_pressed.name(),
        "dark": dark,
    }


def icon(name: str, size: int = 24, widget=None, ink_override: Optional[str] = None) -> QIcon:
    """Return a TA icon that keeps Gold and adapts Charcoal linework in dark mode."""
    base = Path(__file__).resolve().parent / "icons"
    svg_path = base / f"{name}.svg"
    if not svg_path.exists():
        png_path = base / f"{name}.png"
        return QIcon(str(png_path)) if png_path.exists() else QIcon()

    if QSvgRenderer is None:
        return QIcon(str(svg_path))

    try:
        svg = svg_path.read_text(encoding="utf-8")
        colours = theme_colours(widget)
        # Bring legacy bundled SVGs onto the Layer Lab Gold used by the UI.
        svg = svg.replace("#E3B54C", TA_GOLD).replace("#e3b54c", TA_GOLD)
        # Replace TA Charcoal linework with active text only in dark mode.
        ink = ink_override or (colours["text"] if colours["dark"] else TA_CHARCOAL)
        svg = svg.replace(TA_CHARCOAL, ink).replace(TA_CHARCOAL.lower(), ink)
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        px = QPixmap(size, size)
        px.fill(_TRANSPARENT)
        painter = QPainter(px)
        renderer.render(painter)
        painter.end()
        return QIcon(px)
    except Exception:
        return QIcon(str(svg_path))


def theme_stylesheet(widget=None) -> str:
    c = theme_colours(widget)
    return f"""
        QWidget#TAWorkLogRoot {{ background: {c['window']}; color: {c['text']}; }}
        QDialog {{ background: {c['window']}; color: {c['text']}; }}
        QLabel {{ color: {c['text']}; }}
        QLineEdit, QComboBox, QDateEdit, QDateTimeEdit, QSpinBox,
        QTextEdit, QPlainTextEdit, QListWidget, QTreeWidget, QTableWidget, QTextBrowser {{
            color: {c['text']};
            background: {c['base']};
            border: 1px solid {c['border']};
            border-radius: 3px;
            selection-background-color: {TA_GOLD};
            selection-color: {TA_CHARCOAL};
        }}
        QLineEdit, QComboBox, QDateEdit, QDateTimeEdit, QSpinBox {{
            padding: 4px 7px;
            min-height: 20px;
        }}
        QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDateTimeEdit:focus,
        QSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus,
        QListWidget:focus, QTreeWidget:focus, QTableWidget:focus {{
            border-color: {TA_GOLD};
        }}
        QToolButton {{
            color: {c['text']};
            background: {c['base']};
            border: 1px solid {c['border']};
            border-radius: 3px;
            padding: 3px;
            min-width: 22px;
            min-height: 22px;
            font-weight: 650;
        }}
        QToolButton:hover {{ border-color: {TA_GOLD}; background: {c['gold_soft']}; }}
        QToolButton:pressed {{ background: {c['gold_pressed']}; }}
        QPushButton {{
            color: {c['text']};
            background: {c['base']};
            border: 1px solid {c['border']};
            border-radius: 3px;
            padding: 5px 10px;
        }}
        QPushButton:hover {{ border-color: {TA_GOLD}; background: {c['gold_soft']}; }}
        QPushButton:pressed {{ background: {c['gold_pressed']}; }}
        QHeaderView::section {{
            color: {c['text']};
            background: {c['footer_bg']};
            border: none;
            border-right: 1px solid {c['border']};
            border-bottom: 1px solid {c['border']};
            padding: 4px 6px;
            font-weight: 650;
        }}
        QTabWidget::pane {{ border: 1px solid {c['border']}; background: {c['window']}; }}
        QTabBar::tab {{
            background: transparent;
            color: {c['muted']};
            padding: 7px 12px;
            border: none;
            border-bottom: 2px solid transparent;
        }}
        QTabBar::tab:selected {{ color: {c['text']}; border-bottom: 2px solid {TA_GOLD}; }}
        QTabBar::tab:hover {{ color: {c['text']}; }}
        QGroupBox {{
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: 3px;
            margin-top: 9px;
            padding-top: 6px;
            font-weight: 600;
        }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 9px; padding: 0 4px; }}
        QFrame {{ color: {c['text']}; }}
    """


def apply_theme(widget) -> None:
    stylesheet = theme_stylesheet(widget)
    if widget.styleSheet() != stylesheet:
        widget.setStyleSheet(stylesheet)


class _ThemeWatcher(QObject):
    def __init__(self, widget, callback: Optional[Callable] = None, apply_styles: bool = True):
        super().__init__(widget)
        self.widget = widget
        self.callback = callback
        self.apply_styles = apply_styles
        self._queued = False
        self._palette = QApplication.palette()

    def eventFilter(self, obj, event):  # noqa: N802 - Qt API
        if event.type() in (_PALETTE_CHANGE, _APP_PALETTE_CHANGE):
            # Applying a stylesheet can emit widget palette changes of its own.
            if not self._queued and QApplication.palette() != self._palette:
                self._queued = True
                QTimer.singleShot(0, self.refresh)
        return False

    def refresh(self):
        self._queued = False
        palette = QApplication.palette()
        if palette == self._palette:
            return
        self._palette = palette
        if self.apply_styles:
            apply_theme(self.widget)
        if self.callback:
            self.callback()


def install_theme(widget, callback: Optional[Callable] = None) -> None:
    """Apply TA/QGIS palette styling and refresh it if the palette changes."""
    apply_theme(widget)
    watcher = _ThemeWatcher(widget, callback=callback, apply_styles=True)
    widget.installEventFilter(watcher)
    widget._ta_theme_watcher = watcher
    if callback:
        callback()


def watch_theme(widget, callback: Callable) -> None:
    """Watch palette changes without changing the target widget's stylesheet."""
    watcher = _ThemeWatcher(widget, callback=callback, apply_styles=False)
    widget.installEventFilter(watcher)
    widget._ta_theme_action_watcher = watcher


def brand_label_style() -> str:
    return f"color: {TA_GOLD}; font-size: 10pt; font-weight: bold; padding: 2px 0;"


def title_style(widget=None, size: int = 17) -> str:
    c = theme_colours(widget)
    return f"color: {c['text']}; font-size: {size}px; font-weight: 700;"


def muted_style(widget=None, size: int = 11) -> str:
    c = theme_colours(widget)
    return f"color: {c['muted']}; font-size: {size}px;"
