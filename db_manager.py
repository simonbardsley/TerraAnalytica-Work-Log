# -*- coding: utf-8 -*-
"""
SQLite database manager for the Work Log plugin.
One shared database holding multiple projects and their entries.
"""

from __future__ import annotations

import os
import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from qgis.core import QgsApplication, QgsSettings

# Default categories – user can extend via settings / UI later
DEFAULT_CATEGORIES = [
    "Notes",
    "GIS / Spatial Analysis",
    "Remote Sensing",
    "Processing",
    "Mapping / Cartography",
    "Fieldwork / Ground Truth",
    "Coding / Automation",
    "QA / QC",
    "Research / Literature",
    "Documentation / Reporting",
    "Meeting / Client",
    "Screenshot",
    "Bug / Issue",
    "Other",
]

SCHEMA_VERSION = 5
_UNSET = object()


class WorkLogDB:
    """Manages the shared SQLite work-log database."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self._default_db_path()
        self.fts_enabled = False
        self._ensure_parent_dir()
        self._init_schema()

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _default_db_path() -> str:
        """Prefer a stable location inside the current QGIS profile."""
        settings = QgsSettings()
        custom = settings.value("worklog/db_path", "", type=str)
        if custom:
            # Honour the configured path even if the DB does not exist yet;
            # SQLite will create it. This also avoids silently abandoning a
            # user-selected location after a profile/QGIS upgrade.
            return os.path.abspath(os.path.expanduser(custom))

        # profile folder → worklog/worklog.db
        profile = QgsApplication.qgisSettingsDirPath()
        if not profile:
            # Defensive fallback for unusual/portable QGIS profiles.
            user_db = QgsApplication.qgisUserDatabaseFilePath()
            profile = os.path.dirname(user_db) if user_db else str(Path.home())
        return os.path.join(profile, "worklog", "worklog.db")

    def _ensure_parent_dir(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def set_db_path(self, path: str) -> None:
        """Change database location and re-initialise."""
        candidate = WorkLogDB(path)
        QgsSettings().setValue("worklog/db_path", candidate.db_path)
        self.db_path = candidate.db_path
        self.fts_enabled = candidate.fts_enabled

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    @contextmanager
    def _conn(self, connection=None):
        if connection is not None:
            yield connection
            return
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                );

                CREATE TABLE IF NOT EXISTS projects (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    name              TEXT NOT NULL,
                    qgis_project_path TEXT,
                    workspace_name    TEXT,
                    notes             TEXT,
                    is_demo           INTEGER NOT NULL DEFAULT 0,
                    created_at        TEXT NOT NULL,
                    updated_at        TEXT NOT NULL,
                    UNIQUE(name)
                );

                CREATE TABLE IF NOT EXISTS categories (
                    id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS workflows (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id        INTEGER NOT NULL,
                    name              TEXT NOT NULL,
                    purpose           TEXT,
                    version           TEXT NOT NULL DEFAULT '1.0',
                    status            TEXT NOT NULL DEFAULT 'Draft',
                    notes             TEXT,
                    qgis_version      TEXT,
                    platform          TEXT,
                    finalised_at      TEXT,
                    created_at        TEXT NOT NULL,
                    updated_at        TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS workflow_steps (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id       INTEGER NOT NULL,
                    step_order        INTEGER NOT NULL,
                    step_type         TEXT NOT NULL DEFAULT 'Manual',
                    title             TEXT NOT NULL,
                    description       TEXT,
                    algorithm_id      TEXT,
                    parameters_json   TEXT,
                    python_command    TEXT,
                    process_command   TEXT,
                    execution_log     TEXT,
                    source_history_id INTEGER,
                    source_timestamp  TEXT,
                    created_at        TEXT NOT NULL,
                    updated_at        TEXT NOT NULL,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS workflow_parameters (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id       INTEGER NOT NULL,
                    name              TEXT NOT NULL,
                    value             TEXT,
                    unit              TEXT,
                    notes             TEXT,
                    sort_order        INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS workflow_artifacts (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id       INTEGER NOT NULL,
                    kind              TEXT NOT NULL,
                    label             TEXT NOT NULL,
                    path_uri          TEXT,
                    notes             TEXT,
                    sort_order        INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS entries (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id      INTEGER NOT NULL,
                    timestamp       TEXT NOT NULL,          -- when the work happened
                    category        TEXT NOT NULL,
                    user_name       TEXT,                   -- analyst/person who performed the work
                    duration_minutes INTEGER,               -- optional time spent
                    title           TEXT,
                    description     TEXT,
                    tags            TEXT,                   -- comma-separated descriptive tags
                    workflow_id     INTEGER,                -- optional reproducible workflow link
                    workspace_name  TEXT,                   -- QGIS workspace / project title at time of entry
                    created_at      TEXT NOT NULL,
                    updated_at      TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS attachments (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id    INTEGER NOT NULL,
                    filename    TEXT NOT NULL,
                    file_path   TEXT,                       -- on-disk path (preferred)
                    blob_data   BLOB,                       -- optional embedded image
                    mime_type   TEXT,
                    size_bytes  INTEGER,
                    created_at  TEXT NOT NULL,
                    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_entries_project
                    ON entries(project_id);
                CREATE INDEX IF NOT EXISTS idx_entries_timestamp
                    ON entries(timestamp);
                CREATE INDEX IF NOT EXISTS idx_entries_category
                    ON entries(category);
                CREATE INDEX IF NOT EXISTS idx_attachments_entry
                    ON attachments(entry_id);
                CREATE INDEX IF NOT EXISTS idx_workflows_project
                    ON workflows(project_id);
                CREATE INDEX IF NOT EXISTS idx_workflow_steps_workflow
                    ON workflow_steps(workflow_id, step_order);
                """
            )

            # Schema migration: v4 marks opt-in demo projects so they can be removed safely.
            project_columns = {r["name"] for r in conn.execute("PRAGMA table_info(projects)").fetchall()}
            if "is_demo" not in project_columns:
                conn.execute("ALTER TABLE projects ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0")

            # Schema migration: v2 adds entry tags while preserving all v1 data.
            columns = {r["name"] for r in conn.execute("PRAGMA table_info(entries)").fetchall()}
            if "tags" not in columns:
                conn.execute("ALTER TABLE entries ADD COLUMN tags TEXT")
            if "workflow_id" not in columns:
                conn.execute("ALTER TABLE entries ADD COLUMN workflow_id INTEGER")
            if "user_name" not in columns:
                conn.execute("ALTER TABLE entries ADD COLUMN user_name TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_workflow ON entries(workflow_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_user ON entries(user_name)")

            # v5 gives existing disposable demo rows realistic multi-user attribution.
            conn.execute("""
                UPDATE entries
                SET user_name = CASE
                    WHEN category IN ('Fieldwork / Ground Truth', 'QA / QC') THEN 'Sam Lee'
                    ELSE 'Alex Morgan'
                END
                WHERE (user_name IS NULL OR TRIM(user_name) = '')
                  AND project_id IN (SELECT id FROM projects WHERE is_demo = 1)
            """)

            cur = conn.execute("SELECT value FROM meta WHERE key='schema_version'")
            row = cur.fetchone()
            try:
                previous_schema = int(row["value"]) if row else 0
            except (TypeError, ValueError):
                previous_schema = 0

            # Full-text search is an optional enhancement. Some QGIS/Python
            # SQLite builds do not expose the FTS5 module. A missing FTS5
            # extension must not prevent the work-log database from opening.
            try:
                # v2 indexes tags as well as title/description. Recreate the v1
                # FTS table once if necessary, but keep FTS entirely optional.
                existing_fts_cols = []
                try:
                    existing_fts_cols = [
                        r["name"] for r in conn.execute("PRAGMA table_info(entries_fts)").fetchall()
                    ]
                except sqlite3.OperationalError:
                    existing_fts_cols = []

                rebuild_fts = previous_schema < 2 or not existing_fts_cols
                if existing_fts_cols and "tags" not in existing_fts_cols:
                    conn.executescript(
                        """
                        DROP TRIGGER IF EXISTS entries_ai;
                        DROP TRIGGER IF EXISTS entries_ad;
                        DROP TRIGGER IF EXISTS entries_au;
                        DROP TABLE IF EXISTS entries_fts;
                        """
                    )
                    rebuild_fts = True

                conn.executescript(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts
                        USING fts5(title, description, tags, content='entries', content_rowid='id');

                    DROP TRIGGER IF EXISTS entries_ai;
                    DROP TRIGGER IF EXISTS entries_ad;
                    DROP TRIGGER IF EXISTS entries_au;

                    CREATE TRIGGER entries_ai AFTER INSERT ON entries BEGIN
                        INSERT INTO entries_fts(rowid, title, description, tags)
                        VALUES (new.id, new.title, new.description, new.tags);
                    END;
                    CREATE TRIGGER entries_ad AFTER DELETE ON entries BEGIN
                        INSERT INTO entries_fts(entries_fts, rowid, title, description, tags)
                        VALUES ('delete', old.id, old.title, old.description, old.tags);
                    END;
                    CREATE TRIGGER entries_au AFTER UPDATE ON entries BEGIN
                        INSERT INTO entries_fts(entries_fts, rowid, title, description, tags)
                        VALUES ('delete', old.id, old.title, old.description, old.tags);
                        INSERT INTO entries_fts(rowid, title, description, tags)
                        VALUES (new.id, new.title, new.description, new.tags);
                    END;
                    """
                )
                if rebuild_fts:
                    conn.execute("INSERT INTO entries_fts(entries_fts) VALUES ('rebuild')")
                self.fts_enabled = True
            except sqlite3.OperationalError:
                self.fts_enabled = False

            # schema version
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )

            # seed default categories
            for cat in DEFAULT_CATEGORIES:
                conn.execute(
                    "INSERT OR IGNORE INTO categories(name) VALUES (?)", (cat,)
                )

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------
    def get_or_create_project(
        self,
        name: str,
        qgis_project_path: Optional[str] = None,
        workspace_name: Optional[str] = None,
    ) -> int:
        """Return project id, creating the row if it does not exist."""
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT id FROM projects WHERE name = ?", (name,)
            )
            row = cur.fetchone()
            if row:
                # optionally refresh path / workspace
                now = _now()
                conn.execute(
                    """
                    UPDATE projects
                    SET qgis_project_path = COALESCE(?, qgis_project_path),
                        workspace_name    = COALESCE(?, workspace_name),
                        updated_at        = ?
                    WHERE id = ?
                    """,
                    (qgis_project_path, workspace_name, now, row["id"]),
                )
                return row["id"]

            now = _now()
            cur = conn.execute(
                """
                INSERT INTO projects (name, qgis_project_path, workspace_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, qgis_project_path, workspace_name, now, now),
            )
            return cur.lastrowid

    def list_projects(self) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.execute(
                """
                SELECT p.*,
                       (SELECT COUNT(*) FROM entries e WHERE e.project_id = p.id) AS entry_count
                FROM projects p
                ORDER BY p.name COLLATE NOCASE
                """
            )
            return [dict(r) for r in cur.fetchall()]

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def rename_project(self, project_id: int, new_name: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE projects SET name = ?, updated_at = ? WHERE id = ?",
                (new_name, _now(), project_id),
            )

    def archive_untitled_project(self, project_id: int) -> None:
        with self._conn() as conn:
            conn.execute("BEGIN IMMEDIATE")
            project = conn.execute(
                "SELECT id FROM projects WHERE id = ? AND name = 'Untitled' AND qgis_project_path IS NULL",
                (project_id,),
            ).fetchone()
            if not project:
                return
            has_content = conn.execute(
                "SELECT EXISTS(SELECT 1 FROM entries WHERE project_id = ?) "
                "OR EXISTS(SELECT 1 FROM workflows WHERE project_id = ?)",
                (project_id, project_id),
            ).fetchone()[0]
            if not has_content:
                return

            archive_name = "Untitled archive"
            now = _now()
            conn.execute(
                "INSERT OR IGNORE INTO projects(name, created_at, updated_at) VALUES (?, ?, ?)",
                (archive_name, now, now),
            )
            archive_id = conn.execute(
                "SELECT id FROM projects WHERE name = ?", (archive_name,)
            ).fetchone()["id"]
            conn.execute("UPDATE entries SET project_id = ? WHERE project_id = ?", (archive_id, project_id))
            conn.execute("UPDATE workflows SET project_id = ? WHERE project_id = ?", (archive_id, project_id))
            conn.execute("UPDATE projects SET updated_at = ? WHERE id IN (?, ?)", (now, project_id, archive_id))

    def delete_project(self, project_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    # ------------------------------------------------------------------
    # Demo / template data
    # ------------------------------------------------------------------
    def has_demo_data(self) -> bool:
        """Return True when one or more opt-in demo projects are installed."""
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM projects WHERE is_demo = 1").fetchone()
            return bool(row and row["c"])

    def remove_demo_data(self) -> int:
        """Remove only projects explicitly marked as demo data. Returns project count."""
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM projects WHERE is_demo = 1").fetchone()
            count = int(row["c"] or 0) if row else 0
            conn.execute("DELETE FROM projects WHERE is_demo = 1")
            return count

    def install_demo_data(self) -> Dict[str, int]:
        """Install a disposable GIS/remote-sensing demo pack into the active database.

        Dates are generated relative to today so Reports opens on meaningful data even
        when the plugin is installed months or years after this release.
        """
        from datetime import datetime, timedelta

        # Reinstall means reset: never duplicate the template records.
        self.remove_demo_data()
        now = datetime.now().replace(second=0, microsecond=0)
        start = (now - timedelta(days=35)).replace(hour=9, minute=0)

        def demo_project(name: str, notes: str) -> int:
            ts = _now()
            with self._conn() as conn:
                cur = conn.execute(
                    """INSERT INTO projects
                       (name, qgis_project_path, workspace_name, notes, is_demo, created_at, updated_at)
                       VALUES (?, NULL, ?, ?, 1, ?, ?)""",
                    (name, name, notes, ts, ts),
                )
                return int(cur.lastrowid)

        pasture = demo_project(
            "DEMO — Hauraki Pasture Remote Sensing",
            "Template project showing a multi-day Sentinel-1/Sentinel-2, field ground-truth and QGIS analysis workflow.",
        )
        drone = demo_project(
            "DEMO — Drone Orthomosaic & QA",
            "Secondary template project used to demonstrate project comparisons, drone processing, QA/QC and reporting.",
        )

        # Workflow 1: optical vegetation analysis
        w_ndvi = self.create_workflow(
            pasture,
            "Sentinel-2 pasture NDVI & paddock statistics",
            purpose="Produce cloud-screened Sentinel-2 vegetation metrics and paddock-level summary statistics for pasture monitoring.",
            version="1.0",
            status="Final",
            notes="Example reproducible workflow. Replace catalogue IDs, paths and thresholds with values from your own project.",
            qgis_version="QGIS demo",
            platform_name="Template",
        )
        ndvi_steps = [
            ("Data", "Acquire Sentinel-2 L2A scene", "Select the closest cloud-free acquisition to field observations and record the product identifier."),
            ("QGIS Processing", "Clip bands to farm AOI", "Clip B04, B08 and scene classification data to the project boundary.", "gdal:cliprasterbymasklayer", {"CROP_TO_CUTLINE": True, "KEEP_RESOLUTION": True}),
            ("Processing", "Create valid-pixel / cloud mask", "Mask cloud, cloud shadow and invalid pixels using the scene classification layer."),
            ("QGIS Processing", "Calculate NDVI", "Calculate (NIR - Red) / (NIR + Red) as Float32.", "qgis:rastercalculator", {"EXPRESSION": "(B08@1 - B04@1) / (B08@1 + B04@1)"}),
            ("QGIS Processing", "Paddock zonal statistics", "Calculate mean, median, standard deviation, minimum and maximum NDVI for each paddock.", "native:zonalstatisticsfb", {"STATISTICS": [2,3,4,5,6]}),
            ("QA / QC", "Review outputs and metadata", "Check cloud-mask edges, raster alignment, NoData handling and unexpected paddock values before export."),
        ]
        for row in ndvi_steps:
            st, title, desc = row[:3]
            alg = row[3] if len(row) > 3 else None
            params = row[4] if len(row) > 4 else None
            self.add_workflow_step(w_ndvi, st, title, description=desc, algorithm_id=alg,
                                   parameters_json=json.dumps(params, indent=2) if params else None)
        self.replace_workflow_parameters(w_ndvi, [
            {"name":"Output CRS", "value":"EPSG:2193", "unit":"", "notes":"NZTM2000 example project CRS"},
            {"name":"Analysis pixel size", "value":"10", "unit":"m", "notes":"Preserve Sentinel-2 10 m red/NIR grid"},
            {"name":"Resampling", "value":"Nearest neighbour", "unit":"", "notes":"For masks/categorical rasters; avoid changing classes"},
            {"name":"NDVI expression", "value":"(B08-B04)/(B08+B04)", "unit":"", "notes":"Float output"},
            {"name":"Cloud handling", "value":"Mask cloud + shadow + invalid SCL classes", "unit":"", "notes":"Document exact class list for production work"},
            {"name":"Zonal statistics", "value":"mean, median, std, min, max", "unit":"", "notes":"Per paddock polygon"},
        ])
        self.replace_workflow_artifacts(w_ndvi, [
            {"kind":"Input", "label":"Sentinel-2 L2A scene", "path_uri":"catalogue://S2_DEMO_PRODUCT", "notes":"Example catalogue identifier"},
            {"kind":"Input", "label":"Farm / paddock boundaries", "path_uri":"demo/paddocks.gpkg", "notes":"Vector polygons"},
            {"kind":"Input", "label":"Field ground-truth observations", "path_uri":"demo/ground_truth.csv", "notes":"RPM/field observations near overpass"},
            {"kind":"Output", "label":"Cloud-masked NDVI raster", "path_uri":"outputs/demo_ndvi.tif", "notes":"10 m analysis raster"},
            {"kind":"Output", "label":"Paddock vegetation statistics", "path_uri":"outputs/demo_paddock_ndvi.gpkg", "notes":"Vector output with zonal statistics"},
        ])

        # Workflow 2: Sentinel-1 SAR preprocessing
        w_sar = self.create_workflow(
            pasture,
            "Sentinel-1 pasture backscatter preprocessing",
            purpose="Prepare Sentinel-1 VV/VH backscatter for paddock-scale structural and moisture comparison.",
            version="0.9",
            status="Active",
            notes="Example SAR workflow showing how non-QGIS or external processing can be recorded as manual steps.",
            qgis_version="QGIS demo",
            platform_name="Template",
        )
        for st, title, desc in [
            ("Data", "Acquire Sentinel-1 GRD", "Record acquisition date, orbit direction, relative orbit and polarisation."),
            ("External / SNAP", "Apply orbit file and calibration", "Calibrate VV/VH to backscatter; retain processing settings in Final Parameters."),
            ("External / SNAP", "Speckle filtering / terrain correction", "Apply the selected filter and Range-Doppler terrain correction."),
            ("QGIS", "Clip calibrated VV/VH to paddocks", "Bring final rasters into QGIS and clip to the farm analysis extent."),
            ("Analysis", "Extract paddock backscatter statistics", "Calculate paddock medians for VV, VH and derived VV/VH metrics."),
        ]:
            self.add_workflow_step(w_sar, st, title, description=desc)
        self.replace_workflow_parameters(w_sar, [
            {"name":"Polarisations", "value":"VV, VH", "unit":"", "notes":"Dual-pol example"},
            {"name":"Output backscatter", "value":"Gamma0", "unit":"dB", "notes":"Record linear/dB conversion explicitly"},
            {"name":"Terrain model", "value":"Copernicus DEM", "unit":"", "notes":"Example DEM source"},
            {"name":"Output CRS", "value":"EPSG:2193", "unit":"", "notes":"Project CRS"},
        ])
        self.replace_workflow_artifacts(w_sar, [
            {"kind":"Input", "label":"Sentinel-1 GRD scene", "path_uri":"catalogue://S1_DEMO_PRODUCT", "notes":"Example product"},
            {"kind":"Output", "label":"VV Gamma0 raster", "path_uri":"outputs/demo_s1_vv_gamma0.tif", "notes":"Terrain corrected"},
            {"kind":"Output", "label":"VH Gamma0 raster", "path_uri":"outputs/demo_s1_vh_gamma0.tif", "notes":"Terrain corrected"},
        ])

        # Workflow 3: drone orthomosaic/QC
        w_drone = self.create_workflow(
            drone,
            "Drone orthomosaic and spatial QA",
            purpose="Create an orthomosaic from RGB drone imagery and document geospatial quality checks.",
            version="1.1",
            status="Final",
            notes="Template workflow for a small mapping survey.",
            qgis_version="QGIS demo",
            platform_name="Template",
        )
        for st, title, desc in [
            ("Fieldwork", "Flight planning and capture", "Record altitude, overlap, camera mode, weather and flight identifier."),
            ("Photogrammetry", "Align imagery / build sparse cloud", "Run image alignment and inspect tie-point distribution."),
            ("Photogrammetry", "Build surface and orthomosaic", "Generate DEM/DSM as needed and export georeferenced orthomosaic."),
            ("QGIS QA / QC", "Check CRS, extent and control residuals", "Compare against control/check points and inspect visible seam or distortion issues."),
            ("Export", "Package final GeoTIFF and QA summary", "Export final raster and record accuracy / limitations."),
        ]:
            self.add_workflow_step(w_drone, st, title, description=desc)
        self.replace_workflow_parameters(w_drone, [
            {"name":"Flight altitude", "value":"80", "unit":"m AGL", "notes":"Example only"},
            {"name":"Forward overlap", "value":"80", "unit":"%", "notes":"Example only"},
            {"name":"Side overlap", "value":"70", "unit":"%", "notes":"Example only"},
            {"name":"Output CRS", "value":"EPSG:2193", "unit":"", "notes":"NZTM2000"},
            {"name":"Orthomosaic GSD", "value":"0.03", "unit":"m", "notes":"Example target resolution"},
        ])
        self.replace_workflow_artifacts(w_drone, [
            {"kind":"Input", "label":"RGB flight images", "path_uri":"demo/drone/images/", "notes":"Example image folder"},
            {"kind":"Input", "label":"Check points", "path_uri":"demo/drone/check_points.gpkg", "notes":"Independent QA points"},
            {"kind":"Output", "label":"RGB orthomosaic", "path_uri":"outputs/demo_orthomosaic.tif", "notes":"GeoTIFF"},
            {"kind":"Output", "label":"Spatial QA record", "path_uri":"outputs/demo_qa.csv", "notes":"Residuals and notes"},
        ])

        # Multi-day work log. Offset, time, project, class, minutes, title, tags, workflow
        records = [
            (0,  "09:10", pasture, "Research / Literature", 75,  "Define pasture monitoring question", "research, pasture, Sentinel-2, Sentinel-1", None),
            (1,  "10:00", pasture, "GIS / Spatial Analysis", 105, "Prepare paddock boundaries", "QGIS, GeoPackage, paddocks, topology", w_ndvi),
            (2,  "08:35", pasture, "Remote Sensing", 120, "Review Sentinel-2 candidate acquisitions", "Sentinel-2, cloud, catalogue, optical", w_ndvi),
            (3,  "13:20", pasture, "Fieldwork / Ground Truth", 150, "Ground-truth pasture biomass", "fieldwork, ground truth, RPM, biomass, GPS", w_ndvi),
            (4,  "09:05", pasture, "Processing", 135, "Clip and mask Sentinel-2 scene", "Sentinel-2, QGIS, cloud mask, processing", w_ndvi),
            (4,  "13:10", pasture, "Remote Sensing", 90,  "Calculate NDVI and inspect histogram", "NDVI, Sentinel-2, raster calculator, QA", w_ndvi),
            (6,  "10:25", pasture, "GIS / Spatial Analysis", 110, "Paddock zonal statistics", "zonal statistics, paddocks, NDVI, QGIS", w_ndvi),
            (7,  "14:00", pasture, "QA / QC", 70,  "Check cloud-mask and edge artefacts", "QA, cloud mask, Sentinel-2, NoData", w_ndvi),
            (8,  "09:30", pasture, "Documentation / Reporting", 80, "Document optical workflow parameters", "workflow, reproducibility, NDVI, documentation", w_ndvi),
            (10, "08:50", pasture, "Remote Sensing", 95,  "Select Sentinel-1 GRD acquisition", "Sentinel-1, SAR, GRD, orbit", w_sar),
            (11, "09:15", pasture, "Processing", 160, "Calibrate and terrain-correct SAR", "Sentinel-1, SAR, SNAP, Gamma0, terrain correction", w_sar),
            (12, "14:30", pasture, "GIS / Spatial Analysis", 100, "Extract VV/VH paddock statistics", "Sentinel-1, VV, VH, paddocks, QGIS", w_sar),
            (14, "10:10", pasture, "Coding / Automation", 125, "Prototype comparison script", "Python, pandas, Sentinel-1, Sentinel-2, automation", w_sar),
            (15, "13:00", pasture, "QA / QC", 65, "Check optical/SAR date alignment", "QA, temporal alignment, Sentinel-1, Sentinel-2", w_sar),
            (17, "09:00", pasture, "Remote Sensing", 140, "Compare NDVI and backscatter patterns", "NDVI, SAR, correlation, pasture", w_sar),
            (18, "15:00", pasture, "Meeting / Client", 45, "Review preliminary paddock results", "review, communication, paddocks", None),
            (20, "09:40", pasture, "Documentation / Reporting", 115, "Prepare interim GIS/RS summary", "reporting, maps, charts, reproducibility", w_ndvi),
            (22, "08:45", pasture, "Fieldwork / Ground Truth", 130, "Repeat pasture observations", "fieldwork, RPM, GPS, validation", w_ndvi),
            (24, "10:20", pasture, "GIS / Spatial Analysis", 105, "Compare repeat ground truth with imagery", "validation, NDVI, ground truth, paddocks", w_ndvi),
            (27, "09:05", pasture, "Mapping / Cartography", 95, "Prepare paddock vegetation map", "cartography, QGIS, symbology, NDVI", w_ndvi),
            (30, "11:15", pasture, "Documentation / Reporting", 90, "Finalise workflow and parameter record", "workflow, final parameters, provenance, reproducibility", w_ndvi),
            (32, "09:10", pasture, "Research / Literature", 60, "Review SAR pasture literature", "literature, SAR, pasture, Sentinel-1", w_sar),
            (34, "13:15", pasture, "QA / QC", 75, "Final dataset QA and archive check", "QA, metadata, archive, provenance", w_ndvi),

            (5,  "08:00", drone, "Fieldwork / Ground Truth", 110, "Drone flight and check-point capture", "drone, RGB, fieldwork, GCP, check point", w_drone),
            (6,  "13:00", drone, "Processing", 165, "Photogrammetry alignment and dense processing", "drone, photogrammetry, orthomosaic, processing", w_drone),
            (9,  "10:30", drone, "QA / QC", 85, "Inspect orthomosaic and control residuals", "drone, QA, orthomosaic, RMSE", w_drone),
            (13, "11:10", drone, "GIS / Spatial Analysis", 75, "Clip orthomosaic and verify CRS", "QGIS, orthomosaic, CRS, GeoTIFF", w_drone),
            (19, "14:10", drone, "Mapping / Cartography", 80, "Create survey overview map", "cartography, drone, QGIS, layout", w_drone),
            (28, "10:00", drone, "Documentation / Reporting", 70, "Export QA summary and archive notes", "reporting, QA, provenance, drone", w_drone),
        ]

        descriptions = {
            "Define pasture monitoring question": "Set the analysis objective, expected outputs and validation approach before processing begins.",
            "Ground-truth pasture biomass": "Collected representative field observations close to satellite overpass time; recorded GPS and field conditions.",
            "Calibrate and terrain-correct SAR": "Example external-processing record demonstrating that Work Log can preserve non-QGIS steps alongside QGIS work.",
            "Drone flight and check-point capture": "Captured example RGB survey imagery and independent spatial check points for subsequent QA.",
        }
        entry_count = 0
        for offset, hhmm, pid, category, mins, title, tags, wid in records:
            hour, minute = map(int, hhmm.split(":"))
            dt = (start + timedelta(days=offset)).replace(hour=hour, minute=minute)
            self.add_entry(
                pid, category,
                title=title,
                description=descriptions.get(title, "Template record showing how this type of GIS/remote-sensing activity can be documented in TerraAnalytica Work Log."),
                tags=tags,
                workflow_id=wid,
                user_name=("Sam Lee" if (pid == drone or category in ("Fieldwork / Ground Truth", "QA / QC")) else "Alex Morgan"),
                duration_minutes=mins,
                workspace_name="TerraAnalytica Work Log Demo",
                timestamp=dt.isoformat(timespec="minutes"),
            )
            entry_count += 1

        return {"projects": 2, "entries": entry_count, "workflows": 3}

    # ------------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------------
    def list_categories(self) -> List[str]:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT name FROM categories ORDER BY name COLLATE NOCASE"
            )
            return [r["name"] for r in cur.fetchall()]

    def add_category(self, name: str, *, connection=None) -> None:
        with self._conn(connection) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO categories(name) VALUES (?)", (name.strip(),)
            )

    def remove_category(self, name: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM categories WHERE name = ?", (name,))

    # ------------------------------------------------------------------
    # Entries
    # ------------------------------------------------------------------
    def add_entry(
        self,
        project_id: int,
        category: str,
        description: str = "",
        title: str = "",
        tags: str = "",
        workflow_id: Optional[int] = None,
        user_name: str = "",
        duration_minutes: Optional[int] = None,
        workspace_name: Optional[str] = None,
        timestamp: Optional[str] = None,
        *,
        connection=None,
    ) -> int:
        ts = timestamp or _now()
        now = _now()
        with self._conn(connection) as conn:
            cur = conn.execute(
                """
                INSERT INTO entries (
                    project_id, timestamp, category, user_name, duration_minutes,
                    title, description, tags, workflow_id, workspace_name, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    ts,
                    category,
                    user_name.strip() or None,
                    duration_minutes,
                    title or None,
                    description or None,
                    tags or None,
                    workflow_id,
                    workspace_name,
                    now,
                    now,
                ),
            )
            return cur.lastrowid

    def update_entry(
        self,
        entry_id: int,
        category: Optional[str] = None,
        description: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[str] = None,
        workflow_id: Any = _UNSET,
        user_name: Optional[str] = None,
        duration_minutes: Any = _UNSET,
        workspace_name: Optional[str] = None,
        timestamp: Optional[str] = None,
        *,
        connection=None,
    ) -> None:
        fields = []
        values = []
        if category is not None:
            fields.append("category = ?")
            values.append(category)
        if description is not None:
            fields.append("description = ?")
            values.append(description)
        if title is not None:
            fields.append("title = ?")
            values.append(title)
        if tags is not None:
            fields.append("tags = ?")
            values.append(tags)
        if workflow_id is not _UNSET:
            fields.append("workflow_id = ?")
            values.append(workflow_id)
        if user_name is not None:
            fields.append("user_name = ?")
            values.append(user_name.strip() or None)
        if duration_minutes is not _UNSET:
            fields.append("duration_minutes = ?")
            values.append(duration_minutes)
        if workspace_name is not None:
            fields.append("workspace_name = ?")
            values.append(workspace_name)
        if timestamp is not None:
            fields.append("timestamp = ?")
            values.append(timestamp)

        if not fields:
            return

        fields.append("updated_at = ?")
        values.append(_now())
        values.append(entry_id)

        sql = f"UPDATE entries SET {', '.join(fields)} WHERE id = ?"
        with self._conn(connection) as conn:
            conn.execute(sql, values)

    def save_entry(self, project_id, entry_id, fields, removed_attachments, attachments):
        # Keep the entry and its attachment records in one transaction.
        with self._conn() as conn:
            self.add_category(fields["category"], connection=conn)
            if entry_id is None:
                entry_id = self.add_entry(project_id, **fields, connection=conn)
            else:
                self.update_entry(entry_id, **fields, connection=conn)
            for attachment_id in removed_attachments:
                self.delete_attachment(attachment_id, connection=conn)
            for attachment in attachments:
                self.add_attachment(entry_id, **attachment, connection=conn)
            return entry_id

    def delete_entry(self, entry_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))

    def get_entry(self, entry_id: int) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_entries(
        self,
        project_id: int,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        search_text: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Return entries for a project, newest first, with optional filters."""
        clauses = ["e.project_id = ?"]
        params: List[Any] = [project_id]

        if category:
            clauses.append("e.category = ?")
            params.append(category)

        if tag:
            clauses.append("(',' || COALESCE(e.tags, '') || ',') LIKE ?")
            params.append(f"%,{tag},%")

        if date_from:
            clauses.append("e.timestamp >= ?")
            params.append(date_from)

        if date_to:
            # inclusive end-of-day
            if len(date_to) == 10:
                clauses.append("e.timestamp < date(?, '+1 day')")
            else:
                clauses.append("e.timestamp <= ?")
            params.append(date_to)

        join = ""
        if search_text and search_text.strip():
            if not self.fts_enabled:
                return self._list_entries_like(
                    project_id, category, tag, search_text, date_from, date_to, limit, offset
                )
            # FTS5
            join = "JOIN entries_fts fts ON fts.rowid = e.id"
            clauses.append("entries_fts MATCH ?")
            # simple query – escape double quotes
            q = search_text.strip().replace('"', '""')
            params.append(f'"{q}"' if " " in q else q)

        where = " AND ".join(clauses)
        sql = f"""
            SELECT e.*,
                   (SELECT COUNT(*) FROM attachments a WHERE a.entry_id = e.id) AS attachment_count
            FROM entries e
            {join}
            WHERE {where}
            ORDER BY e.timestamp DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        with self._conn() as conn:
            try:
                cur = conn.execute(sql, params)
                return [dict(r) for r in cur.fetchall()]
            except sqlite3.OperationalError:
                # FTS may fail on very short/odd queries – fall back to LIKE
                if search_text:
                    return self._list_entries_like(
                        project_id, category, tag, search_text, date_from, date_to, limit, offset
                    )
                raise

    def _list_entries_like(
        self,
        project_id: int,
        category: Optional[str],
        tag: Optional[str],
        search_text: str,
        date_from: Optional[str],
        date_to: Optional[str],
        limit: int,
        offset: int,
    ) -> List[Dict[str, Any]]:
        clauses = ["project_id = ?"]
        params: List[Any] = [project_id]
        if category:
            clauses.append("category = ?")
            params.append(category)
        if tag:
            clauses.append("(',' || COALESCE(tags, '') || ',') LIKE ?")
            params.append(f"%,{tag},%")
        if date_from:
            clauses.append("timestamp >= ?")
            params.append(date_from)
        if date_to:
            if len(date_to) == 10:
                clauses.append("timestamp < date(?, '+1 day')")
            else:
                clauses.append("timestamp <= ?")
            params.append(date_to)

        like = f"%{search_text.strip()}%"
        clauses.append("(title LIKE ? OR description LIKE ? OR tags LIKE ?)")
        params.extend([like, like, like])

        where = " AND ".join(clauses)
        sql = f"""
            SELECT e.*,
                   (SELECT COUNT(*) FROM attachments a WHERE a.entry_id = e.id) AS attachment_count
            FROM entries e
            WHERE {where}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        with self._conn() as conn:
            cur = conn.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def list_users(self, project_id: Optional[int] = None) -> List[str]:
        """Return distinct recorded work users/analysts, sorted case-insensitively."""
        sql = "SELECT DISTINCT user_name FROM entries WHERE user_name IS NOT NULL AND TRIM(user_name) <> ''"
        params: List[Any] = []
        if project_id is not None:
            sql += " AND project_id = ?"
            params.append(project_id)
        sql += " ORDER BY user_name COLLATE NOCASE"
        with self._conn() as conn:
            return [r["user_name"] for r in conn.execute(sql, params).fetchall()]

    def list_tags(self, project_id: Optional[int] = None) -> List[str]:
        """Return distinct entry tags, case-insensitively sorted."""
        sql = "SELECT tags FROM entries WHERE tags IS NOT NULL AND TRIM(tags) <> ''"
        params: List[Any] = []
        if project_id is not None:
            sql += " AND project_id = ?"
            params.append(project_id)
        found = {}
        with self._conn() as conn:
            for row in conn.execute(sql, params).fetchall():
                for tag in _split_tags(row["tags"] or ""):
                    found.setdefault(tag.casefold(), tag)
        return [found[k] for k in sorted(found)]

    def report_entries(
        self,
        project_id: Optional[int] = None,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        user_name: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return reporting rows across one or all projects."""
        clauses = ["1=1"]
        params: List[Any] = []
        if project_id is not None:
            clauses.append("e.project_id = ?")
            params.append(project_id)
        if category:
            clauses.append("e.category = ?")
            params.append(category)
        if user_name:
            clauses.append("e.user_name = ?")
            params.append(user_name)
        if date_from:
            clauses.append("e.timestamp >= ?")
            params.append(date_from)
        if date_to:
            if len(date_to) == 10:
                clauses.append("e.timestamp < date(?, '+1 day')")
            else:
                clauses.append("e.timestamp <= ?")
            params.append(date_to)

        sql = f"""
            SELECT e.id, e.project_id, e.timestamp, e.category, e.user_name,
                   e.duration_minutes, e.title, e.description, e.tags, e.workflow_id,
                   p.name AS project_name, w.name AS workflow_name, w.version AS workflow_version
            FROM entries e
            JOIN projects p ON p.id = e.project_id
            LEFT JOIN workflows w ON w.id = e.workflow_id
            WHERE {' AND '.join(clauses)}
            ORDER BY e.timestamp
        """
        with self._conn() as conn:
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        if tag:
            wanted = tag.casefold()
            rows = [
                r for r in rows
                if wanted in {t.casefold() for t in _split_tags(r.get("tags") or "")}
            ]
        return rows

    # ------------------------------------------------------------------
    # Workflows / processing provenance
    # ------------------------------------------------------------------
    def create_workflow(
        self, project_id: int, name: str, purpose: str = "", version: str = "1.0",
        status: str = "Draft", notes: str = "", qgis_version: str = "", platform_name: str = "",
    ) -> int:
        now = _now()
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO workflows (
                    project_id, name, purpose, version, status, notes, qgis_version, platform,
                    finalised_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (project_id, name.strip(), purpose or None, version or "1.0", status or "Draft",
                 notes or None, qgis_version or None, platform_name or None,
                 now if (status or "").casefold() == "final" else None, now, now),
            )
            return int(cur.lastrowid)

    def update_workflow(
        self, workflow_id: int, name: str, purpose: str = "", version: str = "1.0",
        status: str = "Draft", notes: str = "",
    ) -> None:
        with self._conn() as conn:
            current = conn.execute("SELECT status, finalised_at FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
            finalised = current["finalised_at"] if current else None
            if (status or "").casefold() == "final" and not finalised:
                finalised = _now()
            elif (status or "").casefold() != "final":
                finalised = None
            conn.execute(
                """UPDATE workflows SET name=?, purpose=?, version=?, status=?, notes=?,
                   finalised_at=?, updated_at=? WHERE id=?""",
                (name.strip(), purpose or None, version or "1.0", status or "Draft",
                 notes or None, finalised, _now(), workflow_id),
            )

    def delete_workflow(self, workflow_id: int) -> None:
        with self._conn() as conn:
            conn.execute("UPDATE entries SET workflow_id = NULL WHERE workflow_id = ?", (workflow_id,))
            conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))

    def get_workflow(self, workflow_id: int) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                """SELECT w.*, p.name AS project_name FROM workflows w
                   JOIN projects p ON p.id=w.project_id WHERE w.id=?""", (workflow_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_workflows(self, project_id: Optional[int] = None) -> List[Dict[str, Any]]:
        clauses = []
        params: List[Any] = []
        if project_id is not None:
            clauses.append("w.project_id = ?")
            params.append(project_id)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        with self._conn() as conn:
            rows = conn.execute(
                f"""SELECT w.*, p.name AS project_name,
                       (SELECT COUNT(*) FROM workflow_steps s WHERE s.workflow_id=w.id) AS step_count
                    FROM workflows w JOIN projects p ON p.id=w.project_id
                    {where} ORDER BY w.updated_at DESC, w.name COLLATE NOCASE""", params
            ).fetchall()
            return [dict(r) for r in rows]

    def list_workflow_steps(self, workflow_id: int) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM workflow_steps WHERE workflow_id=? ORDER BY step_order, id",
                (workflow_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def add_workflow_step(self, workflow_id: int, step_type: str, title: str, **kwargs) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(step_order), 0) + 1 AS n FROM workflow_steps WHERE workflow_id=?",
                (workflow_id,),
            ).fetchone()
            order = int(row["n"] or 1)
            now = _now()
            cur = conn.execute(
                """INSERT INTO workflow_steps (
                    workflow_id, step_order, step_type, title, description, algorithm_id,
                    parameters_json, python_command, process_command, execution_log,
                    source_history_id, source_timestamp, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (workflow_id, order, step_type or "Manual", title.strip(),
                 kwargs.get("description") or None, kwargs.get("algorithm_id") or None,
                 kwargs.get("parameters_json") or None, kwargs.get("python_command") or None,
                 kwargs.get("process_command") or None, kwargs.get("execution_log") or None,
                 kwargs.get("source_history_id"), kwargs.get("source_timestamp") or None, now, now),
            )
            conn.execute("UPDATE workflows SET updated_at=? WHERE id=?", (now, workflow_id))
            return int(cur.lastrowid)

    def update_workflow_step(self, step_id: int, step_type: str, title: str, description: str = "") -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE workflow_steps SET step_type=?, title=?, description=?, updated_at=? WHERE id=?",
                (step_type or "Manual", title.strip(), description or None, _now(), step_id),
            )

    def delete_workflow_step(self, step_id: int) -> None:
        with self._conn() as conn:
            row = conn.execute("SELECT workflow_id FROM workflow_steps WHERE id=?", (step_id,)).fetchone()
            if not row:
                return
            workflow_id = row["workflow_id"]
            conn.execute("DELETE FROM workflow_steps WHERE id=?", (step_id,))
            ids = [r["id"] for r in conn.execute(
                "SELECT id FROM workflow_steps WHERE workflow_id=? ORDER BY step_order, id", (workflow_id,)
            ).fetchall()]
            for i, sid in enumerate(ids, start=1):
                conn.execute("UPDATE workflow_steps SET step_order=? WHERE id=?", (i, sid))
            conn.execute("UPDATE workflows SET updated_at=? WHERE id=?", (_now(), workflow_id))

    def move_workflow_step(self, workflow_id: int, step_id: int, direction: int) -> None:
        steps = self.list_workflow_steps(workflow_id)
        ids = [s["id"] for s in steps]
        if step_id not in ids:
            return
        i = ids.index(step_id)
        j = i + (-1 if direction < 0 else 1)
        if j < 0 or j >= len(ids):
            return
        ids[i], ids[j] = ids[j], ids[i]
        with self._conn() as conn:
            for order, sid in enumerate(ids, start=1):
                conn.execute("UPDATE workflow_steps SET step_order=? WHERE id=?", (order, sid))
            conn.execute("UPDATE workflows SET updated_at=? WHERE id=?", (_now(), workflow_id))

    def replace_workflow_parameters(self, workflow_id: int, rows: List[Dict[str, Any]]) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM workflow_parameters WHERE workflow_id=?", (workflow_id,))
            for i, row in enumerate(rows, start=1):
                name = str(row.get("name") or "").strip()
                if not name:
                    continue
                conn.execute(
                    """INSERT INTO workflow_parameters (workflow_id,name,value,unit,notes,sort_order)
                       VALUES (?,?,?,?,?,?)""",
                    (workflow_id, name, str(row.get("value") or ""), str(row.get("unit") or ""),
                     str(row.get("notes") or ""), i),
                )

    def list_workflow_parameters(self, workflow_id: int) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM workflow_parameters WHERE workflow_id=? ORDER BY sort_order,id", (workflow_id,)
            ).fetchall()]

    def replace_workflow_artifacts(self, workflow_id: int, rows: List[Dict[str, Any]]) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM workflow_artifacts WHERE workflow_id=?", (workflow_id,))
            for i, row in enumerate(rows, start=1):
                label = str(row.get("label") or "").strip()
                if not label:
                    continue
                conn.execute(
                    """INSERT INTO workflow_artifacts (workflow_id,kind,label,path_uri,notes,sort_order)
                       VALUES (?,?,?,?,?,?)""",
                    (workflow_id, str(row.get("kind") or "Input"), label,
                     str(row.get("path_uri") or ""), str(row.get("notes") or ""), i),
                )

    def list_workflow_artifacts(self, workflow_id: int) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM workflow_artifacts WHERE workflow_id=? ORDER BY sort_order,id", (workflow_id,)
            ).fetchall()]

    # ------------------------------------------------------------------
    # Attachments
    # ------------------------------------------------------------------
    def add_attachment(
        self,
        entry_id: int,
        filename: str,
        file_path: Optional[str] = None,
        blob_data: Optional[bytes] = None,
        mime_type: Optional[str] = None,
        *,
        connection=None,
    ) -> int:
        size = None
        if blob_data is not None:
            size = len(blob_data)
        elif file_path and os.path.isfile(file_path):
            size = os.path.getsize(file_path)

        with self._conn(connection) as conn:
            cur = conn.execute(
                """
                INSERT INTO attachments (
                    entry_id, filename, file_path, blob_data, mime_type, size_bytes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    filename,
                    file_path,
                    blob_data,
                    mime_type or _guess_mime(filename),
                    size,
                    _now(),
                ),
            )
            return cur.lastrowid

    def list_attachments(self, entry_id: int) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.execute(
                """
                SELECT id, entry_id, filename, file_path, mime_type, size_bytes, created_at,
                       (blob_data IS NOT NULL) AS has_blob
                FROM attachments
                WHERE entry_id = ?
                ORDER BY id
                """,
                (entry_id,),
            )
            return [dict(r) for r in cur.fetchall()]

    def get_attachment_blob(self, attachment_id: int) -> Optional[bytes]:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT blob_data FROM attachments WHERE id = ?", (attachment_id,)
            )
            row = cur.fetchone()
            return row["blob_data"] if row else None

    def delete_attachment(self, attachment_id: int, *, connection=None) -> None:
        with self._conn(connection) as conn:
            # optionally remove file on disk – left to caller for safety
            conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))

    # ------------------------------------------------------------------
    # Stats / helpers
    # ------------------------------------------------------------------
    def entry_count(self, project_id: int) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT COUNT(*) AS c FROM entries WHERE project_id = ?", (project_id,)
            )
            return cur.fetchone()["c"]

    def total_duration_minutes(self, project_id: int) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """
                SELECT COALESCE(SUM(duration_minutes), 0) AS t
                FROM entries WHERE project_id = ?
                """,
                (project_id,),
            )
            return cur.fetchone()["t"]


# ----------------------------------------------------------------------
# Utility
# ----------------------------------------------------------------------
def _split_tags(value: str) -> List[str]:
    return [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _guess_mime(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
        ".txt": "text/plain",
    }.get(ext, "application/octet-stream")
