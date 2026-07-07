import pytest

from src import config
from src.services.assets import resolve_asset_path


def test_resolve_asset_path_normal_relative(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ASSETS_DIR", str(tmp_path))
    resolved = resolve_asset_path("dive1/image.jpg")
    assert resolved == (tmp_path / "dive1" / "image.jpg").resolve()
    assert resolved.is_relative_to(tmp_path.resolve())


def test_resolve_asset_path_rejects_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ASSETS_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        resolve_asset_path("../secret.txt")


def test_resolve_asset_path_rejects_absolute(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ASSETS_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        resolve_asset_path("/etc/passwd")


def test_resolve_asset_path_rejects_nested_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ASSETS_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        resolve_asset_path("dive1/../../secret.txt")


def test_resolve_asset_path_rejects_nul_byte(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ASSETS_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        resolve_asset_path("dive1/img\x00.jpg")


def test_resolve_asset_path_rejects_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ASSETS_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        resolve_asset_path("")


def test_resolve_asset_path_rejects_assets_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ASSETS_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        resolve_asset_path(".")


def test_resolve_asset_path_nested_relative_stays_within(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ASSETS_DIR", str(tmp_path))
    resolved = resolve_asset_path("dive1/sub/image.png")
    assert resolved == (tmp_path / "dive1" / "sub" / "image.png").resolve()
    assert resolved.is_relative_to(tmp_path.resolve())
