import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
# Model tests use an explicit temporary DB and do not access QGIS settings.
if "qgis.core" not in sys.modules:
    core = types.ModuleType("qgis.core")
    core.QgsApplication = type("QgsApplication", (), {})
    core.QgsSettings = type("QgsSettings", (), {})
    sys.modules["qgis"] = types.ModuleType("qgis")
    sys.modules["qgis.core"] = core

spec = importlib.util.spec_from_file_location("worklog_db_test", ROOT / "db_manager.py")
db_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db_module)

package = types.ModuleType("worklog_release_test")
package.__path__ = [str(ROOT)]
package.__version__ = "test"
sys.modules[package.__name__] = package
spec = importlib.util.spec_from_file_location(
    "worklog_release_test.integrations", ROOT / "integrations.py"
)
integration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(integration)


class DatabaseSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = db_module.WorkLogDB(str(Path(self.temp.name) / "worklog.db"))
        self.project = self.db.get_or_create_project("Release")
        self.other = self.db.get_or_create_project("Other")
        self.entry = self.db.add_entry(
            self.project, "Notes", title="Native plant", tags="field,qa", user_name="Analyst",
            duration_minutes=10, timestamp="2026-11-22T23:59:59"
        )
        self.db.add_entry(self.other, "Notes", title="Other", timestamp="2026-11-23T10:00:00")

    def tearDown(self):
        self.temp.cleanup()

    def test_search_and_filters_with_and_without_fts(self):
        for enabled in (self.db.fts_enabled, False):
            self.db.fts_enabled = enabled
            with self.subTest(fts=enabled):
                rows = self.db.list_entries(self.project, category="Notes", tag="qa",
                                            search_text="plant", date_to="2026-11-22")
                self.assertEqual([row["id"] for row in rows], [self.entry])
                self.assertEqual(len(self.db.list_entries(self.project)), 1)
                self.assertEqual(self.db.list_entries(self.project, date_to="2026-11-21"), [])
                self.assertEqual(self.db.list_entries(self.project, category="' OR 1=1 --"), [])
                self.assertEqual(self.db.list_entries(self.project, limit=1, offset=1), [])

    def test_partial_updates_preserve_omitted_fields_and_support_null(self):
        self.db.update_entry(self.entry, title="'; DROP TABLE entries; --")
        row = self.db.get_entry(self.entry)
        self.assertEqual(row["duration_minutes"], 10)
        self.assertEqual(row["title"], "'; DROP TABLE entries; --")
        self.db.update_entry(self.entry, duration_minutes=None, user_name="")
        row = self.db.get_entry(self.entry)
        self.assertIsNone(row["duration_minutes"])
        self.assertIsNone(row["user_name"])

    def test_reports_and_workflows_remain_project_scoped(self):
        self.assertEqual(len(self.db.report_entries()), 2)
        self.assertEqual(len(self.db.report_entries(self.project, user_name="Analyst",
                                                  tag="qa", date_to="2026-11-22")), 1)
        self.assertEqual(self.db.report_entries(category="' OR 1=1 --"), [])
        workflow = self.db.create_workflow(self.project, "Field survey")
        self.assertEqual([w["id"] for w in self.db.list_workflows()], [workflow])
        self.assertEqual(self.db.list_workflows(self.other), [])


class CapabilityTests(unittest.TestCase):
    def test_optional_discovery_exposes_only_local_actions(self):
        class Host(integration.WorkLogIntegrations):
            dock = None

            def new_entry(self):
                return "editor"

            def open_reports(self):
                return "reports"

            def open_workflows(self):
                return "workflows"

        host = Host()
        descriptor = host.ta_plugin_descriptor()
        self.assertEqual(descriptor["id"], "qgis_worklog")
        self.assertFalse(descriptor["metadata"]["exports_log_contents"])
        self.assertEqual(host.ta_capabilities()["worklog.new_entry"](), "editor")
        self.assertFalse(host.open_worklog())
        self.assertEqual(set(descriptor["capabilities"]), {
            "worklog.open", "worklog.new_entry", "worklog.reports", "worklog.workflows"
        })


if __name__ == "__main__":
    unittest.main()
