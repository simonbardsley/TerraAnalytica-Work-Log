# Work Log release checklist

Target: TerraAnalytica Work Log 1.4.8

## Product and runtime

- [x] QGIS metadata declares QGIS 3.22 through 4.x compatibility.
- [x] Python sources compile with Python 3.9 and current Python.
- [x] Light/dark theme support and the shared TerraAnalytica header are present.
- [x] Boxed Help and Settings controls are present.
- [x] Built-in help, workflows, reports, demo data and exports are documented.
- [ ] Complete hands-on runtime checks in QGIS 3.22.
- [ ] Complete hands-on runtime checks in a current QGIS 3.x LTR.
- [x] Complete hands-on runtime checks in QGIS 4.2.3 on macOS.
- [x] Legacy schema migration and entry preservation are covered by an automated test.

## Git and packaging

- [x] Canonical source is maintained in the TerraAnalytica platform Git repository.
- [x] Deterministic package builder and embedded build provenance are present.
- [x] Automated release-contract tests are present.
- [x] Commit the approved release source (`f6bf55c`).
- [x] Build the installable ZIP from the committed revision (SHA-256 `28b046f449b0664dad4d160c12169ed6bc37e7d3c9d35a233f1c8e876246868c`).
- [x] Create and push the `qgis-worklog-v1.4.8` tag.
- [ ] Publish the ZIP, SHA-256 file and build receipt as release assets.
- [ ] Complete licence selection/review before public distribution.

## Public QGIS repository

- [ ] Confirm the public Git repository URL.
- [ ] Fill `repository`, `tracker` and `homepage` in `metadata.txt`.
- [ ] Add the final release download URL to the QGIS `plugins.xml` catalogue.
- [ ] Validate the catalogue and install through QGIS Plugin Manager.

## Documentation and sales page

- [x] Draft webpage copy, screenshot placements, alt text and related-plugin context in the repository's `docs/WORK_LOG_WEBPAGE_DRAFT.md`.
- [x] Capture approved Light-mode and Dark-mode panel screenshots.
- [x] Capture New Entry, Reports, Workflows and Help screenshots.
- [x] Add useful alt text and captions for every screenshot.
- [ ] Produce the dedicated TerraAnalytica Work Log webpage.
- [ ] Add features, workflows, compatibility, support, pricing and related-plugin context.
- [ ] Link the website, Git release and QGIS repository in both directions.

Release is complete only when every unchecked item above is resolved or explicitly waived.
