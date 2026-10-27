"""Load the pure-Python modules without importing Home Assistant."""
import importlib
import pathlib
import sys
import types

_PKG = "sagemcom_wan_pure"
if _PKG not in sys.modules:
    pkg = types.ModuleType(_PKG)
    pkg.__path__ = [str(pathlib.Path(__file__).parents[1] / "custom_components" / "sagemcom_wan")]
    sys.modules[_PKG] = pkg

wan_detect = importlib.import_module(f"{_PKG}.wan_detect")
metrics = importlib.import_module(f"{_PKG}.metrics")
