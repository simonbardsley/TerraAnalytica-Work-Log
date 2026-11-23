"""Build a deterministic QGIS ZIP from the committed standalone release source."""
from __future__ import annotations

import ast
import configparser
import hashlib
import io
import json
from pathlib import Path
import subprocess
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "qgis_worklog"
FIXED_TIME = (2026, 1, 1, 0, 0, 0)


def main():
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    source = subprocess.check_output(["git", "archive", "--format=zip", revision], cwd=ROOT)
    with ZipFile(io.BytesIO(source)) as archive:
        files = {
            name: archive.read(name) for name in archive.namelist()
            if not name.endswith("/") and name.split("/")[0] not in
            {"scripts", "tests", ".github", ".gitignore", ".gitattributes"}
        }
    metadata = configparser.ConfigParser(interpolation=None)
    scan_configs = {".bandit", ".flake8", ".secrets.baseline", ".gitleaks.toml"}
    if any(Path(name).name in scan_configs for name in files):
        raise ValueError("Release contains a security scanner override configuration")
    metadata.read_string(files["metadata.txt"].decode("utf-8"))
    general = metadata["general"]
    if general["author"] != "TerraAnalytica (NZSpatial Limited)":
        raise ValueError("Use the standard TA suite author identity")
    if general["name"] != "TA Work Log" or "ta" not in general["tags"].split(","):
        raise ValueError("TA display name and discovery tag are required")
    version = general["version"]
    module = ast.parse(files["__init__.py"].decode("utf-8"))
    declared = next(ast.literal_eval(node.value) for node in module.body
                    if isinstance(node, ast.Assign) and any(
                        isinstance(target, ast.Name) and target.id == "__version__"
                        for target in node.targets))
    if declared != version:
        raise ValueError("Python and metadata versions differ")
    digest = hashlib.sha256()
    for name, data in sorted(files.items()):
        if name != "resources/BUILD-INFO.json":
            digest.update(name.encode() + b"\0" + data + b"\0")
        if name.endswith(".py"):
            ast.parse(data.decode("utf-8-sig"), filename=name, feature_version=(3, 9))
    receipt = {
        "pluginId": PLUGIN_ID, "version": version, "sourceRevision": revision,
        "sourceArchiveSha256": digest.hexdigest(), "buildRecipe": "scripts/build_release.py",
        "reproducible": True, "licence": "GPL-2.0-or-later",
    }
    # Full hashes belong in the external verification receipt. QGIS scans the
    # embedded receipt for credentials and flags those public hex digests.
    embedded_receipt = {
        "pluginId": PLUGIN_ID, "version": version,
        "sourceRepository": "https://github.com/simonbardsley/TerraAnalytica-Work-Log",
        "sourceTag": f"v{version}", "buildRecipe": "scripts/build_release.py",
        "reproducible": True, "licence": "GPL-2.0-or-later",
    }
    files["resources/BUILD-INFO.json"] = (json.dumps(embedded_receipt, indent=2) + "\n").encode()
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    target = output / f"{PLUGIN_ID}-{version}.zip"
    with ZipFile(target, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            info = ZipInfo(f"{PLUGIN_ID}/{name}", FIXED_TIME)
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compress_type=ZIP_DEFLATED, compresslevel=9)
    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".zip.sha256").write_text(f"{checksum}  {target.name}\n", encoding="utf-8")
    target.with_suffix(".zip.json").write_text(
        json.dumps(dict(receipt, packageSha256=checksum), indent=2) + "\n", encoding="utf-8"
    )
    print(f"{target}\nSHA-256 {checksum}")


if __name__ == "__main__":
    main()
