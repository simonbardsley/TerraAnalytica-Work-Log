"""Optional, local UI capabilities discoverable through TA Core.

No Core import is required to run Work Log. Discovery exposes actions only.
Callers receive no database paths, log contents or provider credentials.
"""
from . import __version__


class WorkLogIntegrations:
    def ta_capabilities(self):
        return {
            "worklog.open": self.open_worklog,
            "worklog.new_entry": self.new_entry,
            "worklog.reports": self.open_reports,
            "worklog.workflows": self.open_workflows,
        }

    def ta_plugin_descriptor(self):
        return {
            "id": "qgis_worklog",
            "title": "TA Work Log",
            "version": __version__,
            "capabilities": self.ta_capabilities(),
            "metadata": {"local_only": True, "exports_log_contents": False},
        }

    def open_worklog(self):
        """Open the panel without toggling an already-visible panel closed."""
        if self.dock is None:
            return False
        self.toggle_dock(True)
        self.dock.raise_()
        return True
