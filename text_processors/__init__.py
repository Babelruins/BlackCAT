__all__ = ["punkt", "odt"]

import importlib
for module in __all__:
	importlib.import_module("text_processors." + module)