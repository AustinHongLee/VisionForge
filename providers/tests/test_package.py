"""providers 套件煙霧測試：套件可匯入、可觸及 core 的 provisional 介面。"""

import visionforge_providers  # noqa: F401
from visionforge_core.providers import VisionProvider


def test_package_imports_and_sees_interface():
    assert VisionProvider is not None
