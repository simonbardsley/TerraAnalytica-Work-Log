# -*- coding: utf-8 -*-
"""
Full entry create / edit dialog with screenshot attachment support.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from qgis.PyQt.QtCore import Qt, QDateTime, QSize
from qgis.PyQt.QtGui import QPixmap, QIcon, QImage
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QSpinBox,
    QDateTimeEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QCheckBox,
    QSizePolicy,
    QDialogButtonBox,
    QScrollArea,
    QToolButton,
    QWidget,
)

from qgis.core import QgsProject, QgsMapSettings, QgsMapRendererParallelJob, Qgis
from qgis.gui import QgsMapCanvas

from .branding import brand_label_style, install_theme, muted_style, title_style


class EntryDialog(QDialog):
    """Create or edit a single work-log entry."""

    def __init__(
        self,
        parent,
        db,
        project_id: int,
        project_name: str,
        iface,
        entry_id: Optional[int] = None,
        default_user: str = "",
    ):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.project_name = project_name
        self.iface = iface
        self.entry_id = entry_id
        self.saved_entry_id = None
        self.default_user = (default_user or "").strip()
        self._pending_files: List[str] = []  # paths to attach on save
        self._pending_blobs: List[tuple] = []  # (filename, bytes, mime)
        self._removed_attachment_ids: List[int] = []

        title = (
            self.tr("Edit Entry") if entry_id else self.tr("New Entry")
        )
        self.setWindowTitle(self.tr("TA Work Log — {} — {}" ).format(title, project_name))
        self.resize(560, 640)
        self.setMinimumSize(420, 340)

        self._build_ui()
        install_theme(self, self._refresh_theme_assets)
        if entry_id:
            self._load_entry()
        else:
            self._prefill_new()

    def tr(self, text: str) -> str:
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate("EntryDialog", text)

    def _refresh_theme_assets(self) -> None:
        self.brand_label.setStyleSheet(brand_label_style())
        self.title_label.setStyleSheet(title_style(self, 17))

    def _field_label(self, label: str, help_text: str) -> QWidget:
        """Compact label with a clickable/hoverable information icon."""
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(3)
        row.addWidget(QLabel(label))
        info = QToolButton()
        info.setText("ⓘ")
        info.setAutoRaise(True)
        info.setToolTip(help_text)
        info.setAccessibleName(self.tr("Information about {}" ).format(label.rstrip(":")))
        info.clicked.connect(
            lambda checked=False, title=label.rstrip(":"), text=help_text:
                QMessageBox.information(self, title, text)
        )
        row.addWidget(info)
        return widget

    @staticmethod
    def _normalise_tags(value: str) -> str:
        """Store tags compactly and de-duplicate case-insensitively."""
        parts = [p.strip() for p in value.replace(";", ",").split(",") if p.strip()]
        seen = set()
        clean = []
        for part in parts:
            key = part.casefold()
            if key not in seen:
                seen.add(key)
                clean.append(part)
        return ",".join(clean)

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # TerraAnalytica family header
        brand_box = QWidget()
        brand_layout = QVBoxLayout(brand_box)
        brand_layout.setContentsMargins(0, 0, 0, 3)
        brand_layout.setSpacing(0)
        self.brand_label = QLabel("TERRAANALYTICA")
        self.brand_label.setStyleSheet(brand_label_style())
        brand_layout.addWidget(self.brand_label)
        self.title_label = QLabel(self.tr("Edit Work Log Entry") if self.entry_id else self.tr("New Work Log Entry"))
        brand_layout.addWidget(self.title_label)
        layout.addWidget(brand_box)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        # Timestamp
        self.dt_timestamp = QDateTimeEdit()
        self.dt_timestamp.setCalendarPopup(True)
        self.dt_timestamp.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_timestamp.setDateTime(QDateTime.currentDateTime())
        form.addRow(self._field_label(
            self.tr("Date / time:"),
            self.tr("When the GIS or remote-sensing work was actually carried out. This can differ from when you enter the record."),
        ), self.dt_timestamp)

        # User / analyst. The current session user is only a default; the value is stored per entry.
        self.cmb_user = QComboBox()
        self.cmb_user.setEditable(True)
        self.cmb_user.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.cmb_user.addItem("")
        for user in self.db.list_users():
            self.cmb_user.addItem(user)
        if self.default_user:
            idx = self.cmb_user.findText(self.default_user)
            if idx >= 0:
                self.cmb_user.setCurrentIndex(idx)
            else:
                self.cmb_user.setEditText(self.default_user)
        form.addRow(self._field_label(
            self.tr("User / analyst:"),
            self.tr("The person who performed this work. New entries default to the current Work Log session user, but you can change it for an individual record. This is useful for shared project databases and reporting by analyst."),
        ), self.cmb_user)

        # Category
        self.cmb_category = QComboBox()
        self.cmb_category.setEditable(True)
        for cat in self.db.list_categories():
            self.cmb_category.addItem(cat)
        form.addRow(self._field_label(
            self.tr("Work class:"),
            self.tr("A broad class of work used for reporting, such as Remote Sensing, GIS / Spatial Analysis, Fieldwork / Ground Truth, Coding / Automation or Documentation / Reporting."),
        ), self.cmb_category)

        # Duration
        dur_row = QHBoxLayout()
        self.spin_duration = QSpinBox()
        self.spin_duration.setRange(0, 24 * 60)
        self.spin_duration.setSuffix(self.tr(" min"))
        self.spin_duration.setSpecialValueText(self.tr("(none)"))
        self.spin_duration.setValue(0)
        dur_row.addWidget(self.spin_duration)
        dur_row.addStretch()
        form.addRow(self._field_label(
            self.tr("Time spent:"),
            self.tr("Duration spent on this work item in minutes. Reporting converts this to hours by project, work class, date and tag."),
        ), dur_row)

        # Title
        self.edit_title = QLineEdit()
        self.edit_title.setPlaceholderText(self.tr("Short title (optional)"))
        form.addRow(self._field_label(
            self.tr("Title:"),
            self.tr("A short searchable title for the work item. Keep the detailed technical record in Description."),
        ), self.edit_title)

        # Tags
        self.edit_tags = QLineEdit()
        self.edit_tags.setPlaceholderText(self.tr("e.g. Sentinel-2, SAR, NDVI, LiDAR, QGIS"))
        self.edit_tags.setToolTip(self.tr("Comma-separated GIS/remote-sensing technologies, sensors, datasets, methods or themes."))
        form.addRow(self._field_label(
            self.tr("Tags:"),
            self.tr("Specific descriptors used for filtering and reporting. Examples: Sentinel-1, Sentinel-2, SAR, NDVI, LiDAR, drone, QGIS, Python, ground truth. Separate tags with commas."),
        ), self.edit_tags)

        # Optional reproducible workflow link
        self.cmb_workflow = QComboBox()
        self.cmb_workflow.addItem(self.tr("(no workflow linked)"), None)
        for workflow in self.db.list_workflows(project_id=self.project_id):
            label = "{}  v{}".format(workflow.get("name") or "Workflow", workflow.get("version") or "1.0")
            self.cmb_workflow.addItem(label, workflow.get("id"))
        form.addRow(self._field_label(
            self.tr("Workflow:"),
            self.tr("Optionally link this time/log entry to a reproducible GIS or remote-sensing workflow. The workflow stores processing steps, QGIS Processing parameters, final parameters, and inputs/outputs."),
        ), self.cmb_workflow)

        # Description
        self.edit_desc = QTextEdit()
        self.edit_desc.setPlaceholderText(
            self.tr(
                "What did you do?\n"
                "Processes run, file names, parameters, observations…"
            )
        )
        self.edit_desc.setAcceptRichText(False)
        form.addRow(self._field_label(
            self.tr("Description:"),
            self.tr("Technical notes describing what was done: datasets, processing steps, parameters, observations, outputs, uncertainties or decisions."),
        ), self.edit_desc)

        # Workspace (read-only info)
        self.lbl_workspace = QLabel("")
        self.lbl_workspace.setStyleSheet(muted_style(self, 11))
        form.addRow(self._field_label(
            self.tr("Workspace:"),
            self.tr("The QGIS project/workspace associated with the entry. This is recorded automatically for traceability."),
        ), self.lbl_workspace)

        body_layout.addLayout(form)

        # --- Attachments ---
        att_group = QGroupBox(self.tr("Attachments / Screenshots"))
        att_layout = QVBoxLayout(att_group)

        self.list_attachments = QListWidget()
        self.list_attachments.setMaximumHeight(140)
        self.list_attachments.setIconSize(QSize(48, 48))
        att_layout.addWidget(self.list_attachments)

        att_btn_row = QHBoxLayout()
        self.btn_screenshot = QPushButton(self.tr("Capture map canvas"))
        self.btn_screenshot.setToolTip(
            self.tr("Take a screenshot of the current map canvas and attach it")
        )
        self.btn_add_file = QPushButton(self.tr("Add file…"))
        self.btn_remove_att = QPushButton(self.tr("Remove selected"))
        att_btn_row.addWidget(self.btn_screenshot)
        att_btn_row.addWidget(self.btn_add_file)
        att_btn_row.addWidget(self.btn_remove_att)
        att_layout.addLayout(att_btn_row)

        self.chk_embed = QCheckBox(
            self.tr("Also store image inside the database (BLOB)")
        )
        self.chk_embed.setToolTip(
            self.tr(
                "By default images are saved as files next to the database.\n"
                "Enable this to also embed a copy inside SQLite (useful for portability, "
                "but the DB grows)."
            )
        )
        att_layout.addWidget(self.chk_embed)

        body_layout.addWidget(att_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save = buttons.button(QDialogButtonBox.StandardButton.Save)
        cancel = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        save.clicked.connect(self._save)
        cancel.clicked.connect(self.reject)
        for button in (self.btn_screenshot, self.btn_add_file, self.btn_remove_att):
            button.setAutoDefault(False)
        save.setDefault(True)
        layout.addWidget(buttons)

        # Signals
        self.btn_screenshot.clicked.connect(self._capture_canvas)
        self.btn_add_file.clicked.connect(self._add_file)
        self.btn_remove_att.clicked.connect(self._remove_selected_attachment)

    # ------------------------------------------------------------------
    def _prefill_new(self) -> None:
        proj = QgsProject.instance()
        workspace = proj.title() or Path(proj.fileName()).stem if proj.fileName() else self.project_name
        self.lbl_workspace.setText(workspace or "—")
        # sensible default category
        idx = self.cmb_category.findText("Notes")
        if idx >= 0:
            self.cmb_category.setCurrentIndex(idx)

    def _load_entry(self) -> None:
        entry = self.db.get_entry(self.entry_id)
        if not entry:
            QMessageBox.warning(self, self.tr("Work Log"), self.tr("Entry not found."))
            self.reject()
            return

        ts = QDateTime.fromString(entry["timestamp"], "yyyy-MM-dd HH:mm:ss")
        if ts.isValid():
            self.dt_timestamp.setDateTime(ts)

        user_name = entry.get("user_name") or ""
        idx_user = self.cmb_user.findText(user_name)
        if idx_user >= 0:
            self.cmb_user.setCurrentIndex(idx_user)
        else:
            self.cmb_user.setEditText(user_name)

        idx = self.cmb_category.findText(entry.get("category") or "")
        if idx >= 0:
            self.cmb_category.setCurrentIndex(idx)
        else:
            self.cmb_category.setEditText(entry.get("category") or "")

        if entry.get("duration_minutes") is not None:
            self.spin_duration.setValue(int(entry["duration_minutes"]))
        self.edit_title.setText(entry.get("title") or "")
        self.edit_tags.setText((entry.get("tags") or "").replace(",", ", "))
        workflow_id = entry.get("workflow_id")
        if workflow_id is not None:
            for i in range(self.cmb_workflow.count()):
                if self.cmb_workflow.itemData(i) == workflow_id:
                    self.cmb_workflow.setCurrentIndex(i)
                    break
        self.edit_desc.setPlainText(entry.get("description") or "")
        self.lbl_workspace.setText(entry.get("workspace_name") or "—")

        # existing attachments
        for att in self.db.list_attachments(self.entry_id):
            self._add_attachment_item(
                att["filename"],
                att_id=att["id"],
                file_path=att.get("file_path"),
                has_blob=bool(att.get("has_blob")),
            )

    def selected_user(self) -> str:
        """Return the analyst currently selected in the entry form."""
        return self.cmb_user.currentText().strip() if hasattr(self, "cmb_user") else ""

    # ------------------------------------------------------------------
    # Attachments helpers
    # ------------------------------------------------------------------
    def _attachment_dir(self) -> Path:
        """Folder where screenshot / attachment files are stored."""
        db_path = Path(self.db.db_path)
        folder = db_path.parent / "attachments" / str(self.project_id)
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def _add_attachment_item(
        self,
        filename: str,
        att_id: Optional[int] = None,
        file_path: Optional[str] = None,
        has_blob: bool = False,
        pixmap: Optional[QPixmap] = None,
    ) -> None:
        item = QListWidgetItem(filename)
        item.setData(Qt.ItemDataRole.UserRole, {"id": att_id, "path": file_path, "pending": att_id is None})
        if pixmap and not pixmap.isNull():
            item.setIcon(QIcon(pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))
        elif file_path and os.path.isfile(file_path):
            pix = QPixmap(file_path)
            if not pix.isNull():
                item.setIcon(QIcon(pix.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))
        tip = filename
        if has_blob:
            tip += " [BLOB]"
        if file_path:
            tip += f"\n{file_path}"
        item.setToolTip(tip)
        self.list_attachments.addItem(item)

    def _capture_canvas(self) -> None:
        canvas: QgsMapCanvas = self.iface.mapCanvas()
        if canvas is None:
            QMessageBox.warning(
                self, self.tr("Work Log"), self.tr("No map canvas available.")
            )
            return

        # Render current canvas content
        image = canvas.grab()  # QPixmap of the widget
        if image.isNull():
            # fallback via map settings
            settings = canvas.mapSettings()
            job = QgsMapRendererParallelJob(settings)
            job.start()
            job.waitForFinished()
            image = QPixmap.fromImage(job.renderedImage())

        if image.isNull():
            QMessageBox.warning(
                self, self.tr("Work Log"), self.tr("Could not capture map canvas.")
            )
            return

        # Save to disk
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"screenshot_{ts}.png"
        dest = self._attachment_dir() / filename
        if not image.save(str(dest), "PNG"):
            QMessageBox.warning(
                self, self.tr("Work Log"), self.tr("Failed to save screenshot file.")
            )
            return

        self._pending_files.append(str(dest))
        if self.chk_embed.isChecked():
            # read back for BLOB
            with open(dest, "rb") as f:
                data = f.read()
            self._pending_blobs.append((filename, data, "image/png"))

        self._add_attachment_item(filename, file_path=str(dest), pixmap=image)
        # auto-set category if still default
        if self.cmb_category.currentText() in ("Notes", "Other", ""):
            idx = self.cmb_category.findText("Screenshot")
            if idx >= 0:
                self.cmb_category.setCurrentIndex(idx)

    def _add_file(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("Add attachment(s)"),
            "",
            self.tr("Images (*.png *.jpg *.jpeg *.tif *.tiff *.gif *.webp);;All files (*.*)"),
        )
        for path in paths:
            if not os.path.isfile(path):
                continue
            filename = os.path.basename(path)
            # copy into attachment folder so the DB path stays stable
            dest = self._attachment_dir() / filename
            # avoid overwrite
            if dest.exists():
                stem = dest.stem
                suffix = dest.suffix
                i = 1
                while dest.exists():
                    dest = self._attachment_dir() / f"{stem}_{i}{suffix}"
                    i += 1
            try:
                shutil.copy2(path, dest)
            except Exception as e:
                QMessageBox.warning(
                    self,
                    self.tr("Work Log"),
                    self.tr("Could not copy file:\n{}").format(e),
                )
                continue

            self._pending_files.append(str(dest))
            if self.chk_embed.isChecked():
                with open(dest, "rb") as f:
                    data = f.read()
                from .db_manager import _guess_mime
                self._pending_blobs.append((dest.name, data, _guess_mime(dest.name)))

            pix = QPixmap(str(dest))
            self._add_attachment_item(
                dest.name, file_path=str(dest), pixmap=pix if not pix.isNull() else None
            )

    def _remove_selected_attachment(self) -> None:
        row = self.list_attachments.currentRow()
        if row < 0:
            return
        item = self.list_attachments.takeItem(row)
        data = item.data(Qt.ItemDataRole.UserRole) or {}
        if data.get("id") is not None:
            self._removed_attachment_ids.append(data["id"])
        elif data.get("path") in self._pending_files:
            path = data["path"]
            self._pending_files.remove(path)
            self._pending_blobs = [blob for blob in self._pending_blobs if blob[0] != Path(path).name]

    # ------------------------------------------------------------------
    def _save(self) -> None:
        user_name = self.cmb_user.currentText().strip()
        category = self.cmb_category.currentText().strip()
        if not category:
            QMessageBox.warning(
                self, self.tr("Work Log"), self.tr("Please choose or enter a category.")
            )
            self.cmb_category.setFocus()
            return

        timestamp = self.dt_timestamp.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        duration = self.spin_duration.value()
        if duration == 0:
            duration = None
        title = self.edit_title.text().strip()
        tags = self._normalise_tags(self.edit_tags.text())
        workflow_id = self.cmb_workflow.currentData()
        description = self.edit_desc.toPlainText().strip()
        workspace = self.lbl_workspace.text()
        if workspace == "—":
            workspace = None

        fields = {
            "category": category,
            "title": title,
            "description": description,
            "tags": tags,
            "workflow_id": workflow_id,
            "user_name": user_name,
            "duration_minutes": duration,
            "workspace_name": workspace,
            "timestamp": timestamp,
        }
        pending_blobs = {name: (data, mime) for name, data, mime in self._pending_blobs}
        attachments = []
        for path in dict.fromkeys(self._pending_files):
            filename = Path(path).name
            blob, mime = pending_blobs.get(filename, (None, None))
            attachments.append(dict(filename=filename, file_path=path, blob_data=blob, mime_type=mime))

        try:
            self.saved_entry_id = self.db.save_entry(
                self.project_id, self.entry_id, fields, self._removed_attachment_ids, attachments
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self,
                self.tr("Work Log"),
                self.tr("Failed to save entry:\n{}").format(e),
            )
