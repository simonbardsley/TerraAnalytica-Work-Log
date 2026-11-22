# TA Work Log

A lightweight QGIS work diary / technical notebook designed for **GIS and remote-sensing work**.

## Core workflow

The original Work Log workflow remains intentionally simple:

1. Open or select a QGIS project.
2. Create a new entry.
3. Record the work class, time spent, title and technical description.
4. Optionally add GIS/remote-sensing tags and attach files or a map-canvas screenshot.
5. Search or filter the accumulated records later.

## Work classes and tags

**Work class** is the broad activity type used for reporting. Defaults include Remote Sensing, GIS / Spatial Analysis, Processing, Mapping / Cartography, Fieldwork / Ground Truth, Coding / Automation, QA / QC, Research / Literature, Documentation / Reporting, Meeting / Client, Screenshot, Bug / Issue and Other.

**Tags** are more specific descriptors. Examples include `Sentinel-1`, `Sentinel-2`, `SAR`, `NDVI`, `LiDAR`, `drone`, `QGIS`, `Python`, `ground truth`, or a dataset/method name. Multiple tags are comma-separated.

Small **ⓘ** controls provide field-specific help in the entry form and main panel.

## Reports

The **Reports…** window is available from the Work Log panel and plugin menu. It provides:

- total logged hours;
- number of entries;
- active work days;
- average hours per active day;
- hours by work class;
- hours over time, grouped by day, week or month;
- hours by project;
- top tag attribution;
- filters for project, user / analyst, work class, tag and date range.

Tag totals can overlap because one entry can have more than one tag. For example, a two-hour entry tagged `Sentinel-2` and `NDVI` contributes two hours to each tag's attribution.

## Database

One shared SQLite database holds all projects. Existing databases are migrated automatically to schema v5. Workflow/provenance tables, demo markers and user/analyst attribution are added in place; existing entries, tags and attachments are preserved.

Full-text search (FTS5) is used when the SQLite build supplied with QGIS supports it. If FTS5 is unavailable, Work Log falls back to normal SQLite text matching instead of disabling the database.

Default database location is within the active QGIS profile under `worklog/worklog.db`. Attachments are stored in an `attachments` folder beside the database unless embedded as SQLite BLOBs.

## Compatibility

- QGIS 3.22–3.40 family
- QGIS 4.x / Qt6-compatible API forms

Version: **1.4.10**

## Licence

Copyright (C) 2026 NZSpatial Limited, trading as TerraAnalytica.

TA Work Log is free software licensed under the **GNU General
Public License, version 2 or (at your option) any later version**
(`GPL-2.0-or-later`). You may use, study, modify and redistribute the plugin
under those terms. See the bundled `LICENSE` file for the complete licence.

The TerraAnalytica name, logo and product branding are not granted for reuse
as trademarks by the GPL software licence.



## TerraAnalytica interface and QGIS themes

Work Log defines the shared TerraAnalytica plugin visual language: a fixed Charcoal band with a Gold `TERRAANALYTICA` eyebrow, white functional title and a short muted capability statement, followed by compact controls and palette-aware content. The content area follows QGIS light and dark modes. The dock tab is **Work Log** while the Plugin Manager retains the full **TA Work Log** name.

The interface follows the active QGIS/Qt light or dark palette. TA Gold remains the brand accent; controls, tables, search fields, tabs and most action icons adapt for contrast. The boxed **Help** and **Settings** controls match the wider TerraAnalytica plugin family, while field-specific explanatory controls use **ⓘ**. Exported reports remain neutral/customisable and are not forced to carry TerraAnalytica branding.

## Reporting and export

The **Reports…** window summarises logged GIS and remote-sensing work by project, work class, tag and date range. The current filtered report can be:

- exported to **CSV** for further analysis, audit or spreadsheet use;
- exported to **PDF** with summary metrics and charts; or
- sent to the system **Print** dialog.

CSV exports include any linked workflow name/version alongside the work-log entry.

## Reproducible workflows

Open **Workflows…** from the TA Work Log toolbar, menu or dock panel. A workflow is intended to record *how* a GIS or remote-sensing result was produced, while normal Work Log entries continue to record *what work was done and how long it took*.

A workflow can contain:

1. **Ordered steps** – manual steps or imported QGIS Processing History operations.
2. **QGIS Processing provenance** – algorithm ID, parameters/inputs, Python command, `qgis_process` command, timestamp and execution log where QGIS provides them.
3. **Final Parameters** – reproducibility-critical settings such as CRS, pixel size, resampling, thresholds, kernels, bands or model parameters.
4. **Inputs & Outputs** – source datasets, catalogue IDs, cloud assets, files and final products.
5. **Process Diagram** – generated automatically from the ordered workflow steps.
6. **Workflow PDF / Print** – a durable method/provenance record for research, R&D evidence and technical reporting.

Manual steps are intentionally supported so workflows can include operations performed outside QGIS Processing, such as SNAP, Google Earth Engine, Python/Jupyter, field measurements, command-line tools, drone processing or manual interpretation.

A normal Work Log entry can optionally be linked to one of the workflows in the same project.


## Built-in help and demo/template data

Choose **Help & Use Cases…** from the TA Work Log menu (or use the ⓘ button in the dock) for an integrated guide covering entries, reports, workflows, final parameters and GIS/remote-sensing use cases. A Markdown copy is also bundled as `HELP.md`.

For evaluation/training, choose **Load / Reset Demo Data…**. The demo is opt-in and creates two clearly marked projects with recent generated dates, realistic GIS/RS entries and three workflow records. It exercises daily/weekly/monthly reporting, work classes, tags, project comparison, search, CSV/PDF/print and workflow diagrams.

Demo projects are marked internally (`is_demo=1`). **Remove Demo Data…** deletes only those projects and their cascading demo records; real projects are not touched. Resetting the demo removes and recreates only demo-marked projects.


## Reporting identity and users

The plugin remains TerraAnalytica-branded in QGIS. Exported Work Log and Workflow reports are generic by default, with an optional custom organisation/report heading in Settings. Each entry can store a User / Analyst; a session user in the dock is used as the default for new records and reports can filter by user.


## TerraAnalytica QGIS plugin suite

Work Log is part of a family of complementary TerraAnalytica tools for QGIS. Related tools cover layer and map management, labelling, tool discovery, notebooks, spectral analysis and accuracy assessment. Availability varies while the suite is prepared for publication; see the [Work Log homepage](https://terraanalytica.co.nz/qgis-plugins/work-log) for current release information.

## Accuracy and reliability disclaimer

Work Log organises user-entered records and information exposed by QGIS; it does not independently verify that entries, processing history, file references, parameters, reports or workflow descriptions are complete, accurate or suitable for a particular purpose. Review important records against authoritative projects, data and evidence, and keep independent backups. Do not rely on Work Log alone for legal, contractual, safety-critical, regulatory, scientific or professional decisions. Users remain responsible for validating their data, methods, outputs and compliance obligations. The plugin is provided under GPL-2.0-or-later without warranty.

## Supporting development / koha

TA Work Log is intended to be useful to the wider GIS and remote-sensing community. If the plugin saves you time or improves your processing documentation, users may choose to offer a **koha** to support continued development.

Koha is a Māori concept of a voluntary gift or contribution offered in appreciation, reciprocity or acknowledgement of value received. It is optional and does not unlock plugin features. A support link can be added once a public support page is available.


## Visual identity

The plugin UI uses the Layer Lab Gold accent (`#E8A838`) with TerraAnalytica Charcoal (`#202326`) and palette-aware text. Main toolbars use compact icon controls with hover tooltips; the QGIS plugin menu retains descriptive text labels. The product header uses boxed Help and Settings controls, while contextual field explanations use the information symbol.
