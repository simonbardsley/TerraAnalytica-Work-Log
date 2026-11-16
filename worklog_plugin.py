# -*- coding: utf-8 -*-
"""
Main plugin class for QGIS Work Log.
"""

from __future__ import annotations

import os
from pathlib import Path

from qgis.PyQt.QtCore import QCoreApplication, Qt, QTimer
from qgis.PyQt.QtGui import QIcon, QAction
from qgis.PyQt.QtWidgets import QMessageBox, QFileDialog, QInputDialog

from qgis.core import QgsProject, QgsApplication, QgsMessageLog, QgsSettings, Qgis
from qgis.gui import QgsGui

from .db_manager import WorkLogDB
from .dock_widget import WorkLogDockWidget
from .entry_dialog import EntryDialog
from .settings_dialog import SettingsDialog
from .reports_dialog import ReportsDialog
from .workflow_dialog import WorkflowManagerDialog
from .help_dialog import HelpDialog
from .branding import icon as ta_icon, watch_theme


class WorkLogPlugin:
    """QGIS plugin entry point."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = self.tr("&TerraAnalytica Work Log")
        self.toolbar = None
        self.dock = None
        self.db: WorkLogDB | None = None
        self.db_error: str | None = None
        self._current_project_id: int | None = None
        self._untitled_project_id: int | None = None
        self._current_project_name: str | None = None
        # Per-QGIS-session active analyst. A persistent default may be set in Settings.
        self._session_user: str = QgsSettings().value("worklog/default_user", "", type=str).strip()

    # ------------------------------------------------------------------
    def tr(self, message: str) -> str:
        return QCoreApplication.translate("WorkLogPlugin", message)

    def initGui(self) -> None:
        # Database
        try:
            self.db = WorkLogDB()
            self.db_error = None
            QgsMessageLog.logMessage(
                f"Work Log database: {self.db.db_path}",
                "Work Log",
                Qgis.MessageLevel.Info,
            )
        except Exception as e:
            self.db_error = str(e)
            QgsMessageLog.logMessage(
                f"Work Log: failed to open database – {e}",
                "Work Log",
                Qgis.MessageLevel.Critical,
            )
            self.db = None

        # Toolbar
        self.toolbar = self.iface.addToolBar("TA Work Log")
        self.toolbar.setObjectName("TerraAnalyticaWorkLogToolbar")

        icon = ta_icon("worklog", 24, self.iface.mainWindow())

        # Actions
        self.action_toggle_dock = QAction(
            icon, self.tr("Work Log Panel"), self.iface.mainWindow()
        )
        self.action_toggle_dock.setCheckable(True)
        self.action_toggle_dock.setToolTip(self.tr("Show / hide TerraAnalytica Work Log dock"))
        self.action_toggle_dock.triggered.connect(self.toggle_dock)
        self.toolbar.addAction(self.action_toggle_dock)
        self.iface.addPluginToMenu(self.menu, self.action_toggle_dock)
        self.actions.append(self.action_toggle_dock)

        self.action_new_entry = QAction(
            ta_icon("new"), self.tr("New Entry…"), self.iface.mainWindow()
        )
        self.action_new_entry.setToolTip(self.tr("Create a new log entry"))
        self.action_new_entry.triggered.connect(self.new_entry)
        self.toolbar.addAction(self.action_new_entry)
        self.iface.addPluginToMenu(self.menu, self.action_new_entry)
        self.actions.append(self.action_new_entry)

        self.action_session_user = QAction(
            self.tr("Set Session User…"), self.iface.mainWindow()
        )
        self.action_session_user.setToolTip(
            self.tr("Choose the analyst/user prefilled on new work-log entries for this QGIS session")
        )
        self.action_session_user.triggered.connect(self.choose_session_user)
        self.iface.addPluginToMenu(self.menu, self.action_session_user)
        self.actions.append(self.action_session_user)

        self.action_reports = QAction(
            ta_icon("reports"), self.tr("Reports…"), self.iface.mainWindow()
        )
        self.action_reports.setToolTip(
            self.tr("Summarise GIS and remote-sensing work by project, work class, time and tag")
        )
        self.action_reports.triggered.connect(self.open_reports)
        self.toolbar.addAction(self.action_reports)
        self.iface.addPluginToMenu(self.menu, self.action_reports)
        self.actions.append(self.action_reports)

        self.action_workflows = QAction(
            ta_icon("workflow"), self.tr("Workflows…"), self.iface.mainWindow()
        )
        self.action_workflows.setToolTip(
            self.tr("Record reproducible GIS and remote-sensing processing workflows")
        )
        self.action_workflows.triggered.connect(self.open_workflows)
        self.toolbar.addAction(self.action_workflows)
        self.iface.addPluginToMenu(self.menu, self.action_workflows)
        self.actions.append(self.action_workflows)

        self.action_help = QAction(
            ta_icon("help"), self.tr("Help & Use Cases…"), self.iface.mainWindow()
        )
        self.action_help.setToolTip(self.tr("Open the TerraAnalytica Work Log user guide and GIS/remote-sensing use cases"))
        self.action_help.triggered.connect(self.open_help)
        self.toolbar.addAction(self.action_help)
        self.iface.addPluginToMenu(self.menu, self.action_help)
        self.actions.append(self.action_help)

        self.action_demo_load = QAction(
            self.tr("Load / Reset Demo Data…"), self.iface.mainWindow()
        )
        self.action_demo_load.setToolTip(self.tr("Install realistic disposable GIS/remote-sensing template records and workflows"))
        self.action_demo_load.triggered.connect(self.load_demo_data)
        self.iface.addPluginToMenu(self.menu, self.action_demo_load)
        self.actions.append(self.action_demo_load)

        self.action_demo_remove = QAction(
            self.tr("Remove Demo Data…"), self.iface.mainWindow()
        )
        self.action_demo_remove.setToolTip(self.tr("Remove only projects explicitly marked as TerraAnalytica Work Log demo data"))
        self.action_demo_remove.triggered.connect(self.remove_demo_data)
        self.iface.addPluginToMenu(self.menu, self.action_demo_remove)
        self.actions.append(self.action_demo_remove)

        self.action_settings = QAction(
            ta_icon("settings"), self.tr("Settings…"), self.iface.mainWindow()
        )
        self.action_settings.setToolTip(self.tr("Work Log settings, report identity, database and defaults"))
        self.action_settings.triggered.connect(self.open_settings)
        self.iface.addPluginToMenu(self.menu, self.action_settings)
        self.actions.append(self.action_settings)

        # Keep toolbar/menu icons legible when QGIS switches between light and dark themes.
        watch_theme(self.iface.mainWindow(), self.refresh_action_icons)
        self.refresh_action_icons()

        # Dock
        self.dock = WorkLogDockWidget(self.iface, self)
        self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        self.dock.hide()
        self.dock.visibilityChanged.connect(self._on_dock_visibility)

        # React to project changes
        QgsProject.instance().readProject.connect(self._on_project_changed)
        QgsProject.instance().projectSaved.connect(self._on_project_changed)
        QgsProject.instance().cleared.connect(self._on_project_cleared)

        # Initial sync
        QTimer.singleShot(500, self._sync_current_project)

    def refresh_action_icons(self) -> None:
        """Refresh TA Gold + palette-aware action icons after a theme change."""
        host = self.iface.mainWindow()
        mapping = (
            (getattr(self, "action_toggle_dock", None), "worklog"),
            (getattr(self, "action_new_entry", None), "new"),
            (getattr(self, "action_reports", None), "reports"),
            (getattr(self, "action_workflows", None), "workflow"),
            (getattr(self, "action_help", None), "help"),
            (getattr(self, "action_settings", None), "settings"),
        )
        for action, icon_name in mapping:
            if action is not None:
                action.setIcon(ta_icon(icon_name, 24, host))

    def unload(self) -> None:
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)
        if self.toolbar:
            del self.toolbar
        if self.dock:
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None
        try:
            QgsProject.instance().readProject.disconnect(self._on_project_changed)
            QgsProject.instance().projectSaved.disconnect(self._on_project_changed)
            QgsProject.instance().cleared.disconnect(self._on_project_cleared)
        except Exception:
            pass

    def session_user(self) -> str:
        return self._session_user

    def set_session_user(self, name: str) -> None:
        """Set the analyst used as the default for new entries in this QGIS session."""
        self._session_user = (name or "").strip()
        if self.dock and hasattr(self.dock, "sync_session_user"):
            self.dock.sync_session_user()

    def choose_session_user(self) -> None:
        users = self.db.list_users() if self.db else []
        current = self._session_user
        index = users.index(current) if current in users else 0
        name, ok = QInputDialog.getItem(
            self.iface.mainWindow(),
            self.tr("Session user"),
            self.tr("Analyst/user for new Work Log entries in this QGIS session:"),
            users,
            index,
            editable=True,
        )
        if ok:
            self.set_session_user(name)

    # ------------------------------------------------------------------
    # Project linkage
    # ------------------------------------------------------------------
    def _on_project_changed(self, *args) -> None:
        self._sync_current_project()

    def _on_project_cleared(self) -> None:
        if self.db and self._untitled_project_id is not None:
            try:
                self.db.archive_untitled_project(self._untitled_project_id)
            except Exception as exc:
                QgsMessageLog.logMessage(
                    f"Work Log: could not archive Untitled entries – {exc}",
                    "Work Log",
                    Qgis.MessageLevel.Warning,
                )
        self._reset_project_link()
        # QGIS may still be clearing or loading the project in this signal.
        QTimer.singleShot(0, self._relink_after_project_clear)

    def _reset_project_link(self) -> None:
        self._untitled_project_id = None
        self._current_project_id = None
        self._current_project_name = None
        if self.dock:
            self.dock.set_project(None, None)

    def _relink_after_project_clear(self) -> None:
        if self.dock is not None and self._current_project_id is None:
            self._sync_current_project()

    def _sync_current_project(self) -> None:
        if not self.db:
            return
        proj = QgsProject.instance()
        path = proj.fileName()
        title = proj.title() or (Path(path).stem if path else "Untitled")

        # Prefer a meaningful name
        if path:
            name = Path(path).name if Path(path).stem == "Untitled" else Path(path).stem
            qgis_path = path
        else:
            name = title or "Untitled"
            qgis_path = None

        workspace = title or name

        try:
            pid = self.db.get_or_create_project(
                name=name,
                qgis_project_path=qgis_path,
                workspace_name=workspace,
            )
            self._untitled_project_id = pid if not path and name == "Untitled" else None
            self._current_project_id = pid
            self._current_project_name = name
            if self.dock:
                self.dock.set_project(pid, name)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Work Log: could not sync project – {e}", "Work Log", Qgis.MessageLevel.Warning
            )

    def current_project_id(self) -> int | None:
        return self._current_project_id

    def current_project_name(self) -> str | None:
        return self._current_project_name

    def override_project(self, name: str) -> None:
        """Manually switch / create a project by name (override auto-detect)."""
        if not self.db:
            return
        proj = QgsProject.instance()
        path = None if name in ("Untitled", "Untitled archive") else proj.fileName() or None
        workspace = proj.title() or name
        pid = self.db.get_or_create_project(
            name=name, qgis_project_path=path, workspace_name=workspace
        )
        self._current_project_id = pid
        self._current_project_name = name
        if self.dock:
            self.dock.set_project(pid, name)

    # ------------------------------------------------------------------
    # UI actions
    # ------------------------------------------------------------------
    def toggle_dock(self, checked: bool = None) -> None:
        if not self.dock:
            return
        if checked is None:
            checked = not self.dock.isVisible()
        self.dock.setVisible(checked)

    def _on_dock_visibility(self, visible: bool) -> None:
        self.action_toggle_dock.setChecked(visible)
        if visible and self._current_project_id is None:
            self._sync_current_project()
        elif visible and self.dock:
            self.dock.refresh()

    def _dialog_parent(self):
        if self.dock and self.dock.isFloating() and self.dock.isVisible():
            return self.dock
        return self.iface.mainWindow()

    def new_entry(self) -> None:
        if not self.db:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr("Work Log"),
                self.tr("Database is not available.\n\n{}").format(
                    self.db_error or self.tr("Unknown database error")
                ),
            )
            return
        if self._current_project_id is None:
            self._sync_current_project()
        if self._current_project_id is None:
            QMessageBox.information(
                self.iface.mainWindow(),
                self.tr("Work Log"),
                self.tr(
                    "No project is linked yet. Save your QGIS project or "
                    "choose a project name in the Work Log panel."
                ),
            )
            return

        dlg = EntryDialog(
            parent=self._dialog_parent(),
            db=self.db,
            project_id=self._current_project_id,
            project_name=self._current_project_name or "",
            iface=self.iface,
            default_user=self._session_user,
        )
        if dlg.exec():
            if dlg.selected_user():
                self.set_session_user(dlg.selected_user())
            if self.dock and self.dock.isVisible():
                self.dock.show_saved_entry(dlg.saved_entry_id)
            else:
                self.iface.messageBar().pushSuccess(self.tr("Work Log"), self.tr("Entry saved."))

    def open_reports(self) -> None:
        if not self.db:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr("TerraAnalytica Work Log"),
                self.tr("Database is not available.\n\n{}").format(
                    self.db_error or self.tr("Unknown database error")
                ),
            )
            return
        dlg = ReportsDialog(
            parent=self._dialog_parent(),
            db=self.db,
            current_project_id=self._current_project_id,
            current_project_name=self._current_project_name,
        )
        dlg.exec()

    def open_workflows(self) -> None:
        if not self.db:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr("TerraAnalytica Work Log"),
                self.tr("Database is not available.\n\n{}").format(
                    self.db_error or self.tr("Unknown database error")
                ),
            )
            return
        dlg = WorkflowManagerDialog(
            parent=self._dialog_parent(),
            db=self.db,
            current_project_id=self._current_project_id,
        )
        dlg.exec()
        if self.dock and self.dock.isVisible():
            self.dock.refresh()

    def open_help(self) -> None:
        dlg = HelpDialog(parent=self._dialog_parent(), plugin=self)
        dlg.exec()

    def load_demo_data(self) -> None:
        if not self.db:
            QMessageBox.warning(
                self.iface.mainWindow(), self.tr("TerraAnalytica Work Log"),
                self.tr("Database is not available.\n\n{}").format(self.db_error or self.tr("Unknown database error")),
            )
            return
        wording = (
            self.tr("This will create a disposable GIS/remote-sensing demo pack with recent work-log entries, ")
            + self.tr("three example workflows and final parameters.\n\n")
            + self.tr("If demo data is already installed it will be reset. Real projects are not changed.\n\nContinue?")
        )
        if QMessageBox.question(
            self.iface.mainWindow(), self.tr("Load Demo Data"), wording
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            result = self.db.install_demo_data()
            self.override_project("DEMO — Hauraki Pasture Remote Sensing")
            if self.dock:
                self.dock.refresh_categories()
                self.dock.refresh()
            QMessageBox.information(
                self.iface.mainWindow(), self.tr("Demo Data Ready"),
                self.tr(
                    "Demo data was created successfully.\n\n"
                    "Projects: {projects}\nEntries: {entries}\nWorkflows: {workflows}\n\n"
                    "The Work Log panel has been switched to the main demo project. Open Reports and Workflows to explore it."
                ).format(**result),
            )
        except Exception as e:
            QgsMessageLog.logMessage(f"Work Log demo-data error: {e}", "Work Log", Qgis.MessageLevel.Critical)
            QMessageBox.critical(
                self.iface.mainWindow(), self.tr("Demo Data Error"),
                self.tr("Could not create the demo data.\n\n{}").format(str(e)),
            )

    def remove_demo_data(self) -> None:
        if not self.db:
            return
        if not self.db.has_demo_data():
            QMessageBox.information(
                self.iface.mainWindow(), self.tr("Remove Demo Data"),
                self.tr("No TerraAnalytica Work Log demo projects are currently installed."),
            )
            return
        if QMessageBox.question(
            self.iface.mainWindow(), self.tr("Remove Demo Data"),
            self.tr("Remove all projects explicitly marked as demo data?\n\nYour real projects and records will not be changed.")
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            removed = self.db.remove_demo_data()
            self._current_project_id = None
            self._current_project_name = None
            self._sync_current_project()
            if self.dock:
                self.dock.refresh_categories()
                self.dock.refresh()
            QMessageBox.information(
                self.iface.mainWindow(), self.tr("Demo Data Removed"),
                self.tr("Removed {} demo project(s). Real project data was left untouched.").format(removed),
            )
        except Exception as e:
            QMessageBox.critical(
                self.iface.mainWindow(), self.tr("Demo Data Error"),
                self.tr("Could not remove the demo data.\n\n{}").format(str(e)),
            )

    def reopen_database(self, path: str) -> None:
        database = WorkLogDB(path)
        QgsSettings().setValue("worklog/db_path", database.db_path)
        self.db = database
        self.db_error = None
        if self.dock:
            self.dock.db = database

    def open_settings(self) -> None:
        previous_path = self.db.db_path if self.db else None
        dlg = SettingsDialog(
            parent=self._dialog_parent(),
            db=self.db,
            plugin=self,
        )
        dlg.exec()
        if self.db and self.db.db_path != previous_path:
            self._reset_project_link()
            self._sync_current_project()
        if self.dock:
            self.dock.refresh_categories()
            self.dock.refresh()
