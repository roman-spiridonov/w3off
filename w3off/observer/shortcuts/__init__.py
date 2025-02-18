import w3off.observer.shortcuts.erc20Tx as erc20Tx
import w3off.observer.shortcuts.customTx as customTx

# Load shortcuts dynamically:
# import pkgutil
# import importlib
# available_shortcuts = []
# for module_info in pkgutil.iter_modules(__path__):
#     module = importlib.import_module(f".{module_info.name}", __package__)
#     shortcuts_name = getattr(module, 'name', module_info.name)
#     # Add customTx first, append others
#     if module_info.name == 'customTx':
#         available_shortcuts.insert(0, shortcuts_name)
#     else:
#         available_shortcuts.append(shortcuts_name)

available_shortcuts = [customTx.name, erc20Tx.name]  # default
