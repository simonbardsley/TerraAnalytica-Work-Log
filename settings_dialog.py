# -*- coding: utf-8 -*-
"""
Settings dialog – database path, categories, project management.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from qgis.PyQt.QtCore import Qt
from qgis.core import QgsSettings
from .backup import create_backup, restore_backup
from .branding import brand_label_style, install_theme, muted_style, title_style

from qgis.PyQt.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QDialogButtonBox,
    QInputDialog,
    QTabWidget,
    QWidget,
)


class SettingsDialog(QDialog):
    def __init__(self, parent, db, plugin):
        super().__init__(parent)
        self.db = db
        self.plugin = plugin
        self.setWindowTitle(self.tr("TA Work Log — Settings"))
        self.resize(480, 420)
        self._build_ui()
        install_theme(self, self._refresh_theme_assets)
        self._load()

    def tr(self, text: str) -> str:
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate("SettingsDialog", text)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        brand_box = QWidget()
        brand_layout = QVBoxLayout(brand_box)
        brand_layout.setContentsMargins(0, 0, 0, 4)
        brand_layout.setSpacing(0)
        self.brand_label = QLabel("TERRAANALYTICA")
        self.brand_label.setStyleSheet(brand_label_style())
        brand_layout.addWidget(self.brand_label)
        self.title_label = QLabel(self.tr("Work Log Settings"))
        brand_layout.addWidget(self.title_label)
        layout.addWidget(brand_box)

        tabs = QTabWidget()

        # ---- Database tab ----
        db_page = QWidget()
        db_layout = QVBoxLayout(db_page)

        form = QFormLayout()
        path_row = QHBoxLayout()
        self.edit_db_path = QLineEdit()
        self.edit_db_path.setReadOnly(True)
        path_row.addWidget(self.edit_db_path)
        self.btn_browse_db = QPushButton(self.tr("Browse…"))
        path_row.addWidget(self.btn_browse_db)
        form.addRow(self.tr("Database file:"), path_row)
        db_layout.addLayout(form)

        hint = QLabel(
            self.tr(
                "One shared SQLite database holds all projects.\n"
                "Default location is inside your QGIS profile folder.\n"
                "Attachments are stored in an “attachments” sub-folder next to the DB."
            )
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(muted_style(self, 11))
        db_layout.addWidget(hint)

        backup_row = QHBoxLayout()
        self.btn_backup = QPushButton(self.tr("Create backup…"))
        self.btn_backup.setEnabled(self.db is not None)
        self.btn_restore = QPushButton(self.tr("Restore backup…"))
        backup_row.addWidget(self.btn_backup)
        backup_row.addWidget(self.btn_restore)
        backup_row.addStretch()
        db_layout.addLayout(backup_row)

        backup_hint = QLabel(self.tr(
            "Back up the database and attachments to one ZIP. Restore creates a separate copy."
        ))
        backup_hint.setWordWrap(True)
        db_layout.addWidget(backup_hint)
        db_layout.addStretch()
        tabs.addTab(db_page, self.tr("Database"))

        # ---- Categories tab ----
        cat_page = QWidget()
        cat_layout = QVBoxLayout(cat_page)
        self.list_categories = QListWidget()
        cat_layout.addWidget(self.list_categories)
        cat_btn = QHBoxLayout()
        self.btn_add_cat = QPushButton(self.tr("Add…"))
        self.btn_remove_cat = QPushButton(self.tr("Remove"))
        cat_btn.addWidget(self.btn_add_cat)
        cat_btn.addWidget(self.btn_remove_cat)
        cat_btn.addStretch()
        cat_layout.addLayout(cat_btn)
        cat_hint = QLabel(
            self.tr(
                "Work classes are broad GIS/remote-sensing activity types used in reports. "
                "Use Tags on individual entries for sensors, datasets, software and methods."
            )
        )
        cat_hint.setWordWrap(True)
        cat_hint.setStyleSheet(muted_style(self, 11))
        cat_layout.addWidget(cat_hint)
        tabs.addTab(cat_page, self.tr("Work Classes"))

        # ---- Projects tab ----
        proj_page = QWidget()
        proj_layout = QVBoxLayout(proj_page)
        self.list_projects = QListWidget()
        proj_layout.addWidget(self.list_projects)
        proj_btn = QHBoxLayout()
        self.btn_rename_proj = QPushButton(self.tr("Rename…"))
        self.btn_delete_proj = QPushButton(self.tr("Delete project…"))
        proj_btn.addWidget(self.btn_rename_proj)
        proj_btn.addWidget(self.btn_delete_proj)
        proj_btn.addStretch()
        proj_layout.addLayout(proj_btn)
        hint2 = QLabel(
            self.tr(
                "Deleting a project permanently removes all its log entries "
                "and attachment records."
            )
        )
        hint2.setWordWrap(True)
        hint2.setStyleSheet(muted_style(self, 11))
        proj_layout.addWidget(hint2)
        tabs.addTab(proj_page, self.tr("Projects"))

        # ---- Reporting / user defaults tab ----
        rep_page = QWidget()
        rep_layout = QVBoxLayout(rep_page)
        rep_form = QFormLayout()
        self.edit_report_heading = QLineEdit()
        self.edit_report_heading.setPlaceholderText(self.tr("Optional, e.g. My GIS Team or Acme Spatial"))
        rep_form.addRow(self.tr("Report organisation / heading:"), self.edit_report_heading)
        self.edit_default_user = QLineEdit()
        self.edit_default_user.setPlaceholderText(self.tr("Optional default analyst/user"))
        rep_form.addRow(self.tr("Default user / analyst:"), self.edit_default_user)
        rep_layout.addLayout(rep_form)
        rep_hint = QLabel(self.tr(
            "The plugin remains branded TA Work Log, but exported PDF reports are generic by default. "
            "If you set a report organisation/heading it is used in Work Log and Workflow report titles. "
            "The default user starts each QGIS session; the user can still be changed per entry or for the active session."
        ))
        rep_hint.setWordWrap(True)
        rep_hint.setStyleSheet(muted_style(self, 11))
        rep_layout.addWidget(rep_hint)
        rep_layout.addStretch()
        tabs.addTab(rep_page, self.tr("Reporting & User"))

        layout.addWidget(tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        layout.addWidget(buttons)

        # Signals
        self.btn_browse_db.clicked.connect(self._browse_db)
        self.btn_backup.clicked.connect(self._create_backup)
        self.btn_restore.clicked.connect(self._restore_backup)
        self.btn_add_cat.clicked.connect(self._add_category)
        self.btn_remove_cat.clicked.connect(self._remove_category)
        self.btn_rename_proj.clicked.connect(self._rename_project)
        self.btn_delete_proj.clicked.connect(self._delete_project)

    def _refresh_theme_assets(self) -> None:
        self.brand_label.setStyleSheet(brand_label_style())
        self.title_label.setStyleSheet(title_style(self, 17))

    def _load(self) -> None:
        settings = QgsSettings()
        self.edit_report_heading.setText(settings.value("worklog/report_heading", "", type=str))
        self.edit_default_user.setText(settings.value("worklog/default_user", "", type=str))
        if self.db:
            self.edit_db_path.setText(self.db.db_path)
            self._reload_categories()
            self._reload_projects()

    def accept(self) -> None:
        settings = QgsSettings()
        settings.setValue("worklog/report_heading", self.edit_report_heading.text().strip())
        settings.setValue("worklog/default_user", self.edit_default_user.text().strip())
        if self.plugin and not self.plugin.session_user() and self.edit_default_user.text().strip():
            self.plugin.set_session_user(self.edit_default_user.text().strip())
        super().accept()

    def _reload_categories(self) -> None:
        self.list_categories.clear()
        for cat in self.db.list_categories():
            self.list_categories.addItem(cat)

    def _reload_projects(self) -> None:
        self.list_projects.clear()
        for p in self.db.list_projects():
            item = QListWidgetItem(
                f"{p['name']}  ({p.get('entry_count', 0)} entries)"
            )
            item.setData(Qt.ItemDataRole.UserRole, p["id"])
            item.setToolTip(
                f"Path: {p.get('qgis_project_path') or '—'}\n"
                f"Workspace: {p.get('workspace_name') or '—'}"
            )
            self.list_projects.addItem(item)

    def _browse_db(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Select or create Work Log database"),
            self.edit_db_path.text() or str(Path.home()),
            self.tr("SQLite database (*.db *.sqlite);;All files (*.*)"),
        )
        if not path:
            return
        if not path.lower().endswith((".db", ".sqlite", ".sqlite3")):
            path += ".db"
        try:
            self._open_database(path)
            QMessageBox.information(
                self,
                self.tr("TA Work Log"),
                self.tr("Database location updated.\n{}").format(path),
            )
        except Exception as e:
            QMessageBox.critical(
                self, self.tr("TA Work Log"), self.tr("Could not open database:\n{}").format(e)
            )

    def _open_database(self, path: str) -> None:
        if self.db is None:
            self.plugin.reopen_database(path)
            self.db = self.plugin.db
        else:
            self.db.set_db_path(path)
        self.edit_db_path.setText(self.db.db_path)
        self.btn_backup.setEnabled(True)
        self._reload_categories()
        self._reload_projects()

    def _create_backup(self) -> None:
        if self.db is None:
            return
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        destination, _ = QFileDialog.getSaveFileName(
            self, self.tr("Create Work Log backup"),
            str(Path.home() / f"worklog-backup-{timestamp}.zip"),
            self.tr("Work Log backups (*.zip)"),
        )
        if not destination:
            return
        if not destination.lower().endswith(".zip"):
            destination += ".zip"
        title = self.tr("Work Log backup")
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                missing = create_backup(self.db.db_path, destination)
            finally:
                QApplication.restoreOverrideCursor()
        except Exception as exc:
            QMessageBox.warning(self, title, self.tr("Could not create backup:\n{}").format(exc))
            return
        message = self.tr("Backup saved to:\n{}").format(destination)
        if missing:
            message += "\n\n" + self.tr(
                "{} attachment records had no available file or embedded copy."
            ).format(missing)
            QMessageBox.warning(self, title, message)
        else:
            QMessageBox.information(self, title, message)

    def _restore_backup(self) -> None:
        backup, _ = QFileDialog.getOpenFileName(
            self, self.tr("Select a Work Log backup"), str(Path.home()),
            self.tr("Work Log backups (*.zip)"),
        )
        if not backup:
            return
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Choose a folder for the restored copy"), str(Path(backup).parent)
        )
        if not folder:
            return
        title = self.tr("Restore Work Log backup")
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                restored = restore_backup(backup, folder)
            finally:
                QApplication.restoreOverrideCursor()
        except Exception as exc:
            QMessageBox.warning(self, title, self.tr("Could not restore backup:\n{}").format(exc))
            return

        reply = QMessageBox.question(
            self, title,
            self.tr("Restored a separate copy to:\n{}\n\nOpen this copy in Work Log now?").format(restored),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._open_database(str(restored))
            except Exception as exc:
                QMessageBox.warning(
                    self, title, self.tr("The backup was restored, but the copy could not be opened:\n{}").format(exc)
                )

    def _add_category(self) -> None:
        name, ok = QInputDialog.getText(
            self, self.tr("Add work class"), self.tr("Work class name:")
        )
        if ok and name.strip():
            self.db.add_category(name.strip())
            self._reload_categories()

    def _remove_category(self) -> None:
        item = self.list_categories.currentItem()
        if not item:
            return
        name = item.text()
        reply = QMessageBox.question(
            self,
            self.tr("Remove work class"),
            self.tr(
                "Remove category “{}”?\n"
                "Existing entries that use it are not changed."
            ).format(name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.remove_category(name)
            self._reload_categories()

    def _rename_project(self) -> None:
        item = self.list_projects.currentItem()
        if not item:
            return
        pid = item.data(Qt.ItemDataRole.UserRole)
        old_name = item.text().split("  (")[0]
        new_name, ok = QInputDialog.getText(
            self,
            self.tr("Rename project"),
            self.tr("New name:"),
            text=old_name,
        )
        if ok and new_name.strip() and new_name.strip() != old_name:
            try:
                self.db.rename_project(pid, new_name.strip())
                self._reload_projects()
                # if this is the active project, update plugin state
                if self.plugin.current_project_id() == pid:
                    self.plugin.override_project(new_name.strip())
            except Exception as e:
                QMessageBox.warning(
                    self, self.tr("TA Work Log"), self.tr("Rename failed:\n{}").format(e)
                )

    def _delete_project(self) -> None:
        item = self.list_projects.currentItem()
        if not item:
            return
        pid = item.data(Qt.ItemDataRole.UserRole)
        name = item.text().split("  (")[0]
        reply = QMessageBox.warning(
            self,
            self.tr("Delete project"),
            self.tr(
                "Permanently delete project “{}” and ALL its log entries?\n"
                "This cannot be undone."
            ).format(name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_project(pid)
            self._reload_projects()
            if self.plugin.current_project_id() == pid:
                self.plugin._reset_project_link()
                self.plugin._sync_current_project()
