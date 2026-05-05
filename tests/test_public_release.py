from pathlib import Path

from scripts.prepare_public_release import copy_project, validate


def test_public_release_artifact_excludes_private_files(tmp_path):
    destination = tmp_path / "enterprise-rag-public"
    copy_project(destination)
    errors = validate(destination)
    assert errors == []
    assert (destination / "README.md").exists()
    assert (destination / "demo" / "enterprise-rag-dashboard.png").exists()
    assert not (destination / "docs" / "issues.md").exists()
    assert not (destination / "docs" / "public-release.md").exists()
    assert not (destination / "scripts" / "prepare_public_release.py").exists()
    assert not any(path.suffix == ".db" for path in destination.rglob("*"))
