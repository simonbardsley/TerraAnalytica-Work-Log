# -*- coding: utf-8 -*-
"""Built-in user guide for TerraAnalytica Work Log."""

from __future__ import annotations

from qgis.PyQt.QtCore import QCoreApplication, Qt
from .branding import brand_label_style, install_theme, title_style

from qgis.PyQt.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QTextBrowser, QVBoxLayout, QWidget
)


HELP_HTML = r"""
<!doctype html>
<html><head><meta charset="utf-8"><style>
body { font-family: sans-serif; line-height: 1.42; margin: 18px; }
h1 { font-size: 24px; margin-bottom: 3px; }
h2 { font-size: 19px; margin-top: 24px; border-bottom: 1px solid #bbb; padding-bottom: 4px; }
h3 { font-size: 16px; margin-top: 18px; }
code, pre { font-family: monospace; }
pre { padding: 10px; border: 1px solid #bbb; border-radius: 4px; white-space: pre-wrap; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 16px; }
th, td { border: 1px solid #aaa; padding: 6px 8px; text-align: left; vertical-align: top; }
th { font-weight: bold; }
.note { padding: 9px 11px; border-left: 4px solid #777; margin: 10px 0; }
.small { font-size: 90%; }
</style></head><body>
<h1>TerraAnalytica Work Log</h1>
<p><b>GIS &amp; Remote Sensing Work Log, Reporting and Processing Provenance for QGIS</b></p>
<p>TerraAnalytica Work Log is designed for analysts, researchers and consultants who need to remember not only <i>what</i> they did, but <i>how</i> a spatial or remote-sensing result was produced.</p>


<h2 id="interface">Interface, branding and light/dark mode</h2>
<p>The full plugin name is <b>TerraAnalytica Work Log</b>; the dock/tab label is shortened to <b>Work Log</b>. The fixed Charcoal header band uses a Gold <b>TERRAANALYTICA</b> eyebrow, white functional title and a short tools statement: <b>Work diary · reporting · processing provenance</b>.</p>
<p>Below the brand band, the interface follows the active QGIS/Qt light or dark palette. <b>Layer Lab Gold (#E8A838)</b> remains the accent. In light mode primary linework uses <b>TA Charcoal (#202326)</b>; in dark mode linework, surfaces and text follow the system palette for contrast while retaining Gold accents. Use <b>Help</b> for general guidance and <b>ⓘ</b> for field-specific explanations.</p>
<div class="note">Interface branding does not force TerraAnalytica onto exported documents. Reports remain neutral by default or can use the organisation heading configured under Settings.</div>

<h2 id="quickstart">Quick start</h2>
<ol>
<li>Open or save a QGIS project. Work Log links records to the current QGIS project automatically.</li>
<li>Choose <b>New Entry</b> and record the work class, time, title, description and useful tags.</li>
<li>Use <b>Reports</b> to review hours by day, project and work class, or filter by tags.</li>
<li>When a method needs to be repeatable, create a <b>Workflow</b> and link work-log entries to it.</li>
<li>Record the workflow's processing steps, final parameters, inputs and outputs. QGIS Processing History steps can be imported where available.</li>
<li>Export reports to CSV/PDF, print them, or export/print a workflow method record.</li>
</ol>
<div class="note"><b>New user?</b> Use <b>Load / Reset Demo Data</b> from the TerraAnalytica Work Log menu. The demo is optional, clearly marked and can be removed without touching your real projects.</div>

<h2 id="backup">Back up and restore Work Log</h2>
<p>Choose <b>Settings → Database → Create backup</b> to save a ZIP with the current database and its available attachments. Work Log reports attachments whose file and embedded copy are both missing.</p>
<p>Choose <b>Restore backup</b>, select the ZIP and choose a destination folder. Work Log creates a new folder with its own database and attachments. Choose <b>Yes</b> to open the restored copy or <b>No</b> to keep using the current database. Use <b>Settings → Database → Browse</b> to switch copies later.</p>

<h2 id="untitled">Notes from an untitled project</h2>
<p>You can log work before saving the QGIS project. Those entries appear under <b>Untitled</b> in Work Log.</p>
<p>When you close the untitled QGIS project, Work Log moves its saved notes and workflows to <b>Untitled archive</b>. Attachments stay linked to their entries. The next untitled project starts with an empty Work Log.</p>
<p>To find an archived note, click <b>Switch project</b> next to the project name and choose <b>Untitled archive</b>. If a search or date filter hides the note, click <b>Clear filters</b>.</p>

<h2 id="window">Window placement</h2>
<p>Choose <b>Pop out</b> to open Work Log in a separate window. Drag its title bar, use <b>Move to monitor</b> to choose a connected display, or choose <b>Dock in QGIS</b> to return it to the main window.</p>

<h2 id="entries">Work-log entries</h2>
<table>
<tr><th>Field</th><th>Purpose</th><th>GIS / remote-sensing example</th></tr>
<tr><td>Project</td><td>The body of work the entry belongs to.</td><td>Pasture Biomass Monitoring</td></tr>
<tr><td>Work class</td><td>Broad type of activity used for reporting.</td><td>Remote Sensing; GIS / Spatial Analysis; Fieldwork / Ground Truth; QA / QC</td></tr>
<tr><td>Title</td><td>A short description of the activity.</td><td>Calculate Sentinel-2 NDVI</td></tr>
<tr><td>Description</td><td>Enough detail to understand what happened and why.</td><td>Masked cloud/shadow pixels, calculated NDVI and reviewed histogram for anomalous values.</td></tr>
<tr><td>Tags</td><td>Specific sensors, tools, methods, datasets or themes. Tags are searchable and reportable.</td><td>Sentinel-2, NDVI, QGIS, cloud mask, paddocks</td></tr>
<tr><td>Duration</td><td>Time actually spent on the activity.</td><td>90 minutes</td></tr>
<tr><td>Workflow</td><td>Optional link to a repeatable processing method.</td><td>Sentinel-2 pasture NDVI &amp; paddock statistics v1.0</td></tr>
</table>

<h3>Work classes versus tags</h3>
<p>Use <b>Work class</b> for a broad category and <b>Tags</b> for detail. For example:</p>
<pre>Work class: Remote Sensing
Tags: Sentinel-1, SAR, VV, VH, Gamma0, SNAP, pasture</pre>
<p>This keeps reports readable while still allowing precise searching and filtering.</p>

<h2 id="reports">Reports and export</h2>
<p>Reports can be filtered by project, user/analyst, work class, tag and date. They summarise total hours, number of entries, active days, average hours per active day, hours by work class, hours through time, hours by project, user attribution and top tags.</p>
<ul>
<li><b>CSV</b> — detailed filtered records for spreadsheet analysis or archiving. Timestamps are exported consistently as ISO 8601 local date/time (<code>YYYY-MM-DDTHH:MM:SS</code>).</li>
<li><b>PDF</b> — a compact formatted report containing the current filters, summary statistics, charts, top 8 tags and matching records.</li>
<li><b>Print</b> — sends the same report to the system print workflow.</li>
</ul>
<p class="small">Tag hours overlap. A two-hour entry tagged both “Sentinel-2” and “NDVI” contributes two hours to each tag. Do not sum tag attribution totals. User-hour summaries use two decimals and include a total row to avoid apparent rounding mismatches.</p>


<h2 id="identity">Report identity and users</h2>
<p>The plugin itself is branded <b>TerraAnalytica Work Log</b>, but exported reports are generic by default. Under <b>Settings &gt; Reporting &amp; User</b>, set an optional <b>Report organisation / heading</b> if reports should carry your own business, laboratory, team or project identity. Leave it blank to use the neutral titles <b>Work Log Report</b> and <b>Workflow Record</b>.</p>
<p>Each work-log entry can also store a <b>User / Analyst</b>. The user shown in the main dock acts as the current session user and is pre-filled on new entries. An optional persistent default user can be set in Settings. Reports can be filtered by analyst and CSV/PDF outputs retain that attribution.</p>
<div class="note"><b>Session behaviour:</b> changing the active user affects new entries only. Existing records keep the user that was stored when they were created or last edited.</div>

<h2 id="disclaimer">Accuracy, reliability and responsible use</h2>
<p>Work Log helps organise user-entered records and information exposed by QGIS, but it does not independently verify that entries, imported processing history, file references, parameters, durations, reports or workflow descriptions are complete, accurate or suitable for a particular purpose.</p>
<ul>
<li>Review important records and exported reports against the source project, data and processing history.</li>
<li>Keep independent backups and preserve authoritative project files and evidence.</li>
<li>Do not rely on Work Log alone for legal, contractual, safety-critical, regulatory, scientific or professional decisions.</li>
<li>Results may also depend on QGIS, third-party providers, plugins, data quality and the user's configuration.</li>
</ul>
<div class="note"><b>Responsibility:</b> users remain responsible for validating their data, methods, outputs and compliance obligations. Work Log is provided under the GPL-2.0-or-later licence without warranty.</div>

<h2 id="related">Related TerraAnalytica QGIS tools</h2>
<p>Work Log is part of a wider family of complementary TerraAnalytica tools for QGIS. The suite includes focused tools for layer and map management, labelling, tool discovery, notebooks, spectral analysis and accuracy assessment.</p>
<p>Related tools include <b>Layer Lab</b>, <b>Map Lab</b>, <b>Label Lab</b>, <b>Toolsearch</b>, <b>Notebook Lab</b>, <b>Spectral Lab</b> and <b>Accuracy Lab</b>. Availability and release status vary while the suite is prepared for publication.</p>
<p class="small">Visit the Work Log homepage for current releases and information about the TerraAnalytica QGIS plugin suite.</p>

<h2 id="koha">Koha and supporting development</h2>
<p>If TerraAnalytica Work Log saves you time or improves the reproducibility of your GIS/remote-sensing work, you may choose to support continued development with a <b>koha</b>.</p>
<p><b>Koha</b> is a Māori concept commonly used for a voluntary gift or contribution offered in appreciation, reciprocity or acknowledgement of value received. Koha is entirely optional in Work Log: it is not required to use the plugin and it does not unlock features.</p>
<p class="small">A public support link can be added to the plugin homepage when one is available.</p>

<h2 id="workflows">Workflows and reproducibility</h2>
<p>Create a workflow when another analyst — or your future self — should be able to understand and repeat the processing method. A workflow consists of:</p>
<ol>
<li><b>Purpose</b> — what result the method is intended to produce.</li>
<li><b>Ordered steps</b> — QGIS Processing operations and/or manual steps from SNAP, Python, R, Google Earth Engine, photogrammetry software, fieldwork or other systems.</li>
<li><b>Final Parameters</b> — the values that define the final accepted method.</li>
<li><b>Inputs &amp; Outputs</b> — datasets, catalogue IDs, paths, database tables, rasters, vectors and generated products.</li>
<li><b>Version and status</b> — keep Draft/Active methods distinct from a Final method.</li>
</ol>

<h3>What belongs in Final Parameters?</h3>
<p>Record values that could change the scientific or spatial result:</p>
<ul>
<li>CRS, pixel size, resampling method and NoData handling</li>
<li>band selection and index equations</li>
<li>cloud, classification or quality thresholds</li>
<li>SAR calibration/backscatter convention and speckle-filter settings</li>
<li>DEM/terrain-correction source</li>
<li>buffer distances, tolerances, kernels and neighbourhood sizes</li>
<li>model type, important hyperparameters and random seed</li>
<li>zonal statistics or aggregation method</li>
<li>drone altitude, overlap, GSD and control/check-point method</li>
</ul>
<div class="note"><b>Rule of thumb:</b> if changing a value could materially change the output, record it.</div>

<h3>Processing History</h3>
<p>Where QGIS exposes a Processing History record, Work Log can import the algorithm and the execution information supplied by QGIS. Use manual steps for work performed outside QGIS Processing or for conceptual/QA steps that still matter to reproducibility.</p>

<h2 id="usecases">GIS &amp; remote-sensing use cases</h2>
<h3>1. Sentinel-2 vegetation monitoring</h3>
<pre>Acquire L2A → cloud/quality mask → clip AOI → calculate NDVI/red-edge metrics
→ zonal statistics → QA/QC → GeoPackage/CSV/map output</pre>
<p>Useful tags: Sentinel-2, NDVI, red edge, vegetation, cloud mask, zonal statistics.</p>

<h3>2. Sentinel-1 SAR preprocessing</h3>
<pre>Acquire GRD → orbit/calibration → speckle handling → terrain correction
→ VV/VH metrics → paddock/polygon statistics → QA/QC</pre>
<p>Record orbit direction, relative orbit if relevant, polarisation, backscatter convention (e.g. Sigma0/Gamma0), dB/linear representation, DEM and terrain-correction settings.</p>

<h3>3. Drone orthomosaic and spatial QA</h3>
<pre>Flight plan/capture → image alignment → surface/orthomosaic generation
→ CRS/export → independent check → QA summary</pre>
<p>Record flight altitude, overlap, sensor/camera mode, GSD, control/check points and accuracy statistics.</p>

<h3>4. QGIS spatial analysis</h3>
<pre>Input layers → clean/validate → reproject if needed → buffer/intersection/join
→ calculate fields/statistics → QA/QC → export</pre>
<p>Record CRS, tolerance, buffer distance, join keys, geometry fixes and output format.</p>

<h3>5. Ground-truth campaign linked to imagery</h3>
<pre>Plan sample locations → field observations/GPS/photos → data QA
→ link to satellite/drone acquisition → comparison/validation → archive</pre>
<p>Tags make it easy to retrieve all entries associated with a sensor, paddock, site, overpass or instrument.</p>

<h3>6. R&amp;D / method development</h3>
<p>Log experiments as ordinary entries and keep the accepted production method in a versioned Workflow. The work log shows the effort and reasoning trail; the workflow shows the reproducible final method.</p>

<h2 id="demo">Demo / template project</h2>
<p>The optional demo pack creates two clearly marked projects:</p>
<ul>
<li><b>DEMO — Hauraki Pasture Remote Sensing</b> — multi-day Sentinel-2, Sentinel-1, field validation, coding, QA and reporting records.</li>
<li><b>DEMO — Drone Orthomosaic &amp; QA</b> — a smaller drone mapping example so the “hours by project” report is meaningful.</li>
</ul>
<p>It also installs three workflows with example steps, final parameters and input/output records. Demo dates are generated relative to the installation date so the Reports window immediately contains useful daily, weekly and monthly patterns.</p>
<p><b>Load / Reset Demo Data</b> deletes and recreates only demo-marked projects. <b>Remove Demo Data</b> deletes only demo-marked projects and leaves real user projects untouched.</p>

<h2 id="practice">Good practice</h2>
<ul>
<li>Write titles so they still make sense six months later.</li>
<li>Use a small, consistent vocabulary for tags.</li>
<li>Log QA/QC as work, not as an afterthought.</li>
<li>Record dataset/product identifiers where possible, not just vague filenames.</li>
<li>Finalise workflow parameters when a method becomes accepted or operational.</li>
<li>Create a new workflow version when a method changes materially rather than silently overwriting its history.</li>
<li>Export periodic PDF/CSV records when evidence or auditability matters.</li>
</ul>

<p class="small">TerraAnalytica Work Log — designed for practical GIS, Earth observation, remote sensing and spatial-science work.</p>
</body></html>
"""


class HelpDialog(QDialog):
    def __init__(self, parent=None, plugin=None):
        super().__init__(parent)
        self.plugin = plugin
        self.setWindowTitle(self.tr("TA Work Log — Help & Use Cases"))
        self.resize(900, 720)

        layout = QVBoxLayout(self)
        brand_box = QWidget()
        brand_layout = QVBoxLayout(brand_box)
        brand_layout.setContentsMargins(0, 0, 0, 4)
        brand_layout.setSpacing(0)
        self.brand_label = QLabel("TERRAANALYTICA")
        self.brand_label.setStyleSheet(brand_label_style())
        brand_layout.addWidget(self.brand_label)
        self.title_label = QLabel(self.tr("Work Log Help & Use Cases"))
        brand_layout.addWidget(self.title_label)
        layout.addWidget(brand_box)

        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(self.tr("Find in help…"))
        search_row.addWidget(self.search, 1)
        self.btn_find = QPushButton(self.tr("Find"))
        search_row.addWidget(self.btn_find)
        if plugin is not None:
            self.btn_demo = QPushButton(self.tr("Load / Reset Demo Data…"))
            search_row.addWidget(self.btn_demo)
        layout.addLayout(search_row)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setHtml(HELP_HTML)
        layout.addWidget(self.browser, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.btn_find.clicked.connect(self._find)
        self.search.returnPressed.connect(self._find)
        if plugin is not None:
            self.btn_demo.clicked.connect(plugin.load_demo_data)

        install_theme(self, self._refresh_theme_assets)

    def _refresh_theme_assets(self) -> None:
        self.brand_label.setStyleSheet(brand_label_style())
        self.title_label.setStyleSheet(title_style(self, 17))

    def tr(self, text: str) -> str:
        return QCoreApplication.translate("WorkLogHelpDialog", text)

    def _find(self) -> None:
        text = self.search.text().strip()
        if text and not self.browser.find(text):
            cursor = self.browser.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            self.browser.setTextCursor(cursor)
            if not self.browser.find(text):
                QMessageBox.information(self, self.tr("Find"), self.tr("No matching text."))
