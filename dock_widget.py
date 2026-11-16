# -*- coding: utf-8 -*-
"""
Dockable panel for quick viewing, searching and adding Work Log entries.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from qgis.PyQt.QtCore import Qt, QDate, QSize, pyqtSignal
from qgis.PyQt.QtGui import QFont, QColor, QBrush
from qgis.PyQt.QtWidgets import (
    QApplication,
    QDockWidget,
    QMenu,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView,
    QMessageBox,
    QInputDialog,
    QDateEdit,
    QToolButton,
    QFrame,
    QSizePolicy,
    QAbstractItemView,
)

from qgis.gui import QgsDockWidget
from qgis.core import Qgis, QgsMessageLog

from .entry_dialog import EntryDialog
from . import __version__
from .branding import (
    TA_CHARCOAL, TA_GOLD, icon as ta_icon, install_theme,
    muted_style, theme_colours,
)


class WorkLogDockWidget(QgsDockWidget):
    """Right-hand dock panel."""

    def __init__(self, iface, plugin, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.plugin = plugin
        self.db = plugin.db
        self.project_id: Optional[int] = None
        self.project_name: Optional[str] = None

        self.setObjectName("WorkLogDock")
        self.setWindowTitle(self.tr("Work Log"))
        self.setFeatures(self.features() | QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.topLevelChanged.connect(self._update_window_button)
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )

        self._return_dock_area = Qt.DockWidgetArea.RightDockWidgetArea
        self._build_ui()
        self._connect_signals()

    def tr(self, text: str) -> str:
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate("WorkLogDockWidget", text)

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        outer = QWidget()
        outer.setObjectName("TAWorkLogRoot")
        root = QVBoxLayout(outer)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Compact Layer Lab-style header ---
        self.header_widget = QWidget()
        self.header_widget.setObjectName("TAWorkLogHeader")
        header_layout = QVBoxLayout(self.header_widget)
        header_layout.setContentsMargins(12, 9, 10, 8)
        header_layout.setSpacing(5)

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.setSpacing(8)
        title_box = QWidget()
        title_box.setObjectName("TAWorkLogTitleBox")
        title_layout = QVBoxLayout(title_box)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(1)
        self.brand_label = QLabel("TERRAANALYTICA")
        self.brand_label.setObjectName("TAWorkLogBrand")
        title_layout.addWidget(self.brand_label)
        self.title_label = QLabel(self.tr("Work Log"))
        self.title_label.setObjectName("TAWorkLogTitle")
        title_layout.addWidget(self.title_label)
        subtitle_row = QHBoxLayout()
        subtitle_row.setContentsMargins(0, 0, 0, 0)
        subtitle_row.setSpacing(5)
        self.subtitle_label = QLabel(self.tr("Work diary · reporting · processing provenance"))
        self.subtitle_label.setObjectName("TAWorkLogSubtitle")
        subtitle_row.addWidget(self.subtitle_label)
        self.version_label = QLabel("v{}".format(__version__))
        self.version_label.setObjectName("TAWorkLogVersion")
        subtitle_row.addWidget(self.version_label)
        subtitle_row.addStretch()
        title_layout.addLayout(subtitle_row)
        brand_row.addWidget(title_box, 1)

        self.btn_help = QToolButton()
        self.btn_help.setObjectName("TAHeaderToolButton")
        self.btn_help.setText(self.tr("Help"))
        self.btn_help.setFixedHeight(28)
        self.btn_help.setToolTip(self.tr("Help and GIS / remote-sensing use cases"))
        self.btn_help.setAccessibleName(self.tr("Help and use cases"))
        brand_row.addWidget(self.btn_help)

        self.btn_settings = QToolButton()
        self.btn_settings.setObjectName("TAHeaderToolButton")
        self.btn_settings.setText(self.tr("Settings"))
        self.btn_settings.setFixedHeight(28)
        self.btn_settings.setToolTip(self.tr("Work Log settings, reporting identity and default user"))
        self.btn_settings.setAccessibleName(self.tr("Work Log settings"))
        brand_row.addWidget(self.btn_settings)
        header_layout.addLayout(brand_row)
        window_row = QHBoxLayout()
        self.btn_window = QToolButton()
        self.btn_window.setObjectName("TAHeaderToolButton")
        self._update_window_button(False)
        self.btn_window.clicked.connect(self._toggle_window)
        window_row.addWidget(self.btn_window)

        self.btn_monitors = QToolButton()
        self.btn_monitors.setObjectName("TAHeaderToolButton")
        self.btn_monitors.setText(self.tr("Move to monitor"))
        self.monitor_menu = QMenu(self.btn_monitors)
        self.monitor_menu.aboutToShow.connect(self._update_monitor_menu)
        self.btn_monitors.setMenu(self.monitor_menu)
        self.btn_monitors.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        window_row.addWidget(self.btn_monitors)
        window_row.addStretch()
        header_layout.addLayout(window_row)
        root.addWidget(self.header_widget)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 6)
        layout.setSpacing(5)

        # --- Project context ---
        proj_row = QHBoxLayout()
        self.lbl_project = QLabel(self.tr("No project"))
        font = self.lbl_project.font()
        font.setBold(True)
        self.lbl_project.setFont(font)
        self.lbl_project.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.lbl_project.setToolTip(self.tr("Current QGIS project linked to Work Log"))
        proj_row.addWidget(self.lbl_project)

        self.btn_switch = QToolButton()
        self.btn_switch.setFixedSize(28, 28)
        self.btn_switch.setIconSize(QSize(18, 18))
        self.btn_switch.setToolTip(self.tr("Override / choose another Work Log project"))
        self.btn_switch.setAccessibleName(self.tr("Switch project"))
        proj_row.addWidget(self.btn_switch)
        layout.addLayout(proj_row)

        # --- Session user / analyst ---
        user_row = QHBoxLayout()
        user_row.addWidget(QLabel(self.tr("User:")))
        self.cmb_session_user = QComboBox()
        self.cmb_session_user.setEditable(True)
        self.cmb_session_user.setToolTip(self.tr("Analyst/user prefilled on new Work Log entries for this QGIS session"))
        self.cmb_session_user.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        user_row.addWidget(self.cmb_session_user, 1)
        user_info = QToolButton()
        user_info.setText("ⓘ")
        user_info.setToolTip(self.tr("The session user is a convenience default. Each saved entry stores its own user/analyst value, so shared databases can report work by person."))
        user_info.clicked.connect(lambda: QMessageBox.information(
            self, self.tr("Session user"),
            self.tr("The selected user is prefilled on new entries for this QGIS session. You can change the user on any individual entry. Previously recorded users are offered in this list and reports can be filtered by user.")
        ))
        user_row.addWidget(user_info)
        layout.addLayout(user_row)

        # --- Search & filters ---
        filter_frame = QFrame()
        filter_frame.setObjectName("TAFilterCard")
        filter_frame.setFrameShape(QFrame.Shape.NoFrame)
        fl = QVBoxLayout(filter_frame)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(4)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("taSearchEdit")
        self.search_edit.setPlaceholderText(self.tr("Search entries or tags…"))
        self.search_edit.setClearButtonEnabled(True)
        fl.addWidget(self.search_edit)

        cat_row = QHBoxLayout()
        cat_row.addWidget(QLabel(self.tr("Work class:")))
        self.cmb_category = QComboBox()
        self.cmb_category.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        cat_row.addWidget(self.cmb_category)
        fl.addLayout(cat_row)

        tag_row = QHBoxLayout()
        tag_row.addWidget(QLabel(self.tr("Tag:")))
        self.cmb_tag = QComboBox()
        self.cmb_tag.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        tag_row.addWidget(self.cmb_tag)
        fl.addLayout(tag_row)

        date_row = QHBoxLayout()
        date_row.addWidget(QLabel(self.tr("From:")))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(QDate.currentDate().addMonths(-3))
        self.date_from.setSpecialValueText(self.tr("(any)"))
        date_row.addWidget(self.date_from)
        date_row.addWidget(QLabel(self.tr("To:")))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setSpecialValueText(self.tr("(any)"))
        date_row.addWidget(self.date_to)
        fl.addLayout(date_row)

        btn_row = QHBoxLayout()
        self.btn_search = QToolButton()
        self.btn_clear = QToolButton()
        for button in (self.btn_search, self.btn_clear):
            button.setFixedSize(28, 28)
            button.setIconSize(QSize(17, 17))
        self.btn_search.setToolTip(self.tr("Search using the current text and filters"))
        self.btn_search.setAccessibleName(self.tr("Search"))
        self.btn_clear.setToolTip(self.tr("Clear search text and filters"))
        self.btn_clear.setAccessibleName(self.tr("Clear filters"))
        btn_row.addWidget(self.btn_search)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch()
        fl.addLayout(btn_row)
        layout.addWidget(filter_frame)

        # --- Entry list ---
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([
            self.tr("When"), self.tr("Work class"), self.tr("Activity"), self.tr("Min"), self.tr("#")
        ])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(False)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setSortingEnabled(True)
        hdr = self.tree.header()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.tree, stretch=1)

        # --- Compact action toolbar ---
        action_row = QHBoxLayout()
        action_row.setSpacing(5)
        self.btn_new = QToolButton()
        self.btn_edit = QToolButton()
        self.btn_delete = QToolButton()
        self.btn_refresh = QToolButton()
        self.btn_reports = QToolButton()
        self.btn_workflows = QToolButton()
        for button in (self.btn_new, self.btn_edit, self.btn_delete, self.btn_refresh, self.btn_reports, self.btn_workflows):
            button.setFixedSize(30, 30)
            button.setIconSize(QSize(19, 19))
        self.btn_new.setToolTip(self.tr("New work-log entry")); self.btn_new.setAccessibleName(self.tr("New entry"))
        self.btn_edit.setToolTip(self.tr("Edit selected work-log entry")); self.btn_edit.setAccessibleName(self.tr("Edit entry"))
        self.btn_delete.setToolTip(self.tr("Delete selected work-log entry")); self.btn_delete.setAccessibleName(self.tr("Delete entry"))
        self.btn_refresh.setToolTip(self.tr("Refresh Work Log")); self.btn_refresh.setAccessibleName(self.tr("Refresh"))
        self.btn_reports.setToolTip(self.tr("Reports and exports")); self.btn_reports.setAccessibleName(self.tr("Reports"))
        self.btn_workflows.setToolTip(self.tr("GIS / remote-sensing workflows and processing provenance")); self.btn_workflows.setAccessibleName(self.tr("Workflows"))
        for button in (self.btn_new, self.btn_edit, self.btn_delete, self.btn_refresh, self.btn_reports, self.btn_workflows):
            action_row.addWidget(button)
        action_row.addStretch()
        layout.addLayout(action_row)

        root.addWidget(content, 1)

        # Compact Layer Lab-style status/footer.
        self.lbl_status = QLabel("")
        self.lbl_status.setContentsMargins(8, 3, 8, 6)
        root.addWidget(self.lbl_status)

        self.setWidget(outer)
        install_theme(outer, self._refresh_theme_assets)
        self.refresh_categories()
        self.sync_session_user()

    def _refresh_theme_assets(self) -> None:
        c = theme_colours(self)
        self.setStyleSheet(
            f"QDockWidget#WorkLogDock {{ border: 1px solid {TA_GOLD}; }}"
        )
        self.header_widget.setStyleSheet(
            f"""
            QWidget#TAWorkLogHeader, QWidget#TAWorkLogTitleBox {{
                background: {TA_CHARCOAL};
            }}
            QLabel#TAWorkLogBrand {{
                color: {TA_GOLD};
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1.3px;
                background: transparent;
            }}
            QLabel#TAWorkLogTitle {{
                color: #F5F5F5;
                font-size: 17px;
                font-weight: 700;
                background: transparent;
            }}
            QLabel#TAWorkLogSubtitle {{
                color: #B9BDC0;
                font-size: 10px;
                font-weight: 400;
                background: transparent;
            }}
            QLabel#TAWorkLogVersion {{
                color: #8F9498;
                font-size: 9px;
                font-weight: 400;
                background: transparent;
            }}
            QToolButton#TAHeaderToolButton {{
                color: #F5F5F5;
                background: transparent;
                border: 1px solid #62676B;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 650;
            }}
            QToolButton#TAHeaderToolButton:hover {{
                border-color: {TA_GOLD};
                background: rgba(232, 168, 56, 36);
            }}
            QToolButton#TAHeaderToolButton:pressed {{
                background: rgba(232, 168, 56, 64);
            }}
            """
        )
        self.tree.setStyleSheet(
            f"QTreeWidget {{ border: none; background: transparent; }} "
            f"QTreeWidget::item:selected {{ background: {c['gold_pressed']}; color: {c['text']}; }}"
        )
        self.lbl_status.setStyleSheet(
            f"color: {c['muted']}; font-size: 9px;"
        )
        self.btn_switch.setIcon(ta_icon("switch", 18, self))
        self.btn_search.setIcon(ta_icon("search", 17, self))
        self.btn_clear.setIcon(ta_icon("clear", 17, self))
        self.btn_new.setIcon(ta_icon("new", 19, self))
        self.btn_edit.setIcon(ta_icon("edit", 19, self))
        self.btn_delete.setIcon(ta_icon("delete", 19, self))
        self.btn_refresh.setIcon(ta_icon("refresh", 19, self))
        self.btn_reports.setIcon(ta_icon("reports", 19, self))
        self.btn_workflows.setIcon(ta_icon("workflow", 19, self))
        if hasattr(self.plugin, "refresh_action_icons"):
            self.plugin.refresh_action_icons()

    def _update_window_button(self, floating: bool) -> None:
        self.btn_window.setText(self.tr("Dock in QGIS") if floating else self.tr("Pop out"))

    def _toggle_window(self) -> None:
        if self.isFloating():
            self.setFloating(False)
            self.iface.addDockWidget(self._return_dock_area, self)
            self.show()
            self.raise_()
        else:
            self._pop_out_window()

    def _update_monitor_menu(self) -> None:
        self.monitor_menu.clear()
        for number, screen in enumerate(QApplication.screens(), start=1):
            label = self.tr("Monitor {}").format(number)
            name = screen.name().strip()
            if name:
                label = "{} — {}".format(label, name)
            self.monitor_menu.addAction(
                label, lambda checked=False, target=screen: self._move_to_screen(target)
            )

    def _pop_out_window(self) -> None:
        if not self.isFloating():
            area = self.iface.mainWindow().dockWidgetArea(self)
            if area != Qt.DockWidgetArea.NoDockWidgetArea:
                self._return_dock_area = area
            self.setFloating(True)
        if self.windowType() != Qt.WindowType.Window:
            self.setWindowFlags(
                Qt.WindowType.Window
                | Qt.WindowType.WindowTitleHint
                | Qt.WindowType.WindowSystemMenuHint
                | Qt.WindowType.WindowMinMaxButtonsHint
                | Qt.WindowType.WindowCloseButtonHint
            )
        self.show()
        self.raise_()
        self.activateWindow()

    def _move_to_screen(self, screen) -> None:
        if screen not in QApplication.screens():
            return

        self._pop_out_window()
        self.showNormal()
        handle = self.windowHandle()
        if handle is not None and handle.screen() != screen:
            handle.setScreen(screen)
        area = screen.availableGeometry()
        frame = self.frameGeometry()
        frame_width = frame.width() - self.width()
        frame_height = frame.height() - self.height()
        self.resize(
            min(self.width(), max(1, area.width() - frame_width)),
            min(self.height(), max(1, area.height() - frame_height)),
        )
        self.move(
            area.x() + max(0, (area.width() - self.frameGeometry().width()) // 2),
            area.y() + max(0, (area.height() - self.frameGeometry().height()) // 2),
        )

    def _connect_signals(self) -> None:
        self.btn_switch.clicked.connect(self._switch_project)
        self.btn_settings.clicked.connect(self.plugin.open_settings)
        self.btn_help.clicked.connect(self._show_help)
        self.cmb_session_user.currentIndexChanged.connect(self._session_user_changed)
        if self.cmb_session_user.lineEdit():
            self.cmb_session_user.lineEdit().editingFinished.connect(self._session_user_changed)
        self.btn_search.clicked.connect(self.refresh)
        self.btn_clear.clicked.connect(self._clear_filters)
        self.search_edit.returnPressed.connect(self.refresh)
        self.btn_new.clicked.connect(self._new_entry)
        self.btn_edit.clicked.connect(self._edit_entry)
        self.btn_delete.clicked.connect(self._delete_entry)
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_reports.clicked.connect(self.plugin.open_reports)
        self.btn_workflows.clicked.connect(self.plugin.open_workflows)
        self.tree.itemDoubleClicked.connect(self._edit_entry)

    # ------------------------------------------------------------------
    def sync_session_user(self) -> None:
        if not hasattr(self, "cmb_session_user"):
            return
        current = self.plugin.session_user() if hasattr(self.plugin, "session_user") else ""
        self.cmb_session_user.blockSignals(True)
        self.cmb_session_user.clear()
        self.cmb_session_user.addItem("")
        if self.db:
            for user in self.db.list_users():
                self.cmb_session_user.addItem(user)
        idx = self.cmb_session_user.findText(current)
        if idx >= 0:
            self.cmb_session_user.setCurrentIndex(idx)
        else:
            self.cmb_session_user.setEditText(current)
        self.cmb_session_user.blockSignals(False)

    def _session_user_changed(self, *args) -> None:
        if hasattr(self.plugin, "set_session_user"):
            self.plugin.set_session_user(self.cmb_session_user.currentText().strip())

    def set_project(self, project_id: Optional[int], name: Optional[str]) -> None:
        self.project_id = project_id
        self.project_name = name
        if name:
            self.lbl_project.setText(self.tr("Project: {}").format(name))
        else:
            self.lbl_project.setText(self.tr("No project linked"))
        self.refresh_tags()
        self.refresh()

    def refresh_categories(self) -> None:
        self.cmb_category.blockSignals(True)
        self.cmb_category.clear()
        self.cmb_category.addItem(self.tr("(all)"), None)
        if self.db:
            for cat in self.db.list_categories():
                self.cmb_category.addItem(cat, cat)
        self.cmb_category.blockSignals(False)
        self.refresh_tags()

    def refresh_tags(self) -> None:
        if not hasattr(self, "cmb_tag"):
            return
        current = self.cmb_tag.currentData() if self.cmb_tag.count() else None
        self.cmb_tag.blockSignals(True)
        self.cmb_tag.clear()
        self.cmb_tag.addItem(self.tr("(all)"), None)
        if self.db:
            for tag in self.db.list_tags(project_id=self.project_id):
                self.cmb_tag.addItem(tag, tag)
        if current:
            idx = self.cmb_tag.findData(current)
            if idx >= 0:
                self.cmb_tag.setCurrentIndex(idx)
        self.cmb_tag.blockSignals(False)

    def refresh(self) -> None:
        self.refresh_tags()
        self.sync_session_user()
        self.tree.clear()
        if not self.db or self.project_id is None:
            self.lbl_status.setText(self.tr("No project selected."))
            return

        cat = self.cmb_category.currentData()
        tag = self.cmb_tag.currentData()
        text = self.search_edit.text().strip() or None
        from_date = self.date_from.date()
        to_date = self.date_to.date()
        d_from = None if from_date == self.date_from.minimumDate() else from_date.toString("yyyy-MM-dd")
        d_to = None if to_date == self.date_to.minimumDate() else to_date.toString("yyyy-MM-dd")

        try:
            entries = self.db.list_entries(
                project_id=self.project_id,
                category=cat,
                tag=tag,
                search_text=text,
                date_from=d_from,
                date_to=d_to,
                limit=500,
            )
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Work Log search error: {e}", "Work Log", Qgis.MessageLevel.Warning
            )
            self.lbl_status.setText(self.tr("Search error – see log."))
            return

        for e in entries:
            title = e.get("title") or ""
            desc = (e.get("description") or "").replace("\n", " ")
            if len(desc) > 80:
                desc = desc[:77] + "…"
            display = title if title else desc
            if title and desc:
                display = f"{title} — {desc}"

            when = e.get("timestamp") or ""
            # show just date+time nicely
            if len(when) >= 16:
                when = when[:16]

            item = QTreeWidgetItem(
                [
                    when,
                    e.get("category") or "",
                    display,
                    str(e["duration_minutes"]) if e.get("duration_minutes") is not None else "",
                    str(e.get("attachment_count") or 0),
                ]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, e["id"])
            tip = e.get("description") or ""
            if e.get("tags"):
                tip += ("\n\n" if tip else "") + self.tr("Tags: ") + (e.get("tags") or "").replace(",", ", ")
            item.setToolTip(2, tip)
            self.tree.addTopLevelItem(item)

        total = self.db.entry_count(self.project_id)
        mins = self.db.total_duration_minutes(self.project_id)
        hours = mins / 60.0
        self.lbl_status.setText(
            self.tr("{} shown / {} total  ·  {:.1f} h logged").format(
                len(entries), total, hours
            )
        )

    def show_saved_entry(self, entry_id: int) -> None:
        self.refresh()
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            if item.data(0, Qt.ItemDataRole.UserRole) == entry_id:
                self.tree.setCurrentItem(item)
                self.tree.scrollToItem(item)
                self.lbl_status.setText(self.tr("Entry saved. ") + self.lbl_status.text())
                return
        self.lbl_status.setText(self.tr("Entry saved. Check the search and date filters to show it."))

    def _clear_filters(self) -> None:
        self.search_edit.clear()
        self.cmb_category.setCurrentIndex(0)
        self.cmb_tag.setCurrentIndex(0)
        self.date_from.setDate(self.date_from.minimumDate())
        self.date_to.setDate(self.date_to.minimumDate())
        self.refresh()

    def _show_help(self) -> None:
        self.plugin.open_help()

    def _switch_project(self) -> None:
        if not self.db:
            return
        projects = self.db.list_projects()
        names = [p["name"] for p in projects]
        current = self.project_name or ""
        name, ok = QInputDialog.getItem(
            self,
            self.tr("Switch project"),
            self.tr(
                "Select an existing project or type a new name:\n"
                "(This overrides the auto-detected QGIS project name.)"
            ),
            names,
            max(0, names.index(current) if current in names else 0),
            editable=True,
        )
        if ok and name.strip():
            self.plugin.override_project(name.strip())

    def _selected_entry_id(self) -> Optional[int]:
        items = self.tree.selectedItems()
        if not items:
            return None
        return items[0].data(0, Qt.ItemDataRole.UserRole)

    def _new_entry(self) -> None:
        self.plugin.new_entry()

    def _edit_entry(self) -> None:
        eid = self._selected_entry_id()
        if eid is None:
            QMessageBox.information(
                self, self.tr("Work Log"), self.tr("Select an entry first.")
            )
            return
        dlg = EntryDialog(
            parent=self,
            db=self.db,
            project_id=self.project_id,
            project_name=self.project_name or "",
            iface=self.iface,
            entry_id=eid,
            default_user=self.plugin.session_user() if hasattr(self.plugin, "session_user") else "",
        )
        if dlg.exec():
            self.show_saved_entry(dlg.saved_entry_id)

    def _delete_entry(self) -> None:
        eid = self._selected_entry_id()
        if eid is None:
            QMessageBox.information(
                self, self.tr("Work Log"), self.tr("Select an entry first.")
            )
            return
        reply = QMessageBox.question(
            self,
            self.tr("Delete entry"),
            self.tr("Permanently delete this log entry and its attachments?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_entry(eid)
                self.refresh()
            except Exception as e:
                QMessageBox.warning(
                    self, self.tr("Work Log"), self.tr("Could not delete: {}").format(e)
                )
