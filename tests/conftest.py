"""Make pure Octi modules importable without installing Home Assistant."""

from __future__ import annotations

import sys
import types
from pathlib import Path

package_root = Path(__file__).parents[1] / "custom_components"
octi_root = package_root / "octi"

custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(package_root)]
sys.modules.setdefault("custom_components", custom_components)

octi_package = types.ModuleType("custom_components.octi")
octi_package.__path__ = [str(octi_root)]
sys.modules.setdefault("custom_components.octi", octi_package)
