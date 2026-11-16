# Changelog

## 1.4.8

- Create portable Work Log backups and restore independent copies from Settings.

## 1.4.7

- Explain Untitled archive, filters and window placement in the built-in Help and bundled guide.

## 1.4.6

- Clear Untitled when its QGIS project closes and keep saved notes, workflows and attachments in Untitled archive.

## 1.4.5

- Stop style-generated palette events from repeatedly refreshing Work Log widgets.

## 1.4.4

- Keep Save and Cancel in a fixed footer below the scrollable entry form.

## 1.4.3

- Confirm saved entries and show when filters hide them.
- Widen the User / analyst field in New Entry.
- Save entry and attachment records atomically and restore settings persistence.
- Return Work Log to its previous dock area on the first dock-back action.

## 1.4.2

- Use a standard desktop window for the popped-out Work Log.
- Show dedicated Pop out, Dock in QGIS, and Move to monitor controls.

## 1.4.1

- Align the New Entry information buttons and improve dialog handling.
- Pop Work Log out of QGIS, move it to another monitor, or dock it again.

## 1.4.0

- Matched the current TerraAnalytica product header with boxed **Help** and **Settings** controls.
- Added the compact plugin version beside the capability subtitle.
- Added embedded deterministic build provenance and release-readiness tests.
- Synchronised the README, bundled help and Plugin Manager metadata for the completion release.

## 1.3.1

- Removed the Gold divider from the Charcoal header band.
- Added the Layer Lab-style capability line **Work diary · reporting · processing provenance** beneath the Work Log title.

## 1.3.0

- Established the shared TerraAnalytica plugin header: a persistent Charcoal band, Gold `TERRAANALYTICA` eyebrow, white functional title and Gold divider.
- Kept the header visually identical in light and dark modes while making the complete content area, controls, text, borders, selections and icons respond to the active QGIS palette.
- Added a light header-icon rendering path so Charcoal SVG linework remains visible on the Charcoal band.
- Retained the short **Work Log** dock-tab label.

## 1.2.9

- Refined the Work Log dock against Layer Lab 1.0.0 with its Gold outer border, native compact header typography, frameless filter block and tighter four-pixel rhythm.
- Matched Layer Lab's borderless, non-alternating content tree and understated nine-pixel status/footer treatment.
- Kept the QGIS dock tab label as **Work Log**.

## 1.2.8

- Restyled the Work Log dock to match Layer Lab 1.0.0: compact six-pixel shell, four-pixel spacing, uppercase Gold section header and Gold divider.
- Aligned the Gold accent, compact three-pixel control corners, borderless tree and selected-row treatment with Layer Lab.
- Shortened the QGIS dock tab label from **TA Work Log** to **Work Log**.

## 1.2.7 — Unified TA light/dark interface

- Aligned Work Log with the TerraAnalytica Toolsearch Panel visual system.
- Added palette-aware light/dark styling derived from the active QGIS/Qt theme while retaining TA Gold as the accent.
- Added the shared `TERRAANALYTICA` Gold brand label and compact Work Log titles across the dock and major dialogs.
- Shortened the dock/toolbar label to **TA Work Log** while keeping **TerraAnalytica Work Log** as the full Plugin Manager identity.
- Added a settings control beside `?` Help in the Work Log header and retained `ⓘ` for field-specific explanations.
- Made common form controls, tables, tabs and compact action buttons follow the same Gold/Charcoal/palette-aware treatment as Toolsearch.
- Added palette-aware TA action icons so Charcoal linework remains legible in dark mode; the master Work Log logo remains fixed Gold/Charcoal.
- Changed workflow diagram connectors/box outlines to TA Gold for a consistent provenance visual language.
- Kept exported Work Log/Workflow reports neutral or user-branded, separate from plugin UI branding.

## 1.2.6 — TerraAnalytica UI / chart branding

- Updated the main plugin icon and bundled action icons to TerraAnalytica Gold (`#E3B54C`) and Charcoal (`#202326`).
- Converted the main dock actions, search controls, report exports and common Workflow controls to compact icon buttons with hover tooltips and accessible names.
- Kept descriptive text commands in the QGIS plugin menu for discoverability.
- Changed general Help controls to a question-mark icon; field-specific explanations continue to use the information symbol.
- Changed report and on-screen bar charts to TA Gold while retaining neutral/charcoal print typography.
- Updated Help and README documentation for the icon conventions and visual identity.

## 1.2.5
- Fixed PDF/Print chart clipping when report charts contained more rows than the on-screen Reports dialog could display.
- Reports now render charts to dedicated print images with protected geometry instead of screen-grabbing the live widgets.
- Added explicit chart image dimensions so the By user / Top tags summaries stay below the full chart row rather than covering lower categories or dates.
- Kept the compact two-page landscape report structure introduced in v1.2.4.

## 1.2.4
- Reduced PDF/Print tag summary to the top 8 tags so compact reports normally fit the summary on page 1 and detailed entries on page 2.
- Standardised CSV timestamps to ISO 8601 local form (`YYYY-MM-DDTHH:MM:SS`).
- User/analyst hour summaries now display two decimal places and include a total row to avoid apparent one-decimal rounding mismatches.
- Slightly refined report metadata typography while retaining the compact landscape layout.
- Improved timeline timestamp parsing so both legacy space-separated and ISO `T` timestamps group consistently.

## 1.2.3
- Expanded Plugin Manager metadata to describe GIS/remote-sensing logging, reporting and processing-provenance features more clearly.
- Updated built-in Help, HELP.md and README for custom report identity, session/default analysts and multi-user reporting.
- Added a short, optional koha/support-development explanation.
- Defined koha as a voluntary contribution in appreciation/reciprocity; it does not unlock features.
- Corrected README version/schema references for the current database generation.


## 1.2.2
- Refined PDF/print typography and page composition for compact professional output.
- Work Log reports now default to A4 landscape; Workflow Records use compact A4 portrait.
- Exported reports are generic by default rather than TerraAnalytica-branded.
- Added optional custom report organisation/heading in Settings.
- Added per-entry User / Analyst attribution and a session user selector.
- Added report filtering and CSV/PDF attribution by user.
- Demo data now includes multiple example analysts.

## 1.2.1

- Added an opt-in **GIS / Remote Sensing Demo Pack** with realistic recent work-log records.
- Demo data includes two projects, multiple work classes/tags, three reproducible workflows, final parameters and inputs/outputs.
- Demo dates are generated relative to installation time so day/week/month Reports are immediately meaningful.
- Added **Load / Reset Demo Data…** and **Remove Demo Data…** menu actions.
- Demo projects are explicitly marked in database schema v4 so removal cannot delete normal user projects.
- Added a built-in **Help & Use Cases** window accessible from the plugin menu and dock ⓘ control.
- Added bundled `HELP.md` documentation covering logging, reporting, workflows, final parameters, exports and GIS/remote-sensing examples.
- Added practical use cases for Sentinel-2 vegetation monitoring, Sentinel-1 SAR processing, drone orthomosaics, QGIS spatial analysis, ground-truth campaigns and R&D method development.

## 1.2.0

- Added **CSV export** for the currently filtered Work Log report records.
- Added **PDF report export** with report totals, charts, tag attribution and matching entries.
- Added **Print** support for the current Work Log report.
- Added a first-class **GIS / Remote Sensing Workflow** manager.
- Workflow records store name, purpose/result, version, status, method notes, QGIS version and platform.
- Added ordered workflow steps with manual step capture for QGIS, remote-sensing software, scripts, notebooks, fieldwork and external services.
- Added **QGIS Processing History import**, retaining algorithm ID, inputs/parameters, Python command, `qgis_process` command, timestamp and execution log when supplied by QGIS.
- Added editable **Final Parameters** tables for reproducibility-critical values such as CRS, pixel size, resampling method, thresholds and model settings.
- Added **Inputs & Outputs** records for datasets, assets, files, catalogue IDs and generated products.
- Added an automatically generated dependency-free **workflow process diagram**.
- Added workflow PDF/print reports containing workflow metadata, diagram, ordered steps, final parameters and inputs/outputs.
- Work Log entries can optionally be linked to a workflow.
- Database schema upgraded from v2 to v3 in place; existing entries are preserved.
- Improved FTS5 migration so a full-text index is rebuilt safely if FTS becomes available after previously being unavailable.

## 1.1.0

- Rebranded plugin as **TerraAnalytica Work Log**.
- Added field-level **ⓘ help** aimed at GIS and remote-sensing technical records.
- Added a first-class **Tags** field for sensors, datasets, software, methods and themes.
- Search now covers tags as well as titles/descriptions.
- Added tag filtering to the main Work Log panel.
- Added a **Reports** window with project, work-class, tag and date filters.
- Added graphical summaries for hours by work class, day/week/month and project.
- Added total hours, record count, active days, average hours per active day and top-tag attribution.
- Expanded default work classes for GIS / remote sensing, field ground truth, coding, QA/QC, research and reporting.
- Database schema upgraded from v1 to v2 in place; existing records are preserved.
- Retains optional FTS5 search with LIKE fallback when FTS5 is unavailable.
- Maintains QGIS 3 / QGIS 4 compatibility approach using `qgis.PyQt` and scoped Qt enums.

## 1.0.2

- Made FTS5 optional instead of fatal to database startup.
- Improved database path handling and error reporting.
