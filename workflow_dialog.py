# -*- coding: utf-8 -*-
"""Workflow/provenance recording for TerraAnalytica Work Log."""

from __future__ import annotations

import html
import json
import platform
from typing import Any, Dict, List, Optional

from qgis.PyQt.QtCore import Qt, QDateTime, QRectF, QUrl, QMarginsF
from qgis.PyQt.QtGui import QColor, QPainter, QPalette, QTextDocument, QFont, QPageSize, QPageLayout
from qgis.PyQt.QtPrintSupport import QPrinter, QPrintDialog
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from qgis.core import QgsApplication, QgsSettings, Qgis
from qgis.gui import QgsGui


def _json_safe(value: Any) -> Any:
    """Convert QVariant-ish values into JSON-safe Python values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if hasattr(value, "toString"):
        try:
            return value.toString()
        except Exception:
            pass
    return str(value)


def _printer_pdf_format():
    container = getattr(QPrinter, "OutputFormat", QPrinter)
    return getattr(container, "PdfFormat")


def _document_print(document: QTextDocument, printer: QPrinter) -> None:
    if hasattr(document, "print_"):
        document.print_(printer)
    else:
        document.print(printer)


def _configure_printer(printer: QPrinter) -> None:
    """Use a consistent A4 portrait layout for workflow method sheets."""
    try:
        size_ids = getattr(QPageSize, "PageSizeId", QPageSize)
        printer.setPageSize(QPageSize(getattr(size_ids, "A4")))
        orientations = getattr(QPageLayout, "Orientation", QPageLayout)
        printer.setPageOrientation(getattr(orientations, "Portrait"))
        units = getattr(QPageLayout, "Unit", QPageLayout)
        printer.setPageMargins(QMarginsF(10, 10, 10, 10), getattr(units, "Millimeter"))
    except Exception:
        pass


def _report_heading(kind: str) -> str:
    custom = QgsSettings().value("worklog/report_heading", "", type=str).strip()
    return f"{custom} - {kind}" if custom else kind

from .branding import TA_GOLD, brand_label_style, icon as ta_icon, install_theme, title_style


class WorkflowDiagramWidget(QWidget):
    """Simple dependency-free vertical workflow diagram."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.steps: List[Dict[str, Any]] = []
        self.setMinimumWidth(560)
        self.setMinimumHeight(260)

    def set_steps(self, steps: List[Dict[str, Any]]) -> None:
        self.steps = steps or []
        self.setMinimumHeight(max(260, 42 + len(self.steps) * 88))
        self.updateGeometry()
        self.update()

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        palette = self.palette()
        text = palette.color(QPalette.ColorRole.Text)
        fill = palette.color(QPalette.ColorRole.Base)
        border = QColor(TA_GOLD)
        muted = palette.color(QPalette.ColorRole.Mid)

        painter.setPen(text)
        title_font = painter.font()
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(18, 28, "Processing workflow")

        if not self.steps:
            title_font.setBold(False)
            painter.setFont(title_font)
            painter.setPen(muted)
            painter.drawText(18, 62, "Add manual or QGIS Processing History steps to build the diagram.")
            painter.end()
            return

        box_w = min(620, max(360, self.width() - 100))
        x = max(30, int((self.width() - box_w) / 2))
        y = 46
        box_h = 60
        gap = 28

        for i, step in enumerate(self.steps):
            rect = QRectF(x, y, box_w, box_h)
            painter.setPen(border)
            painter.setBrush(fill)
            painter.drawRoundedRect(rect, 6, 6)

            painter.setPen(text)
            f = painter.font()
            f.setBold(True)
            painter.setFont(f)
            step_type = step.get("step_type") or "Step"
            title = step.get("title") or "Untitled"
            painter.drawText(QRectF(x + 12, y + 7, box_w - 24, 22),
                             int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                             f"{i + 1}. {title}")
            f.setBold(False)
            painter.setFont(f)
            detail = step.get("algorithm_id") or step.get("description") or step_type
            if len(detail) > 105:
                detail = detail[:102] + "…"
            painter.setPen(muted)
            painter.drawText(QRectF(x + 12, y + 31, box_w - 24, 20),
                             int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                             f"{step_type} · {detail}")

            if i < len(self.steps) - 1:
                painter.setPen(border)
                cx = x + box_w / 2
                painter.drawLine(int(cx), int(y + box_h), int(cx), int(y + box_h + gap - 8))
                painter.drawText(QRectF(cx - 12, y + box_h + gap - 18, 24, 18),
                                 int(Qt.AlignmentFlag.AlignCenter), "▼")
            y += box_h + gap
        painter.end()


class StepEditDialog(QDialog):
    def __init__(self, parent, step: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.step = step or {}
        self.setWindowTitle(self.tr("TA Work Log — Workflow Step"))
        self.resize(680, 560)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.cmb_type = QComboBox()
        self.cmb_type.addItems([
            "Input / Acquire", "Pre-processing", "Processing", "Analysis",
            "QA / QC", "Manual", "Decision", "Output / Export",
        ])
        self.cmb_type.setEditable(True)
        self.edit_title = QLineEdit()
        self.edit_desc = QTextEdit()
        form.addRow(self.tr("Step type:"), self.cmb_type)
        form.addRow(self.tr("Title:"), self.edit_title)
        form.addRow(self.tr("Description:"), self.edit_desc)
        layout.addLayout(form)

        self.txt_details = QTextEdit()
        self.txt_details.setReadOnly(True)
        self.txt_details.setPlaceholderText(self.tr("Imported QGIS Processing parameters and commands appear here."))
        layout.addWidget(QLabel(self.tr("Captured processing details:")))
        layout.addWidget(self.txt_details, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._load()
        install_theme(self)

    def tr(self, text: str) -> str:
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate("StepEditDialog", text)

    def _load(self) -> None:
        st = self.step.get("step_type") or "Manual"
        i = self.cmb_type.findText(st)
        if i >= 0:
            self.cmb_type.setCurrentIndex(i)
        else:
            self.cmb_type.setEditText(st)
        self.edit_title.setText(self.step.get("title") or "")
        self.edit_desc.setPlainText(self.step.get("description") or "")
        bits = []
        if self.step.get("algorithm_id"):
            bits.append("Algorithm ID:\n" + str(self.step["algorithm_id"]))
        if self.step.get("parameters_json"):
            bits.append("Parameters:\n" + str(self.step["parameters_json"]))
        if self.step.get("python_command"):
            bits.append("Python command:\n" + str(self.step["python_command"]))
        if self.step.get("process_command"):
            bits.append("qgis_process command:\n" + str(self.step["process_command"]))
        if self.step.get("execution_log"):
            bits.append("Execution log:\n" + str(self.step["execution_log"]))
        self.txt_details.setPlainText("\n\n".join(bits))

    def _validate(self) -> None:
        if not self.edit_title.text().strip():
            QMessageBox.information(self, self.tr("Workflow Step"), self.tr("Give the step a short title."))
            return
        self.accept()

    def values(self) -> Dict[str, str]:
        return {
            "step_type": self.cmb_type.currentText().strip() or "Manual",
            "title": self.edit_title.text().strip(),
            "description": self.edit_desc.toPlainText().strip(),
        }


class ProcessingHistoryPicker(QDialog):
    """Select recent QGIS Processing history entries for a workflow."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.records: List[Dict[str, Any]] = []
        self.setWindowTitle(self.tr("TA Work Log — QGIS Processing History"))
        self.resize(920, 560)
        layout = QVBoxLayout(self)
        label = QLabel(self.tr(
            "Select one or more Processing runs. TerraAnalytica Work Log will retain the algorithm, "
            "parameters, Python/qgis_process commands and execution log supplied by QGIS."
        ))
        label.setWordWrap(True)
        layout.addWidget(label)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            self.tr("Time"), self.tr("Algorithm"), self.tr("Algorithm ID"), self.tr("Parameters")
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._load_history()
        install_theme(self)

    def tr(self, text: str) -> str:
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate("ProcessingHistoryPicker", text)

    def _load_history(self) -> None:
        try:
            registry = QgsGui.historyProviderRegistry()
            start = QDateTime.currentDateTime().addDays(-365)
            end = QDateTime.currentDateTime()
            entries = registry.queryEntries(start, end, "processing")
        except Exception as exc:
            QMessageBox.warning(self, self.tr("Processing History"),
                                self.tr("Could not read QGIS Processing History:\n{}" ).format(exc))
            entries = []

        records = []
        for entry in entries:
            try:
                data = dict(entry.entry)
            except Exception:
                data = _json_safe(entry.entry)
                if not isinstance(data, dict):
                    data = {}
            algorithm_id = str(data.get("algorithm_id") or "")
            display = algorithm_id or self.tr("Processing operation")
            if algorithm_id:
                try:
                    info = QgsApplication.processingRegistry().algorithmInformation(algorithm_id)
                    if getattr(info, "displayName", ""):
                        display = info.displayName
                except Exception:
                    try:
                        alg = QgsApplication.processingRegistry().algorithmById(algorithm_id)
                        if alg:
                            display = alg.displayName()
                    except Exception:
                        pass
            params = _json_safe(data.get("parameters") or {})
            inputs = params.get("inputs", params) if isinstance(params, dict) else params
            params_json = json.dumps(inputs, ensure_ascii=False, indent=2)
            timestamp = entry.timestamp.toString("yyyy-MM-dd HH:mm:ss") if entry.timestamp else ""
            records.append({
                "history_id": int(getattr(entry, "id", 0) or 0),
                "timestamp": timestamp,
                "algorithm_id": algorithm_id,
                "title": display,
                "parameters_json": params_json,
                "python_command": str(data.get("python_command") or ""),
                "process_command": str(data.get("process_command") or ""),
                "execution_log": str(data.get("log") or ""),
            })
        records.sort(key=lambda r: r["timestamp"], reverse=True)
        self.records = records[:200]
        self.table.setRowCount(len(self.records))
        for row, rec in enumerate(self.records):
            summary = rec["parameters_json"].replace("\n", " ")
            if len(summary) > 160:
                summary = summary[:157] + "…"
            vals = [rec["timestamp"], rec["title"], rec["algorithm_id"], summary]
            for col, value in enumerate(vals):
                self.table.setItem(row, col, QTableWidgetItem(value))

    def selected_records(self) -> List[Dict[str, Any]]:
        rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()})
        return [self.records[r] for r in rows if 0 <= r < len(self.records)]


class WorkflowEditorDialog(QDialog):
    """Edit one reproducible GIS/remote-sensing workflow."""

    def __init__(self, parent, db, workflow_id: int):
        super().__init__(parent)
        self.db = db
        self.workflow_id = workflow_id
        self.workflow = db.get_workflow(workflow_id) or {}
        self.setWindowTitle(self.tr("TA Work Log — Workflow — {}" ).format(self.workflow.get("name") or "Workflow"))
        self.resize(980, 760)
        self.setMinimumSize(760, 600)
        self._build_ui()
        install_theme(self, self._refresh_theme_assets)
        self._load()

    def tr(self, text: str) -> str:
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate("WorkflowEditorDialog", text)

    def _info_button(self, title: str, text: str, *, help_button: bool = False) -> QToolButton:
        b = QToolButton()
        if help_button:
            b.setText("?")
            b.setToolTip(self.tr("Help: {}" ).format(title))
            b.setAccessibleName(self.tr("Help: {}" ).format(title))
        else:
            b.setText("ⓘ")
            b.setToolTip(text)
            b.setAccessibleName(self.tr("Information: {}" ).format(title))
        b.setAutoRaise(True)
        b.clicked.connect(lambda: QMessageBox.information(self, title, text))
        return b

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
        self.title_label = QLabel(self.tr("Workflow Record"))
        brand_layout.addWidget(self.title_label)
        header.addWidget(brand_box)
        header.addWidget(self._info_button(
            self.tr("Workflow records"),
            self.tr("Record the reproducible method behind a GIS or remote-sensing result. Import QGIS Processing runs where possible, and add manual steps for work performed in other software, code, fieldwork or external services."),
            help_button=True,
        ))
        header.addStretch()
        layout.addLayout(header)

        form = QFormLayout()
        self.edit_name = QLineEdit()
        self.edit_version = QLineEdit()
        self.cmb_status = QComboBox(); self.cmb_status.addItems(["Draft", "Active", "Final"])
        self.edit_purpose = QTextEdit(); self.edit_purpose.setMaximumHeight(78)
        self.edit_notes = QTextEdit(); self.edit_notes.setMaximumHeight(78)
        form.addRow(self.tr("Workflow name:"), self.edit_name)
        row = QHBoxLayout(); row.addWidget(QLabel(self.tr("Version:"))); row.addWidget(self.edit_version); row.addWidget(QLabel(self.tr("Status:"))); row.addWidget(self.cmb_status); row.addStretch()
        form.addRow("", row)
        form.addRow(self.tr("Purpose / result:"), self.edit_purpose)
        form.addRow(self.tr("Method notes:"), self.edit_notes)
        layout.addLayout(form)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._steps_tab(), self.tr("Steps"))
        self.tabs.addTab(self._parameters_tab(), self.tr("Final Parameters"))
        self.tabs.addTab(self._artifacts_tab(), self.tr("Inputs & Outputs"))
        self.tabs.addTab(self._diagram_tab(), self.tr("Diagram"))
        self.tabs.currentChanged.connect(lambda _: self._refresh_diagram())
        layout.addWidget(self.tabs, 1)

        bottom = QHBoxLayout()
        self.btn_pdf = QToolButton(); self.btn_pdf.setIcon(ta_icon("pdf")); self.btn_pdf.setAutoRaise(True); self.btn_pdf.setToolTip(self.tr("Export workflow record to PDF")); self.btn_pdf.setAccessibleName(self.tr("Export workflow PDF"))
        self.btn_print = QToolButton(); self.btn_print.setIcon(ta_icon("print")); self.btn_print.setAutoRaise(True); self.btn_print.setToolTip(self.tr("Print workflow record")); self.btn_print.setAccessibleName(self.tr("Print workflow"))
        self.btn_save = QToolButton(); self.btn_save.setIcon(ta_icon("save")); self.btn_save.setAutoRaise(True); self.btn_save.setToolTip(self.tr("Save workflow changes")); self.btn_save.setAccessibleName(self.tr("Save workflow"))
        self.btn_close = QToolButton(); self.btn_close.setIcon(ta_icon("close")); self.btn_close.setAutoRaise(True); self.btn_close.setToolTip(self.tr("Close workflow editor")); self.btn_close.setAccessibleName(self.tr("Close"))
        bottom.addWidget(self.btn_pdf); bottom.addWidget(self.btn_print); bottom.addStretch(); bottom.addWidget(self.btn_save); bottom.addWidget(self.btn_close)
        layout.addLayout(bottom)
        self.btn_pdf.clicked.connect(self._export_pdf)
        self.btn_print.clicked.connect(self._print_report)
        self.btn_save.clicked.connect(self._save_from_button)
        self.btn_close.clicked.connect(self.accept)

    def _refresh_theme_assets(self) -> None:
        self.brand_label.setStyleSheet(brand_label_style())
        self.title_label.setStyleSheet(title_style(self, 17))
        self.btn_pdf.setIcon(ta_icon("pdf", 18, self))
        self.btn_print.setIcon(ta_icon("print", 18, self))
        self.btn_save.setIcon(ta_icon("save", 18, self))
        self.btn_close.setIcon(ta_icon("close", 18, self))

    def _steps_tab(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        self.tbl_steps = QTableWidget(0, 4)
        self.tbl_steps.setHorizontalHeaderLabels(["#", self.tr("Type"), self.tr("Step"), self.tr("Algorithm / detail")])
        self.tbl_steps.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_steps.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_steps.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        h = self.tbl_steps.horizontalHeader(); h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents); h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents); h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch); h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.tbl_steps, 1)
        row = QHBoxLayout()
        self.btn_add_manual = QToolButton(); self.btn_add_manual.setIcon(ta_icon("new")); self.btn_add_manual.setAutoRaise(True); self.btn_add_manual.setToolTip(self.tr("Add a manual workflow step")); self.btn_add_manual.setAccessibleName(self.tr("Add manual step"))
        self.btn_add_history = QToolButton(); self.btn_add_history.setIcon(ta_icon("history")); self.btn_add_history.setAutoRaise(True); self.btn_add_history.setToolTip(self.tr("Import one or more QGIS Processing History records")); self.btn_add_history.setAccessibleName(self.tr("QGIS Processing History"))
        self.btn_edit_step = QToolButton(); self.btn_edit_step.setIcon(ta_icon("view")); self.btn_edit_step.setAutoRaise(True); self.btn_edit_step.setToolTip(self.tr("Open or edit the selected workflow step")); self.btn_edit_step.setAccessibleName(self.tr("Open or edit step"))
        self.btn_remove_step = QToolButton(); self.btn_remove_step.setIcon(ta_icon("delete")); self.btn_remove_step.setAutoRaise(True); self.btn_remove_step.setToolTip(self.tr("Remove the selected workflow step")); self.btn_remove_step.setAccessibleName(self.tr("Remove step"))
        self.btn_up = QToolButton(); self.btn_up.setIcon(ta_icon("up")); self.btn_up.setAutoRaise(True); self.btn_up.setToolTip(self.tr("Move selected step up")); self.btn_up.setAccessibleName(self.tr("Move step up"))
        self.btn_down = QToolButton(); self.btn_down.setIcon(ta_icon("down")); self.btn_down.setAutoRaise(True); self.btn_down.setToolTip(self.tr("Move selected step down")); self.btn_down.setAccessibleName(self.tr("Move step down"))
        for b in [self.btn_add_manual, self.btn_add_history, self.btn_edit_step, self.btn_remove_step, self.btn_up, self.btn_down]: row.addWidget(b)
        row.addStretch(); lay.addLayout(row)
        self.btn_add_manual.clicked.connect(self._add_manual_step); self.btn_add_history.clicked.connect(self._add_history_steps); self.btn_edit_step.clicked.connect(self._edit_step); self.btn_remove_step.clicked.connect(self._remove_step); self.btn_up.clicked.connect(lambda: self._move_step(-1)); self.btn_down.clicked.connect(lambda: self._move_step(1)); self.tbl_steps.itemDoubleClicked.connect(lambda *_: self._edit_step())
        return w

    def _parameters_tab(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        help_row = QHBoxLayout(); lbl = QLabel(self.tr("Record the parameter values that define the final/reproducible method, not every experimental value.")); lbl.setWordWrap(True); help_row.addWidget(lbl); help_row.addWidget(self._info_button(self.tr("Final parameters"), self.tr("Examples include CRS, pixel size, resampling method, cloud threshold, band selection, kernel size, model settings or classification thresholds. These values are intended to describe the final method used for the result."))); lay.addLayout(help_row)
        self.tbl_params = QTableWidget(0, 4); self.tbl_params.setHorizontalHeaderLabels([self.tr("Parameter"), self.tr("Value"), self.tr("Unit"), self.tr("Notes")]); self.tbl_params.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); lay.addWidget(self.tbl_params, 1)
        row = QHBoxLayout(); b1 = QToolButton(); b1.setIcon(ta_icon("parameter")); b1.setAutoRaise(True); b1.setToolTip(self.tr("Add a final parameter")); b1.setAccessibleName(self.tr("Add parameter")); b2 = QToolButton(); b2.setIcon(ta_icon("delete")); b2.setAutoRaise(True); b2.setToolTip(self.tr("Remove selected parameter")); b2.setAccessibleName(self.tr("Remove parameter")); row.addWidget(b1); row.addWidget(b2); row.addStretch(); lay.addLayout(row); b1.clicked.connect(lambda: self.tbl_params.insertRow(self.tbl_params.rowCount())); b2.clicked.connect(lambda: self._remove_table_row(self.tbl_params))
        return w

    def _artifacts_tab(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        lbl = QLabel(self.tr("Record significant source datasets and final outputs. Paths/URIs can point to local files, GeoPackages, cloud assets, catalogue IDs or dataset URLs.")); lbl.setWordWrap(True); lay.addWidget(lbl)
        self.tbl_artifacts = QTableWidget(0, 4); self.tbl_artifacts.setHorizontalHeaderLabels([self.tr("Kind"), self.tr("Label"), self.tr("Path / URI / ID"), self.tr("Notes")]); self.tbl_artifacts.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); lay.addWidget(self.tbl_artifacts, 1)
        row = QHBoxLayout(); bi = QToolButton(); bi.setIcon(ta_icon("input")); bi.setAutoRaise(True); bi.setToolTip(self.tr("Add an input dataset or source")); bi.setAccessibleName(self.tr("Add input")); bo = QToolButton(); bo.setIcon(ta_icon("output")); bo.setAutoRaise(True); bo.setToolTip(self.tr("Add an output product")); bo.setAccessibleName(self.tr("Add output")); br = QToolButton(); br.setIcon(ta_icon("delete")); br.setAutoRaise(True); br.setToolTip(self.tr("Remove selected input/output")); br.setAccessibleName(self.tr("Remove input or output")); row.addWidget(bi); row.addWidget(bo); row.addWidget(br); row.addStretch(); lay.addLayout(row); bi.clicked.connect(lambda: self._add_artifact("Input")); bo.clicked.connect(lambda: self._add_artifact("Output")); br.clicked.connect(lambda: self._remove_table_row(self.tbl_artifacts))
        return w

    def _diagram_tab(self) -> QWidget:
        scroll = QScrollArea(); scroll.setWidgetResizable(True); self.diagram = WorkflowDiagramWidget(); scroll.setWidget(self.diagram); return scroll

    def _load(self) -> None:
        w = self.db.get_workflow(self.workflow_id) or {}
        self.workflow = w
        self.edit_name.setText(w.get("name") or "")
        self.edit_version.setText(w.get("version") or "1.0")
        i = self.cmb_status.findText(w.get("status") or "Draft"); self.cmb_status.setCurrentIndex(max(i, 0))
        self.edit_purpose.setPlainText(w.get("purpose") or "")
        self.edit_notes.setPlainText(w.get("notes") or "")
        self._refresh_steps()
        params = self.db.list_workflow_parameters(self.workflow_id); self.tbl_params.setRowCount(len(params))
        for r, p in enumerate(params):
            for c, key in enumerate(["name", "value", "unit", "notes"]): self.tbl_params.setItem(r, c, QTableWidgetItem(str(p.get(key) or "")))
        arts = self.db.list_workflow_artifacts(self.workflow_id); self.tbl_artifacts.setRowCount(len(arts))
        for r, a in enumerate(arts):
            for c, key in enumerate(["kind", "label", "path_uri", "notes"]): self.tbl_artifacts.setItem(r, c, QTableWidgetItem(str(a.get(key) or "")))
        self._refresh_diagram()

    def _selected_step(self) -> Optional[Dict[str, Any]]:
        row = self.tbl_steps.currentRow()
        steps = self.db.list_workflow_steps(self.workflow_id)
        return steps[row] if 0 <= row < len(steps) else None

    def _refresh_steps(self) -> None:
        steps = self.db.list_workflow_steps(self.workflow_id)
        self.tbl_steps.setRowCount(len(steps))
        for r, s in enumerate(steps):
            detail = s.get("algorithm_id") or s.get("description") or ""
            vals = [str(r + 1), s.get("step_type") or "", s.get("title") or "", detail]
            for c, v in enumerate(vals): self.tbl_steps.setItem(r, c, QTableWidgetItem(str(v)))
        self._refresh_diagram()

    def _refresh_diagram(self) -> None:
        if hasattr(self, "diagram"):
            self.diagram.set_steps(self.db.list_workflow_steps(self.workflow_id))

    def _add_manual_step(self) -> None:
        dlg = StepEditDialog(self)
        if dlg.exec():
            v = dlg.values(); self.db.add_workflow_step(self.workflow_id, v["step_type"], v["title"], description=v["description"]); self._refresh_steps()

    def _add_history_steps(self) -> None:
        dlg = ProcessingHistoryPicker(self)
        if not dlg.exec(): return
        selected = dlg.selected_records()
        if not selected:
            QMessageBox.information(self, self.tr("Processing History"), self.tr("Select at least one Processing run.")); return
        for rec in reversed(selected):
            self.db.add_workflow_step(
                self.workflow_id, "Processing", rec["title"],
                description=self.tr("Imported from QGIS Processing History."),
                algorithm_id=rec["algorithm_id"], parameters_json=rec["parameters_json"],
                python_command=rec["python_command"], process_command=rec["process_command"],
                execution_log=rec["execution_log"], source_history_id=rec["history_id"],
                source_timestamp=rec["timestamp"],
            )
        self._refresh_steps()

    def _edit_step(self) -> None:
        step = self._selected_step()
        if not step: return
        dlg = StepEditDialog(self, step)
        if dlg.exec():
            v = dlg.values(); self.db.update_workflow_step(step["id"], v["step_type"], v["title"], v["description"]); self._refresh_steps()

    def _remove_step(self) -> None:
        step = self._selected_step()
        if not step: return
        if QMessageBox.question(self, self.tr("Remove Step"), self.tr("Remove this workflow step?")) == QMessageBox.StandardButton.Yes:
            self.db.delete_workflow_step(step["id"]); self._refresh_steps()

    def _move_step(self, direction: int) -> None:
        step = self._selected_step()
        if not step: return
        row = self.tbl_steps.currentRow(); self.db.move_workflow_step(self.workflow_id, step["id"], direction); self._refresh_steps(); self.tbl_steps.selectRow(max(0, min(self.tbl_steps.rowCount() - 1, row + direction)))

    @staticmethod
    def _remove_table_row(table: QTableWidget) -> None:
        r = table.currentRow()
        if r >= 0: table.removeRow(r)

    def _add_artifact(self, kind: str) -> None:
        r = self.tbl_artifacts.rowCount(); self.tbl_artifacts.insertRow(r); self.tbl_artifacts.setItem(r, 0, QTableWidgetItem(kind))

    @staticmethod
    def _table_rows(table: QTableWidget, keys: List[str]) -> List[Dict[str, str]]:
        out = []
        for r in range(table.rowCount()):
            row = {}
            for c, key in enumerate(keys): row[key] = table.item(r, c).text().strip() if table.item(r, c) else ""
            out.append(row)
        return out

    def _save(self) -> bool:
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.information(self, self.tr("Workflow"), self.tr("Give the workflow a name.")); return False
        self.db.update_workflow(self.workflow_id, name, self.edit_purpose.toPlainText().strip(), self.edit_version.text().strip() or "1.0", self.cmb_status.currentText(), self.edit_notes.toPlainText().strip())
        self.db.replace_workflow_parameters(self.workflow_id, self._table_rows(self.tbl_params, ["name", "value", "unit", "notes"]))
        self.db.replace_workflow_artifacts(self.workflow_id, self._table_rows(self.tbl_artifacts, ["kind", "label", "path_uri", "notes"]))
        self.workflow = self.db.get_workflow(self.workflow_id) or {}; self.setWindowTitle(self.tr("TA Work Log — Workflow — {}" ).format(name)); self._refresh_diagram()
        return True

    def _save_from_button(self) -> None:
        try:
            if self._save():
                QMessageBox.information(self, self.tr("Workflow"), self.tr("Workflow saved."))
        except Exception as exc:
            QMessageBox.warning(self, self.tr("Workflow"), self.tr("Could not save workflow:\n{}").format(exc))

    def _report_document(self) -> QTextDocument:
        self._save()
        w = self.db.get_workflow(self.workflow_id) or {}
        steps = self.db.list_workflow_steps(self.workflow_id)
        params = self.db.list_workflow_parameters(self.workflow_id)
        arts = self.db.list_workflow_artifacts(self.workflow_id)
        doc = QTextDocument()
        doc.setDocumentMargin(4)
        font = QFont(); font.setPointSizeF(8.0); doc.setDefaultFont(font)
        image = self.diagram.grab().toImage()
        doc.addResource(getattr(getattr(QTextDocument, "ResourceType", QTextDocument), "ImageResource"), QUrl("workflow_diagram.png"), image)

        def esc(v):
            return html.escape(str(v or ""))

        step_rows = "".join(
            f"<tr><td class='num'>{i+1}</td><td>{esc(s.get('step_type'))}</td><td>{esc(s.get('title'))}</td><td>{esc(s.get('algorithm_id') or s.get('description'))}</td></tr>"
            for i, s in enumerate(steps)
        ) or "<tr><td colspan='4' class='muted'>No steps recorded</td></tr>"
        param_rows = "".join(
            f"<tr><td>{esc(p.get('name'))}</td><td>{esc(p.get('value'))}</td><td>{esc(p.get('unit'))}</td><td>{esc(p.get('notes'))}</td></tr>"
            for p in params
        ) or "<tr><td colspan='4' class='muted'>No final parameters recorded</td></tr>"
        art_rows = "".join(
            f"<tr><td>{esc(a.get('kind'))}</td><td>{esc(a.get('label'))}</td><td class='path'>{esc(a.get('path_uri'))}</td><td>{esc(a.get('notes'))}</td></tr>"
            for a in arts
        ) or "<tr><td colspan='4' class='muted'>No inputs/outputs recorded</td></tr>"

        style = """
        body{font-family:Arial,Helvetica,sans-serif;font-size:8pt;color:#222;}
        h1{font-size:15pt;margin:0 0 5px 0;font-weight:600;}
        h2{font-size:10.3pt;margin:9px 0 3px 0;font-weight:600;}
        p{margin:2px 0 5px 0;line-height:1.18;} .meta{font-size:7.7pt;} .muted{color:#666;}
        table{border-collapse:collapse;width:100%;} th,td{border:0.6px solid #aaa;padding:2px 3px;vertical-align:top;}
        th{background:#f0f0f0;font-size:7.4pt;font-weight:600;} td{font-size:7.4pt;}
        tr{page-break-inside:avoid;} .num{text-align:right;white-space:nowrap;} .path{font-size:6.9pt;}
        .diagram{text-align:center;margin:1px 0 3px 0;}
        """
        heading = _report_heading("Workflow Record")
        body = f"""
        <html><head><style>{style}</style></head><body>
        <h1>{esc(heading)}</h1>
        <p class='meta'><b>Project:</b> {esc(w.get('project_name'))}<br>
        <b>Workflow:</b> {esc(w.get('name'))}<br>
        <b>Version:</b> {esc(w.get('version'))} &nbsp;&nbsp; <b>Status:</b> {esc(w.get('status'))} &nbsp;&nbsp;
        <b>QGIS:</b> {esc(w.get('qgis_version'))} &nbsp;&nbsp; <b>Platform:</b> {esc(w.get('platform'))}</p>
        <h2>Purpose / result</h2><p>{esc(w.get('purpose')).replace(chr(10), '<br>')}</p>
        <h2>Workflow diagram</h2><div class='diagram'><img src='workflow_diagram.png' width='400'></div>
        <h2>Processing steps</h2>
        <table><tr><th width='5%'>#</th><th width='18%'>Type</th><th width='30%'>Step</th><th width='47%'>Algorithm / detail</th></tr>{step_rows}</table>
        <h2>Final parameters</h2>
        <table><tr><th width='26%'>Parameter</th><th width='24%'>Value</th><th width='12%'>Unit</th><th width='38%'>Notes</th></tr>{param_rows}</table>
        <h2>Inputs & outputs</h2>
        <table><tr><th width='12%'>Kind</th><th width='24%'>Label</th><th width='36%'>Path / URI / ID</th><th width='28%'>Notes</th></tr>{art_rows}</table>
        <h2>Method notes</h2><p>{esc(w.get('notes')).replace(chr(10), '<br>')}</p>
        </body></html>"""
        doc.setHtml(body)
        return doc

    def _export_pdf(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Export Workflow PDF"), f"{self.edit_name.text().strip() or 'workflow'}_v{self.edit_version.text().strip() or '1.0'}.pdf", self.tr("PDF files (*.pdf)"))
        if not path: return
        if not path.lower().endswith(".pdf"): path += ".pdf"
        try:
            printer = QPrinter(); printer.setOutputFormat(_printer_pdf_format()); printer.setOutputFileName(path); _configure_printer(printer); _document_print(self._report_document(), printer)
            QMessageBox.information(self, self.tr("Workflow PDF"), self.tr("Workflow report exported to:\n{}" ).format(path))
        except Exception as exc:
            QMessageBox.warning(self, self.tr("Workflow PDF"), self.tr("Could not create PDF:\n{}" ).format(exc))

    def _print_report(self) -> None:
        try:
            printer = QPrinter(); _configure_printer(printer); dlg = QPrintDialog(printer, self)
            if dlg.exec(): _document_print(self._report_document(), printer)
        except Exception as exc:
            QMessageBox.warning(self, self.tr("Print Workflow"), self.tr("Could not print workflow:\n{}" ).format(exc))


class WorkflowManagerDialog(QDialog):
    """Browse/create workflow records across TerraAnalytica projects."""

    def __init__(self, parent, db, current_project_id=None):
        super().__init__(parent)
        self.db = db
        self.current_project_id = current_project_id
        self.setWindowTitle(self.tr("TA Work Log — Workflows"))
        self.resize(860, 560)
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        brand_box = QWidget()
        brand_layout = QVBoxLayout(brand_box)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(0)
        self.brand_label = QLabel("TERRAANALYTICA")
        self.brand_label.setStyleSheet(brand_label_style())
        brand_layout.addWidget(self.brand_label)
        self.title_label = QLabel(self.tr("Workflows"))
        brand_layout.addWidget(self.title_label)
        header.addWidget(brand_box)
        header.addStretch()
        layout.addLayout(header)
        pr = QHBoxLayout(); pr.addWidget(QLabel(self.tr("Project:"))); self.cmb_project = QComboBox(); pr.addWidget(self.cmb_project, 1); self.btn_new = QToolButton(); self.btn_new.setIcon(ta_icon("new")); self.btn_new.setAutoRaise(True); self.btn_new.setToolTip(self.tr("Create a new workflow")); self.btn_new.setAccessibleName(self.tr("New workflow")); pr.addWidget(self.btn_new); layout.addLayout(pr)
        self.table = QTableWidget(0, 5); self.table.setHorizontalHeaderLabels([self.tr("Workflow"), self.tr("Version"), self.tr("Status"), self.tr("Steps"), self.tr("Updated")]); self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); h=self.table.horizontalHeader(); h.setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch); [h.setSectionResizeMode(i,QHeaderView.ResizeMode.ResizeToContents) for i in range(1,5)]; layout.addWidget(self.table,1)
        row=QHBoxLayout(); self.btn_edit=QToolButton(); self.btn_edit.setIcon(ta_icon("edit")); self.btn_edit.setAutoRaise(True); self.btn_edit.setToolTip(self.tr("Open or edit selected workflow")); self.btn_edit.setAccessibleName(self.tr("Open or edit workflow")); self.btn_delete=QToolButton(); self.btn_delete.setIcon(ta_icon("delete")); self.btn_delete.setAutoRaise(True); self.btn_delete.setToolTip(self.tr("Delete selected workflow")); self.btn_delete.setAccessibleName(self.tr("Delete workflow")); self.btn_refresh=QToolButton(); self.btn_refresh.setIcon(ta_icon("refresh")); self.btn_refresh.setAutoRaise(True); self.btn_refresh.setToolTip(self.tr("Refresh workflow list")); self.btn_refresh.setAccessibleName(self.tr("Refresh workflows")); row.addWidget(self.btn_edit); row.addWidget(self.btn_delete); row.addWidget(self.btn_refresh); row.addStretch(); close=QToolButton(); close.setIcon(ta_icon("close")); close.setAutoRaise(True); close.setToolTip(self.tr("Close workflow manager")); close.setAccessibleName(self.tr("Close")); row.addWidget(close); layout.addLayout(row)
        self._ids=[]; self._load_projects(); self.refresh(); self.cmb_project.currentIndexChanged.connect(self.refresh); self.btn_new.clicked.connect(self._new); self.btn_edit.clicked.connect(self._edit); self.btn_delete.clicked.connect(self._delete); self.btn_refresh.clicked.connect(self.refresh); self.table.itemDoubleClicked.connect(lambda *_: self._edit()); close.clicked.connect(self.accept)
        self._btn_close = close
        install_theme(self, self._refresh_theme_assets)

    def _refresh_theme_assets(self) -> None:
        self.brand_label.setStyleSheet(brand_label_style())
        self.title_label.setStyleSheet(title_style(self, 17))
        self.btn_new.setIcon(ta_icon("new", 18, self))
        self.btn_edit.setIcon(ta_icon("edit", 18, self))
        self.btn_delete.setIcon(ta_icon("delete", 18, self))
        self.btn_refresh.setIcon(ta_icon("refresh", 18, self))
        self._btn_close.setIcon(ta_icon("close", 18, self))

    def tr(self, text: str) -> str:
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate("WorkflowManagerDialog", text)

    def _load_projects(self) -> None:
        self.cmb_project.clear(); idx=0
        for i,p in enumerate(self.db.list_projects()):
            self.cmb_project.addItem(p["name"], p["id"])
            if p["id"] == self.current_project_id: idx=i
        if self.cmb_project.count(): self.cmb_project.setCurrentIndex(idx)

    def refresh(self) -> None:
        project_id=self.cmb_project.currentData(); rows=self.db.list_workflows(project_id); self._ids=[r["id"] for r in rows]; self.table.setRowCount(len(rows))
        for i,w in enumerate(rows):
            vals=[w.get("name") or "",w.get("version") or "",w.get("status") or "",str(w.get("step_count") or 0),w.get("updated_at") or ""]
            for c,v in enumerate(vals): self.table.setItem(i,c,QTableWidgetItem(str(v)))

    def _selected_id(self) -> Optional[int]:
        r=self.table.currentRow(); return self._ids[r] if 0 <= r < len(self._ids) else None

    def _new(self) -> None:
        project_id=self.cmb_project.currentData()
        if project_id is None:
            QMessageBox.information(self,self.tr("Workflow"),self.tr("Select a project first.")); return
        try:
            qgis_version = getattr(Qgis, "QGIS_VERSION", "") or (Qgis.version() if hasattr(Qgis, "version") else "")
        except Exception: qgis_version=""
        wid=self.db.create_workflow(project_id,self.tr("New GIS / Remote Sensing Workflow"),qgis_version=qgis_version,platform_name=platform.platform())
        dlg=WorkflowEditorDialog(self,self.db,wid); dlg.exec(); self.refresh()

    def _edit(self) -> None:
        wid=self._selected_id()
        if not wid: return
        dlg=WorkflowEditorDialog(self,self.db,wid); dlg.exec(); self.refresh()

    def _delete(self) -> None:
        wid=self._selected_id()
        if not wid: return
        w=self.db.get_workflow(wid) or {}
        if QMessageBox.question(self,self.tr("Delete Workflow"),self.tr("Delete workflow '{}' and its recorded steps/parameters? Work Log entries will be kept but unlinked." ).format(w.get("name") or "")) == QMessageBox.StandardButton.Yes:
            self.db.delete_workflow(wid); self.refresh()
