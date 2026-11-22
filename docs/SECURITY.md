# Release security scope

## Scanner configuration

Version 1.4.12 removes `.bandit` and its broad B608 exclusion. Entry updates,
entry search (FTS and LIKE), reporting and workflow listing now use fixed SQL
statements with bound values. No B608 suppression is required.

The release builder rejects packaged scanner override configuration files.
Regression tests cover partial updates, explicit NULLs, project isolation,
date filters, pagination, search and SQL-like user text.

## Optional local integrations

Work Log exposes four UI actions through TA Core's existing capability discovery
contract. Core and AI Central remain optional. The descriptor exports no log
contents, database path, analyst information, attachment data or credentials.
The actions open existing user interfaces. Saving entries still requires the
user to complete the editor.

This release includes no provider key, account token, personal database, provider
configuration or bundled user profile. Work Log does not configure a network
endpoint or issue AI provider requests. AI Central retains responsibility for
its own explicitly configured providers and user-controlled sharing policy.

Inspect the final archive with Bandit and detect-secrets before publication.
The QGIS repository must run its own scan after upload. Local checks cannot
guarantee its approval result.
