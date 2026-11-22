# Work Log release checklist

Target: TA Work Log 1.4.12

## 1.4.12 standard security checks

- [ ] Run standard Bandit checks with no scan configuration files.
- [ ] Run detect-secrets on the shipped package and review findings privately.
- [ ] Run SQL and capability regression tests.
- [ ] Verify optional TA Core discovery and standalone operation.
- [ ] Upload the new version and inspect the QGIS repository's own results.

The 1.4.11 update standardises the author as TerraAnalytica (NZSpatial Limited).

## 1.4.10 naming update

- [x] Public display name is TA Work Log and metadata includes ta/terraanalytica tags.
- [x] Menu, messages, help and README use the same product name.
- [x] Existing package, settings, database and toolbar identifiers are retained.
- [ ] Build the committed source with `python3 scripts/build_release.py`.
- [ ] Upload the 1.4.10 ZIP as a new version of the existing qgis_worklog listing.
- [ ] Confirm the plugin support email and review QGIS approval status.

The checkboxes below record the previous 1.4.9 release baseline.

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
- [x] Commit the approved release source (`062e146`).
- [x] Build the installable ZIP from the committed revision (SHA-256 `175bc01c768df115fa624a9c8b0904d338c3d22b0a832e5f3c3ef01ac68cd65c`).
- [x] Create and push the public `v1.4.9` tag.
- [x] Publish the ZIP, SHA-256 file and build receipt as release assets.
- [x] Select GPL-2.0-or-later and bundle the complete licence as `LICENSE`.

## Public QGIS repository

- [x] Confirm the public Git repository URL.
- [x] Fill `repository`, `tracker` and `homepage` in `metadata.txt`.
- [ ] Add the final release download URL to the QGIS `plugins.xml` catalogue.
- [ ] Validate the catalogue and install through QGIS Plugin Manager.

## Documentation and sales page

- [x] Draft webpage copy, screenshot placements, alt text and related-plugin context in the repository's `docs/WORK_LOG_WEBPAGE_DRAFT.md`.
- [x] Capture approved Light-mode and Dark-mode panel screenshots.
- [x] Capture New Entry, Reports, Workflows and Help screenshots.
- [x] Add useful alt text and captions for every screenshot.
- [x] Produce the dedicated TerraAnalytica Work Log webpage.
- [x] Add features, workflows, compatibility, support, pricing and related-plugin context.
- [ ] Link the website, Git release and QGIS repository in both directions.

Release is complete only when every unchecked item above is resolved or explicitly waived.
