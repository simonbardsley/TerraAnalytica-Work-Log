# TerraAnalytica Work Log — Help and Use Cases

**Purpose:** a lightweight QGIS work diary, reporting tool and processing-provenance recorder designed specifically for GIS, Earth observation and remote-sensing work. The interface uses Layer Lab Gold (`#E8A838`) and TerraAnalytica Charcoal (`#202326`) accents while remaining compatible with QGIS themes.


## Interface icons and help

The main Work Log, Reports and Workflow controls use compact TerraAnalytica Gold/Charcoal icons so the plugin stays tidy inside QGIS. The product header uses boxed **Help** and **Settings** controls consistent with the wider TerraAnalytica plugin family. Hover over an icon to see its tooltip and action. Descriptive text is retained in the QGIS **Plugins > TerraAnalytica Work Log** menu for discoverability.

- **Help** — opens the complete guide and use-case workflows.
- **ⓘ** — explains the specific field or concept beside it.
- Gold-accent action icons identify common operations such as new entry, edit, reports, workflows, export and print.

## Interface, branding and light/dark mode

The plugin interface establishes the shared TerraAnalytica application family for **Work Log** and the Lab plugins. The full product name remains **TerraAnalytica Work Log**, while the dock tab is shortened to **Work Log**. Its fixed Charcoal band uses a Gold `TERRAANALYTICA` eyebrow, white functional title and the short capability statement `Work diary · reporting · processing provenance`.

Below the fixed brand band, Work Log follows the active QGIS/Qt light or dark palette. **Layer Lab Gold (`#E8A838`)** remains the accent. In light mode primary linework/text uses **TA Charcoal (`#202326`)**; in dark mode linework, surfaces and text follow the system palette for contrast while retaining Gold accents. Use the boxed **Help** control for the complete guide and **ⓘ** for field-specific explanations.

This branding applies to the plugin interface only. PDF/print outputs remain neutral by default or can use the organisation name configured under **Settings → Reporting & User**.

## Quick start

1. Open or save a QGIS project.
2. Select the current **User / Analyst** in the Work Log dock.
3. Create a **New Entry** and record work class, time, title, description and useful tags.
4. Use **Reports** to review hours by day/week/month, project, analyst, work class and tag.
5. Create a **Workflow** when a method needs to be understood or repeated.
6. Record ordered steps, final parameters, inputs and outputs; import QGIS Processing History where appropriate.
7. Export work reports as CSV/PDF or print them. Workflow method records can also be exported or printed.

## Window placement

Choose **Pop out** in the Work Log header to open a separate desktop window. Drag its title bar or choose **Move to monitor** to select a display detected by QGIS. Choose **Dock in QGIS** to return the panel to the main window.

## Back up and restore Work Log

Open **Settings → Database → Create backup** to save a ZIP containing the current Work Log database and its available attachments. Work Log reports any attachment whose file and embedded copy are both missing.

To recover a backup or move it to another computer, open **Settings → Database → Restore backup**, select the ZIP, and choose a destination folder. Work Log creates a new folder there with its own database and attachment files. Choose **Yes** to open the restored copy, or **No** to keep using your current database. You can switch between copies later using **Settings → Database → Browse**.

## Notes from an untitled project

You can log work before saving the QGIS project. Those entries appear under **Untitled** in Work Log.

When you close the untitled QGIS project, Work Log moves its saved notes and workflows to **Untitled archive**. Attachments stay linked to their entries. The next untitled project starts with an empty Work Log.

To find an archived note, click **Switch project** next to the project name and choose **Untitled archive**. If a search or date filter hides the note, click **Clear filters**.

## Work-log entries

A work-log entry records **what was done, by whom, when and for how long**.

Typical fields include:

- **Project** — the body of work the entry belongs to.
- **User / Analyst** — the person who performed the work.
- **Work class** — a broad reporting category such as Remote Sensing, GIS / Spatial Analysis, Fieldwork / Ground Truth, QA / QC or Documentation / Reporting.
- **Title** — a short, recognisable activity name.
- **Description** — enough technical detail to understand what happened and why.
- **Tags** — specific sensors, datasets, tools, methods, sites or themes.
- **Duration** — time spent on the activity.
- **Workflow** — an optional link to a repeatable method record.

### Work class vs tags

Use **Work class** for a broad reporting category and **Tags** for detail.

Example:

- Work class: `Remote Sensing`
- Tags: `Sentinel-1, SAR, VV, VH, Gamma0, SNAP, pasture`

A small, consistent tag vocabulary makes later search and reporting much more useful.

## Users, analysts and sessions

Each entry can record the **User / Analyst** who performed the work.

The user selected in the main Work Log dock acts as the active **session user** and is pre-filled on new entries. It can be changed during the session, and an individual entry can override it.

An optional persistent **Default user / analyst** can be set under **Settings > Reporting & User**. Reports can be filtered by analyst, and CSV/PDF exports retain the user attribution.

Changing the session user affects new records only; existing records keep the user stored with them.

This supports both individual use and shared project databases.

## Reports and export

Reports can be filtered by:

- project;
- user / analyst;
- work class;
- tag; and
- date range.

They summarise total hours, number of entries, active work days, average hours per active day, hours by work class, hours over time, hours by project, user attribution and top tags.

Export options:

- **CSV** — detailed filtered records for spreadsheet analysis, audit or archive. Exported timestamps use consistent ISO 8601 local format (`YYYY-MM-DDTHH:MM:SS`).
- **PDF** — a compact formatted report with the current filters, summaries, charts, top 8 tags and matching records.
- **Print** — sends the same report to the system print workflow.

Tag totals can overlap. A two-hour entry tagged both `Sentinel-2` and `NDVI` contributes two hours to each tag attribution, so tag totals should not be summed.

User-hour summaries use two decimal places and include a total row so displayed analyst subtotals remain consistent with the underlying durations.

## Report identity and document branding

The plugin itself is branded **TerraAnalytica Work Log**, but generated documents are deliberately generic by default so they can be used by individuals, consultancies, research groups and organisations.

Under **Settings > Reporting & User**, set an optional **Report organisation / heading**. For example, `Acme Spatial` produces `Acme Spatial - Work Log Report`. Leave it blank to use the neutral titles **Work Log Report** and **Workflow Record**.

Work Log PDF reports use a compact A4 landscape layout for activity tables and TA Gold charts. Workflow Records use A4 portrait. Report charts are rendered with protected print geometry so long class/date lists are not clipped by the summary tables below them.

## When to create a workflow

A normal entry records *what you did and how long it took*. A **Workflow** records *how a result was produced so it can be understood or repeated*.

A workflow can include:

1. **Purpose / result** — what the method is intended to produce.
2. **Ordered steps** — QGIS Processing operations and/or manual steps from SNAP, Python, R, Google Earth Engine, drone/photogrammetry software, fieldwork or other systems.
3. **Final Parameters** — the values that define the accepted method.
4. **Inputs & Outputs** — datasets, catalogue IDs, paths, database tables, rasters, vectors and generated products.
5. **Version and status** — so Draft/Active methods can be distinguished from a Final method.
6. **Process diagram** — generated from the recorded workflow steps.

### What belongs in Final Parameters?

Record values that could materially change the scientific or spatial result, for example:

- CRS, pixel size, resampling method and NoData handling;
- band selection and index equations;
- cloud, classification or quality thresholds;
- SAR calibration/backscatter convention and speckle-filter settings;
- DEM / terrain-correction source;
- buffer distances, tolerances, kernels and neighbourhood sizes;
- model type, important hyperparameters and random seed;
- zonal-statistics or aggregation method; and
- drone altitude, overlap, GSD and control/check-point method.

**Rule of thumb:** if changing a value could change the output, record it.

### QGIS Processing History

Where QGIS exposes a Processing History record, Work Log can import the algorithm and the execution information supplied by QGIS. Use manual steps for work performed outside QGIS Processing or for conceptual, interpretation or QA steps that still matter to reproducibility.

## GIS and remote-sensing use cases

### Sentinel-2 vegetation monitoring

Acquire L2A → cloud/quality mask → clip AOI → NDVI/red-edge metrics → zonal statistics → QA/QC → output.

Useful tags: `Sentinel-2, NDVI, red edge, vegetation, cloud mask, zonal statistics`.

### Sentinel-1 SAR processing

Acquire GRD → calibration → speckle handling → terrain correction → VV/VH metrics → polygon statistics → QA/QC.

Record orbit direction, relative orbit where relevant, polarisation, backscatter convention, dB/linear representation, DEM and terrain-correction settings.

### Drone orthomosaic and spatial QA

Flight/capture → alignment → surface/orthomosaic → CRS/export → independent check → QA summary.

Record flight altitude, overlap, sensor/camera mode, GSD, control/check points and accuracy statistics.

### QGIS spatial analysis

Inputs → geometry/data QA → reprojection → buffer/intersection/join → calculations/statistics → QA → export.

Record CRS, tolerance, buffer distance, join keys, geometry fixes and output format.

### Ground truth linked to imagery

Sampling plan → observations/GPS/photos → QA → match to satellite/drone acquisition → validation → archive.

Tags can identify sensor, paddock/site, overpass, instrument or campaign.

### R&D / method development

Use ordinary work-log entries to record experiments, time and decisions. Keep the accepted production or scientific method in a versioned Workflow with its final parameters and inputs/outputs.

## Demo / template data

The plugin menu contains **Load / Reset Demo Data** and **Remove Demo Data**.

The demo includes:

- **DEMO — Hauraki Pasture Remote Sensing** — multi-day Sentinel-2, Sentinel-1, field validation, coding, QA and reporting records;
- **DEMO — Drone Orthomosaic & QA** — a smaller drone mapping example; and
- realistic workflows with steps, final parameters, inputs/outputs and multiple example analysts.

Demo dates are generated relative to the current date so daily, weekly and monthly Reports are immediately meaningful.

Demo projects are explicitly marked in the database. Resetting or removing the demo affects only demo-marked projects and does not delete normal user projects.

## Accuracy, reliability and responsible use

Work Log helps organise user-entered records and information exposed by QGIS, but it does not independently verify that entries, imported processing history, file references, parameters, durations, reports or workflow descriptions are complete, accurate or suitable for a particular purpose.

- Review important records and exported reports against the source project, data and processing history.
- Keep independent backups and preserve authoritative project files and evidence.
- Do not rely on Work Log alone for legal, contractual, safety-critical, regulatory, scientific or professional decisions.
- Results may also depend on QGIS, third-party providers, plugins, data quality and the user's configuration.

Users remain responsible for validating their data, methods, outputs and compliance obligations. Work Log is provided under the GPL-2.0-or-later licence without warranty.

## Related TerraAnalytica QGIS tools

Work Log is part of a wider family of complementary TerraAnalytica tools for QGIS. The suite includes focused tools for layer and map management, labelling, tool discovery, notebooks, spectral analysis and accuracy assessment.

Related tools include **Layer Lab**, **Map Lab**, **Label Lab**, **Toolsearch**, **Notebook Lab**, **Spectral Lab** and **Accuracy Lab**. Availability and release status vary while the suite is prepared for publication. Visit the Work Log homepage for current releases and suite information.

## Koha and supporting development

If TerraAnalytica Work Log saves you time or improves the reproducibility of your GIS/remote-sensing work, you may choose to support its ongoing development with a **koha**.

**Koha** is a Māori concept commonly used for a voluntary gift or contribution offered in appreciation, reciprocity or acknowledgement of value received.

For TerraAnalytica Work Log, koha is entirely optional: it is not a purchase requirement and it does not unlock features.

A public support destination can be linked from the plugin homepage when one is available.

## Good practice

- Write titles so they still make sense six months later.
- Use a small, consistent vocabulary for tags.
- Log QA/QC as work, not as an afterthought.
- Record dataset/product identifiers where possible, not just vague filenames.
- Finalise workflow parameters when a method becomes accepted or operational.
- Create a new workflow version when a method changes materially rather than silently overwriting its history.
- Export periodic PDF/CSV records when evidence, auditability or R&D documentation matters.
