# -*- coding: utf-8 -*-
"""Reporting dialog for TerraAnalytica Work Log."""

from __future__ import annotations

import csv
import html
import logging
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

from qgis.PyQt.QtCore import Qt, QDate, QRectF, QUrl, QMarginsF
from qgis.PyQt.QtGui import QColor, QPainter, QPen, QFontMetrics, QPalette, QTextDocument, QFont, QPageSize, QPageLayout, QImage
from qgis.PyQt.QtPrintSupport import QPrinter, QPrintDialog
from qgis.core import QgsSettings

from .branding import (
    TA_GOLD, TA_CHARCOAL, brand_label_style, icon as ta_icon, install_theme,
    muted_style, theme_colours, title_style,
)
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


LOGGER = logging.getLogger(__name__)


class HorizontalBarChart(QWidget):
    """Dependency-free horizontal bar chart drawn with Qt."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.title = title
        self._data: List[Tuple[str, float]] = []
        self.setMinimumHeight(190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, data: Iterable[Tuple[str, float]], title: Optional[str] = None) -> None:
        self._data = [(str(k), float(v or 0.0)) for k, v in data]
        if title is not None:
            self.title = title
        self.update()

    def _draw_chart(self, painter: QPainter, rect, *, print_mode: bool = False) -> None:
        """Draw the chart into an arbitrary rectangle.

        ``print_mode`` uses fixed, print-friendly colours and a compact row height so
        report images are independent of the on-screen widget size. This prevents
        longer charts being clipped when the Reports dialog happens to be short.
        """
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if print_mode:
            text_color = QColor(TA_CHARCOAL)
            muted = QColor(120, 120, 120)
            accent = QColor(TA_GOLD)
            base_font = QFont(painter.font())
            base_font.setPointSizeF(7.7)
            painter.setFont(base_font)
        else:
            palette = self.palette()
            text_color = palette.color(QPalette.ColorRole.Text)
            muted = palette.color(QPalette.ColorRole.Mid)
            accent = QColor(TA_GOLD)

        painter.setPen(text_color)
        title_font = QFont(painter.font())
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(10, 20, self.title)

        if not self._data:
            title_font.setBold(False)
            painter.setFont(title_font)
            painter.setPen(muted)
            painter.drawText(10, 48, "No logged time for the selected filters.")
            return

        data = self._data[:14]
        max_value = max((v for _, v in data), default=0.0)
        if max_value <= 0:
            max_value = 1.0

        normal_font = QFont(painter.font())
        normal_font.setBold(False)
        painter.setFont(normal_font)
        fm = QFontMetrics(painter.font())
        label_cap = 156 if print_mode else 190
        label_floor = 82 if print_mode else 90
        label_width = min(label_cap, max(label_floor, max(fm.horizontalAdvance(k) for k, _ in data) + 10))
        value_width = 52 if print_mode else 72
        top = 32 if print_mode else 34
        bottom = 8 if print_mode else 10
        minimum_row = 14 if print_mode else 19
        row_h = max(minimum_row, int((rect.height() - top - bottom) / max(1, len(data))))
        bar_x = 10 + label_width
        bar_w = max(20, rect.width() - bar_x - value_width - 16)

        for i, (label, value) in enumerate(data):
            y = top + i * row_h
            label_elided = fm.elidedText(label, Qt.TextElideMode.ElideRight, label_width - 8)
            painter.setPen(text_color)
            painter.drawText(QRectF(10, y, label_width - 8, row_h),
                             int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                             label_elided)

            inset = 3 if print_mode else 4
            min_bar_h = 6 if print_mode else 7
            bar_rect = QRectF(bar_x, y + inset, bar_w * (value / max_value), max(min_bar_h, row_h - inset * 2))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(accent)
            painter.drawRoundedRect(bar_rect, 2, 2)

            painter.setPen(text_color)
            painter.drawText(QRectF(bar_x + bar_w + 5, y, value_width, row_h),
                             int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
                             f"{value:.1f} h")

    def report_image(self, width: int = 360, height: int = 246) -> QImage:
        """Render a stable print image that always contains every displayed row."""
        format_container = getattr(QImage, "Format", QImage)
        image_format = getattr(format_container, "Format_ARGB32", None)
        if image_format is None:
            image_format = getattr(QImage, "Format_ARGB32")
        image = QImage(width, height, image_format)
        image.fill(QColor(255, 255, 255))
        painter = QPainter(image)
        self._draw_chart(painter, QRectF(0, 0, width, height), print_mode=True)
        painter.end()
        return image

    def paintEvent(self, event):  # noqa: N802 - Qt API name
        painter = QPainter(self)
        self._draw_chart(painter, self.rect(), print_mode=False)
        painter.end()


class ReportsDialog(QDialog):
    """Project/time reporting for GIS and remote-sensing work logs."""

    def __init__(self, parent, db, current_project_id=None, current_project_name=None):
        super().__init__(parent)
        self.db = db
        self.current_project_id = current_project_id
        self.current_project_name = current_project_name
        self._current_rows = []
        self._summary_cache = {}
        self._summary_caps = []
        self.setWindowTitle(self.tr("TA Work Log — Reports"))
        self.resize(900, 720)
        self.setMinimumSize(720, 560)
        self._build_ui()
        install_theme(self, self._refresh_theme_assets)
        self._load_filters()
        self.refresh()

    def tr(self, text: str) -> str:
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate("ReportsDialog", text)

    def _info_button(self, title: str, message: str, *, help_button: bool = False) -> QToolButton:
        btn = QToolButton()
        if help_button:
            btn.setText("?")
            btn.setToolTip(self.tr("Help: {}" ).format(title))
            btn.setAccessibleName(self.tr("Help: {}" ).format(title))
        else:
            btn.setText("ⓘ")
            btn.setToolTip(message)
            btn.setAccessibleName(self.tr("Information: {}" ).format(title))
        btn.setAutoRaise(True)
        btn.clicked.connect(lambda: QMessageBox.information(self, title, message))
        return btn

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        header.setSpacing(8)
        brand_box = QWidget()
        brand_layout = QVBoxLayout(brand_box)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(0)
        self.brand_label = QLabel("TERRAANALYTICA")
        self.brand_label.setStyleSheet(brand_label_style())
        brand_layout.addWidget(self.brand_label)
        self.title_label = QLabel(self.tr("Work Log Reports"))
        brand_layout.addWidget(self.title_label)
        header.addWidget(brand_box)
        header.addWidget(self._info_button(
            self.tr("Reporting help"),
            self.tr(
                "Reports summarise logged duration for TerraAnalytica GIS and remote-sensing work. "
                "Work classes are the entry categories. Tags are more specific descriptors such as "
                "Sentinel-2, SAR, LiDAR, QGIS, fieldwork, NDVI or machine-learning methods. "
                "An entry can have several tags, so totals by tag can overlap."
            ),
            help_button=True,
        ))
        header.addStretch()
        layout.addLayout(header)

        filter_frame = QFrame()
        filter_frame.setFrameShape(QFrame.Shape.StyledPanel)
        grid = QGridLayout(filter_frame)

        grid.addWidget(QLabel(self.tr("Project:")), 0, 0)
        self.cmb_project = QComboBox()
        grid.addWidget(self.cmb_project, 0, 1)

        grid.addWidget(QLabel(self.tr("Work class:")), 0, 2)
        self.cmb_category = QComboBox()
        grid.addWidget(self.cmb_category, 0, 3)

        grid.addWidget(QLabel(self.tr("User / analyst:")), 1, 0)
        self.cmb_user = QComboBox()
        grid.addWidget(self.cmb_user, 1, 1)

        grid.addWidget(QLabel(self.tr("Tag:")), 1, 2)
        self.cmb_tag = QComboBox()
        grid.addWidget(self.cmb_tag, 1, 3)

        grid.addWidget(QLabel(self.tr("Timeline:")), 2, 0)
        self.cmb_group = QComboBox()
        self.cmb_group.addItem(self.tr("Day"), "day")
        self.cmb_group.addItem(self.tr("Week"), "week")
        self.cmb_group.addItem(self.tr("Month"), "month")
        grid.addWidget(self.cmb_group, 2, 1)

        grid.addWidget(QLabel(self.tr("From:")), 2, 2)
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(QDate.currentDate().addMonths(-3))
        grid.addWidget(self.date_from, 2, 3)

        grid.addWidget(QLabel(self.tr("To:")), 3, 0)
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setDate(QDate.currentDate())
        grid.addWidget(self.date_to, 3, 1)
        self.btn_refresh = QToolButton(); self.btn_refresh.setIcon(ta_icon("refresh")); self.btn_refresh.setAutoRaise(True)
        self.btn_refresh.setToolTip(self.tr("Refresh report using the current filters")); self.btn_refresh.setAccessibleName(self.tr("Refresh report"))
        grid.addWidget(self.btn_refresh, 3, 3)

        layout.addWidget(filter_frame)

        # Summary cards
        summary = QHBoxLayout()
        self.lbl_total_hours = self._summary_card(self.tr("TOTAL HOURS"))
        self.lbl_entries = self._summary_card(self.tr("ENTRIES"))
        self.lbl_active_days = self._summary_card(self.tr("ACTIVE DAYS"))
        self.lbl_avg_day = self._summary_card(self.tr("AVG HRS / ACTIVE DAY"))
        summary.addWidget(self.lbl_total_hours._summary_frame)
        summary.addWidget(self.lbl_entries._summary_frame)
        summary.addWidget(self.lbl_active_days._summary_frame)
        summary.addWidget(self.lbl_avg_day._summary_frame)
        layout.addLayout(summary)

        charts = QHBoxLayout()
        self.chart_class = HorizontalBarChart(self.tr("Hours by work class"))
        self.chart_time = HorizontalBarChart(self.tr("Hours over time"))
        charts.addWidget(self.chart_class, 1)
        charts.addWidget(self.chart_time, 1)
        layout.addLayout(charts, 1)

        self.chart_project = HorizontalBarChart(self.tr("Hours by project"))
        self.chart_project.setMinimumHeight(150)
        layout.addWidget(self.chart_project, 1)

        tag_row = QHBoxLayout()
        self.lbl_tag_summary = QLabel("")
        self.lbl_tag_summary.setWordWrap(True)
        self.lbl_tag_summary.setStyleSheet(muted_style(self, 11))
        tag_row.addWidget(self.lbl_tag_summary, 1)
        tag_row.addWidget(self._info_button(
            self.tr("Tag totals"),
            self.tr(
                "Tag hours are attribution totals. If one two-hour entry has both Sentinel-2 and NDVI tags, "
                "the same two hours appear under each tag. Therefore tag totals should not be added together."
            ),
        ))
        layout.addLayout(tag_row)

        export_row = QHBoxLayout()
        self.btn_csv = QToolButton(); self.btn_csv.setIcon(ta_icon("csv")); self.btn_csv.setAutoRaise(True)
        self.btn_pdf = QToolButton(); self.btn_pdf.setIcon(ta_icon("pdf")); self.btn_pdf.setAutoRaise(True)
        self.btn_print = QToolButton(); self.btn_print.setIcon(ta_icon("print")); self.btn_print.setAutoRaise(True)
        self.btn_csv.setToolTip(self.tr("Export the currently filtered work-log records to CSV"))
        self.btn_pdf.setToolTip(self.tr("Create a compact PDF report with the current filters, totals and charts"))
        self.btn_print.setToolTip(self.tr("Print the current filtered report"))
        self.btn_csv.setAccessibleName(self.tr("Export CSV")); self.btn_pdf.setAccessibleName(self.tr("Export PDF")); self.btn_print.setAccessibleName(self.tr("Print report"))
        export_row.addWidget(self.btn_csv)
        export_row.addWidget(self.btn_pdf)
        export_row.addWidget(self.btn_print)
        export_row.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        export_row.addWidget(buttons)
        layout.addLayout(export_row)

        self.btn_csv.clicked.connect(self._export_csv)
        self.btn_pdf.clicked.connect(self._export_pdf)
        self.btn_print.clicked.connect(self._print_report)
        self.btn_refresh.clicked.connect(self.refresh)
        self.cmb_project.currentIndexChanged.connect(self._project_changed)
        self.cmb_category.currentIndexChanged.connect(self.refresh)
        self.cmb_user.currentIndexChanged.connect(self.refresh)
        self.cmb_tag.currentIndexChanged.connect(self.refresh)
        self.cmb_group.currentIndexChanged.connect(self.refresh)
        self.date_from.dateChanged.connect(self.refresh)
        self.date_to.dateChanged.connect(self.refresh)

    def _refresh_theme_assets(self) -> None:
        self.brand_label.setStyleSheet(brand_label_style())
        self.title_label.setStyleSheet(title_style(self, 17))
        self.btn_refresh.setIcon(ta_icon("refresh", 18, self))
        self.btn_csv.setIcon(ta_icon("csv", 18, self))
        self.btn_pdf.setIcon(ta_icon("pdf", 18, self))
        self.btn_print.setIcon(ta_icon("print", 18, self))
        self.lbl_tag_summary.setStyleSheet(muted_style(self, 11))
        for cap in self._summary_caps:
            cap.setStyleSheet(muted_style(self, 10))

    def _summary_card(self, caption: str) -> QLabel:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(10, 7, 10, 7)
        cap = QLabel(caption)
        cap.setStyleSheet(muted_style(self, 10))
        self._summary_caps.append(cap)
        val = QLabel("0")
        f = val.font()
        f.setBold(True)
        f.setPointSize(f.pointSize() + 5)
        val.setFont(f)
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(cap)
        lay.addWidget(val)
        val._summary_frame = frame  # keep a stable owner reference
        return val

    def _load_filters(self) -> None:
        self.cmb_project.blockSignals(True)
        self.cmb_project.clear()
        self.cmb_project.addItem(self.tr("All projects"), None)
        current_index = 0
        for i, p in enumerate(self.db.list_projects(), start=1):
            self.cmb_project.addItem(p["name"], p["id"])
            if p["id"] == self.current_project_id:
                current_index = i
        self.cmb_project.setCurrentIndex(current_index)
        self.cmb_project.blockSignals(False)

        self.cmb_category.blockSignals(True)
        self.cmb_category.clear()
        self.cmb_category.addItem(self.tr("(all work classes)"), None)
        for cat in self.db.list_categories():
            self.cmb_category.addItem(cat, cat)
        self.cmb_category.blockSignals(False)
        self._reload_users()
        self._reload_tags()

    def _reload_users(self) -> None:
        selected = self.cmb_user.currentData() if self.cmb_user.count() else None
        project_id = self.cmb_project.currentData()
        self.cmb_user.blockSignals(True)
        self.cmb_user.clear()
        self.cmb_user.addItem(self.tr("(all users)"), None)
        restore = 0
        for i, user in enumerate(self.db.list_users(project_id=project_id), start=1):
            self.cmb_user.addItem(user, user)
            if user == selected:
                restore = i
        self.cmb_user.setCurrentIndex(restore)
        self.cmb_user.blockSignals(False)

    def _reload_tags(self) -> None:
        selected = self.cmb_tag.currentData() if self.cmb_tag.count() else None
        project_id = self.cmb_project.currentData()
        self.cmb_tag.blockSignals(True)
        self.cmb_tag.clear()
        self.cmb_tag.addItem(self.tr("(all tags)"), None)
        tags = self.db.list_tags(project_id=project_id)
        restore = 0
        for i, tag in enumerate(tags, start=1):
            self.cmb_tag.addItem(tag, tag)
            if tag == selected:
                restore = i
        self.cmb_tag.setCurrentIndex(restore)
        self.cmb_tag.blockSignals(False)

    def _project_changed(self) -> None:
        self._reload_users()
        self._reload_tags()
        self.refresh()

    def refresh(self) -> None:
        if not self.db:
            return
        project_id = self.cmb_project.currentData()
        category = self.cmb_category.currentData()
        user_name = self.cmb_user.currentData()
        tag = self.cmb_tag.currentData()
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")

        rows = self.db.report_entries(
            project_id=project_id,
            category=category,
            tag=tag,
            user_name=user_name,
            date_from=date_from,
            date_to=date_to,
        )
        self._current_rows = rows

        total_minutes = sum(int(r.get("duration_minutes") or 0) for r in rows)
        total_hours = total_minutes / 60.0
        active_days = {str(r.get("timestamp") or "")[:10] for r in rows if r.get("timestamp")}
        self.lbl_total_hours.setText(f"{total_hours:.1f}")
        self.lbl_entries.setText(str(len(rows)))
        self.lbl_active_days.setText(str(len(active_days)))
        self.lbl_avg_day.setText(f"{(total_hours / len(active_days)) if active_days else 0.0:.1f}")

        by_class: Dict[str, float] = defaultdict(float)
        by_time: Dict[str, float] = defaultdict(float)
        by_project: Dict[str, float] = defaultdict(float)
        by_user: Dict[str, float] = defaultdict(float)
        by_tag: Dict[str, float] = defaultdict(float)
        grouping = self.cmb_group.currentData() or "day"

        for r in rows:
            hours = float(r.get("duration_minutes") or 0) / 60.0
            by_class[r.get("category") or self.tr("Unclassified")] += hours
            by_project[r.get("project_name") or self.tr("Unknown project")] += hours
            by_user[r.get("user_name") or self.tr("Unassigned")] += hours
            key = self._time_key(r.get("timestamp"), grouping)
            if key:
                by_time[key] += hours
            for t in self._split_tags(r.get("tags") or ""):
                by_tag[t] += hours

        class_data = sorted(by_class.items(), key=lambda kv: (-kv[1], kv[0].lower()))
        time_data = sorted(by_time.items(), key=lambda kv: kv[0])
        project_data = sorted(by_project.items(), key=lambda kv: (-kv[1], kv[0].lower()))
        user_data = sorted(by_user.items(), key=lambda kv: (-kv[1], kv[0].lower()))
        self.chart_class.set_data(class_data, self.tr("Hours by work class"))
        self.chart_time.set_data(time_data[-14:], self.tr("Hours by {}" ).format(grouping))
        self.chart_project.set_data(project_data, self.tr("Hours by project"))

        top_tags = sorted(by_tag.items(), key=lambda kv: (-kv[1], kv[0].lower()))[:8]
        if top_tags:
            text = self.tr("Top tags (overlapping attribution): ") + "; ".join(
                f"{name} {hours:.1f} h" for name, hours in top_tags
            )
        else:
            text = self.tr("No tags recorded for the selected entries yet.")
        self.lbl_tag_summary.setText(text)
        self._summary_cache = {
            "total_hours": total_hours,
            "entries": len(rows),
            "active_days": len(active_days),
            "avg_day": (total_hours / len(active_days)) if active_days else 0.0,
            "by_class": class_data,
            "by_time": time_data,
            "by_project": project_data,
            "by_user": user_data,
            "by_tag": sorted(by_tag.items(), key=lambda kv: (-kv[1], kv[0].lower())),
            "grouping": grouping,
            "date_from": date_from,
            "date_to": date_to,
        }

    @staticmethod
    def _printer_pdf_format():
        container = getattr(QPrinter, "OutputFormat", QPrinter)
        return getattr(container, "PdfFormat")

    @staticmethod
    def _document_print(document: QTextDocument, printer: QPrinter) -> None:
        if hasattr(document, "print_"):
            document.print_(printer)
        else:
            document.print(printer)

    @staticmethod
    def _iso_timestamp(value: Optional[str]) -> str:
        """Return a consistent ISO-8601 local timestamp for exports."""
        raw = str(value or "").strip()
        if not raw:
            return ""
        candidates = (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d",
        )
        for fmt in candidates:
            try:
                dt = datetime.strptime(raw[:19] if "%S" in fmt else raw[:16] if "%M" in fmt else raw[:10], fmt)
                if fmt == "%Y-%m-%d":
                    return dt.strftime("%Y-%m-%dT00:00:00")
                return dt.strftime("%Y-%m-%dT%H:%M:%S")
            except ValueError:
                continue
        # Preserve unknown values rather than silently discarding provenance.
        return raw.replace(" ", "T", 1)

    def _export_csv(self) -> None:
        project = self.cmb_project.currentText().replace("All projects", "all_projects")
        default = "work_log_{}_{}_to_{}.csv".format(
            project.replace(" ", "_"), self.date_from.date().toString("yyyy-MM-dd"),
            self.date_to.date().toString("yyyy-MM-dd")
        )
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Export Work Log CSV"), default, self.tr("CSV files (*.csv)"))
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            fields = [
                "id", "timestamp", "project_name", "user_name", "category", "duration_minutes", "hours",
                "title", "description", "tags", "workflow_name", "workflow_version"
            ]
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                for r in self._current_rows:
                    writer.writerow({
                        "id": r.get("id"), "timestamp": self._iso_timestamp(r.get("timestamp")),
                        "project_name": r.get("project_name"), "user_name": r.get("user_name") or "", "category": r.get("category"),
                        "duration_minutes": r.get("duration_minutes") or 0,
                        "hours": round(float(r.get("duration_minutes") or 0) / 60.0, 3),
                        "title": r.get("title") or "", "description": r.get("description") or "",
                        "tags": r.get("tags") or "", "workflow_name": r.get("workflow_name") or "",
                        "workflow_version": r.get("workflow_version") or "",
                    })
            QMessageBox.information(self, self.tr("CSV Export"), self.tr("Exported {} records to:\n{}" ).format(len(self._current_rows), path))
        except Exception as exc:
            QMessageBox.warning(self, self.tr("CSV Export"), self.tr("Could not export CSV:\n{}" ).format(exc))

    @staticmethod
    def _rows_html(data, left_title, right_title="Hours", limit: int = 12, decimals: int = 1, include_total: bool = False) -> str:
        rows = list(data)[:limit]
        if not rows:
            return "<tr><td colspan='2' class='muted'>No data</td></tr>"
        fmt = "{:." + str(int(decimals)) + "f}"
        body = "".join(
            "<tr><td>{}</td><td class='num'>{}</td></tr>".format(
                html.escape(str(k)), fmt.format(float(v or 0.0))
            ) for k, v in rows
        )
        if include_total:
            total = sum(float(v or 0.0) for _, v in rows)
            body += "<tr class='total'><td><b>Total</b></td><td class='num'><b>{}</b></td></tr>".format(fmt.format(total))
        return body

    @staticmethod
    def _report_heading(kind: str) -> str:
        custom = QgsSettings().value("worklog/report_heading", "", type=str).strip()
        return f"{custom} - {kind}" if custom else kind

    @staticmethod
    def _safe_stem(value: str, fallback: str) -> str:
        clean = re.sub(r"[^A-Za-z0-9._-]+", "_", (value or "").strip()).strip("_.-")
        return clean.lower() or fallback

    @staticmethod
    def _configure_printer(printer: QPrinter, landscape: bool = False) -> None:
        """Use an explicit A4 layout so PDF export and Print start from the same geometry."""
        try:
            size_ids = getattr(QPageSize, "PageSizeId", QPageSize)
            printer.setPageSize(QPageSize(getattr(size_ids, "A4")))
            orientations = getattr(QPageLayout, "Orientation", QPageLayout)
            orientation = getattr(orientations, "Landscape" if landscape else "Portrait")
            printer.setPageOrientation(orientation)
            units = getattr(QPageLayout, "Unit", QPageLayout)
            printer.setPageMargins(QMarginsF(10, 10, 10, 10), getattr(units, "Millimeter"))
        except Exception:
            # Older Qt/QGIS builds may expose a reduced printer API. Printing still works.
            LOGGER.debug("QPrinter page layout API is unavailable", exc_info=True)

    def _report_document(self) -> QTextDocument:
        cache = self._summary_cache or {}
        doc = QTextDocument()
        doc.setDocumentMargin(4)
        font = QFont()
        font.setPointSizeF(8.2)
        doc.setDefaultFont(font)

        # Render charts to dedicated print images rather than grabbing their current
        # on-screen widget geometry. The Reports dialog can be shorter than a 14-row
        # chart, and a screen grab would therefore clip the lower rows in PDF/Print.
        for name, widget in [("class_chart.png", self.chart_class), ("time_chart.png", self.chart_time)]:
            try:
                doc.addResource(
                    getattr(getattr(QTextDocument, "ResourceType", QTextDocument), "ImageResource"),
                    QUrl(name), widget.report_image(360, 246)
                )
            except Exception:
                LOGGER.debug("Could not render report chart image: %s", name, exc_info=True)

        project = self.cmb_project.currentText()
        work_class = self.cmb_category.currentText()
        user = self.cmb_user.currentText()
        tag = self.cmb_tag.currentText()
        heading = self._report_heading("Work Log Report")
        entries = self._current_rows[:160]
        single_project = self.cmb_project.currentData() is not None

        def esc(v):
            return html.escape(str(v or ""))

        if single_project:
            entry_header = "<tr><th width='16%'>Date/time</th><th width='13%'>User</th><th width='21%'>Work class</th><th width='8%'>Hours</th><th width='42%'>Activity</th></tr>"
            entry_rows = "".join(
                "<tr><td>{}</td><td>{}</td><td>{}</td><td class='num'>{:.2f}</td><td>{}</td></tr>".format(
                    esc((r.get("timestamp") or "")[:16].replace("T", " ")),
                    esc(r.get("user_name") or "-"), esc(r.get("category") or ""),
                    float(r.get("duration_minutes") or 0) / 60.0,
                    esc(r.get("title") or r.get("description") or "")[:180],
                ) for r in entries
            )
        else:
            entry_header = "<tr><th width='14%'>Date/time</th><th width='20%'>Project</th><th width='11%'>User</th><th width='18%'>Work class</th><th width='7%'>Hours</th><th width='30%'>Activity</th></tr>"
            entry_rows = "".join(
                "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td class='num'>{:.2f}</td><td>{}</td></tr>".format(
                    esc((r.get("timestamp") or "")[:16].replace("T", " ")), esc(r.get("project_name") or ""),
                    esc(r.get("user_name") or "-"), esc(r.get("category") or ""),
                    float(r.get("duration_minutes") or 0) / 60.0,
                    esc(r.get("title") or r.get("description") or "")[:160],
                ) for r in entries
            )
        if not entry_rows:
            entry_rows = "<tr><td colspan='6' class='muted'>No matching records</td></tr>"

        project_breakdown = self._rows_html(cache.get("by_project", []), "Project", limit=10)
        user_breakdown = self._rows_html(cache.get("by_user", []), "User", limit=10, decimals=2, include_total=True)
        tag_breakdown = self._rows_html(cache.get("by_tag", []), "Tag", limit=8)
        project_section = "" if single_project else f"<td><h3>By project</h3><table class='mini'><tr><th>Project</th><th>Hours</th></tr>{project_breakdown}</table></td>"

        style = """
        body{font-family:Arial,Helvetica,sans-serif;font-size:8.2pt;color:#222;}
        h1{font-size:15pt;margin:0 0 5px 0;font-weight:600;}
        h2{font-size:10.5pt;margin:10px 0 4px 0;font-weight:600;}
        h3{font-size:9pt;margin:3px 0 3px 0;font-weight:600;}
        p{margin:2px 0 5px 0;} .meta{font-size:8.3pt;color:#333;} .muted{color:#666;}
        table{border-collapse:collapse;width:100%;} th,td{border:0.6px solid #aaa;padding:2px 3px;vertical-align:top;}
        th{font-size:7.5pt;font-weight:600;background:#f0f0f0;} td{font-size:7.5pt;}
        .cards td{text-align:center;padding:4px 3px;font-size:11pt;font-weight:600;} .cards small{font-size:6.8pt;font-weight:normal;color:#555;}
        .layout td{border:none;padding:3px 5px;vertical-align:top;} .mini th,.mini td{font-size:7pt;padding:1.5px 2px;}
        .num{text-align:right;white-space:nowrap;} .total td{border-top:1px solid #777;} .entries tr{page-break-inside:avoid;}
        .pagebreak{page-break-before:always;}
        """
        body = f"""<html><head><style>{style}</style></head><body>
        <h1>{esc(heading)}</h1>
        <p class='meta'><b>Period:</b> {esc(cache.get('date_from',''))} to {esc(cache.get('date_to',''))} &nbsp;&nbsp;
        <b>Project:</b> {esc(project)} &nbsp;&nbsp; <b>User:</b> {esc(user)}<br>
        <b>Work class:</b> {esc(work_class)} &nbsp;&nbsp; <b>Tag:</b> {esc(tag)} &nbsp;&nbsp; <b>Timeline:</b> {esc(cache.get('grouping','day')).title()}</p>
        <table class='cards'><tr>
          <td>{cache.get('total_hours',0):.1f} h<br><small>Total hours</small></td>
          <td>{cache.get('entries',0)}<br><small>Entries</small></td>
          <td>{cache.get('active_days',0)}<br><small>Active days</small></td>
          <td>{cache.get('avg_day',0):.1f} h<br><small>Avg / active day</small></td>
        </tr></table>
        <table class='layout'><tr>
          <td width='50%'><h2>Hours by work class</h2><img src='class_chart.png' width='330' height='226'></td>
          <td width='50%'><h2>Hours over time</h2><img src='time_chart.png' width='330' height='226'></td>
        </tr></table>
        <table class='layout'><tr>
          {project_section}
          <td><h3>By user</h3><table class='mini'><tr><th>User</th><th>Hours</th></tr>{user_breakdown}</table></td>
          <td><h3>Top tags</h3><table class='mini'><tr><th>Tag</th><th>Hours</th></tr>{tag_breakdown}</table></td>
        </tr></table>
        <p class='muted'><i>Tag hours are overlapping attribution totals; one entry may contribute to several tags.</i></p>
        <div class='pagebreak'></div>
        <h2>Matching work-log entries</h2>
        <table class='entries'>{entry_header}{entry_rows}</table>
        <p class='muted'>{'Showing first 160 matching entries in this report.' if len(self._current_rows) > 160 else ''}</p>
        </body></html>"""
        doc.setHtml(body)
        return doc

    def _export_pdf(self) -> None:
        prefix = self._safe_stem(QgsSettings().value("worklog/report_heading", "", type=str), "work_log")
        default = f"{prefix}_report_{self.date_from.date().toString('yyyy-MM-dd')}_to_{self.date_to.date().toString('yyyy-MM-dd')}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Export Work Log PDF"), default, self.tr("PDF files (*.pdf)"))
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            printer = QPrinter()
            printer.setOutputFormat(self._printer_pdf_format())
            printer.setOutputFileName(path)
            self._configure_printer(printer, landscape=True)
            self._document_print(self._report_document(), printer)
            QMessageBox.information(self, self.tr("PDF Export"), self.tr("Report exported to:\n{}" ).format(path))
        except Exception as exc:
            QMessageBox.warning(self, self.tr("PDF Export"), self.tr("Could not create PDF:\n{}" ).format(exc))

    def _print_report(self) -> None:
        try:
            printer = QPrinter()
            self._configure_printer(printer, landscape=True)
            dlg = QPrintDialog(printer, self)
            if dlg.exec():
                self._document_print(self._report_document(), printer)
        except Exception as exc:
            QMessageBox.warning(self, self.tr("Print Report"), self.tr("Could not print report:\n{}" ).format(exc))

    @staticmethod
    def _split_tags(value: str) -> List[str]:
        return [p.strip() for p in value.replace(";", ",").split(",") if p.strip()]

    @staticmethod
    def _time_key(timestamp: Optional[str], grouping: str) -> Optional[str]:
        if not timestamp:
            return None
        parsed = ReportsDialog._iso_timestamp(timestamp)
        try:
            dt = datetime.strptime(parsed[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            try:
                dt = datetime.strptime(str(timestamp)[:10], "%Y-%m-%d")
            except ValueError:
                return str(timestamp)[:10]
        if grouping == "month":
            return dt.strftime("%Y-%m")
        if grouping == "week":
            iso = dt.isocalendar()
            return f"{iso.year}-W{iso.week:02d}"
        return dt.strftime("%Y-%m-%d")
