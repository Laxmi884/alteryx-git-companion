"""Smoke test: package is importable."""


def test_package_importable() -> None:
    """Verify that alteryx_diff is importable and has a version string."""
    import alteryx_diff

    assert alteryx_diff.__version__ == "0.1.0"
