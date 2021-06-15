__all__ = ["base_tm", "machine_translation"]

import importlib
list_of_widgets = []
#list_of_workers = []
for module in __all__:
	list_of_widgets.append([importlib.import_module("plugins." + module).main_widget, importlib.import_module("plugins." + module).main_worker])
	#list_of_workers.append(importlib.import_module("plugins." + module).main_worker)