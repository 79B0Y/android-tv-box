import json
from pathlib import Path


def test_manifest_domain_and_version_match_version_file():
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = repo_root / "custom_components" / "android_tv_box" / "manifest.json"
    version_file = repo_root / "VERSION"

    assert manifest_path.exists(), f"Missing manifest at {manifest_path}"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert data.get("domain") == "android_tv_box"
    assert "version" in data, "manifest.json must set a version"

    # VERSION file should match manifest version (trim to handle newline absence)
    version_txt = version_file.read_text(encoding="utf-8").strip()
    assert data["version"] == version_txt


def test_manifest_has_required_dependency():
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = repo_root / "custom_components" / "android_tv_box" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    reqs = data.get("requirements") or []
    assert any(r.startswith("adb-shell") for r in reqs), "adb-shell must be declared in manifest requirements"

