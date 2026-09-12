"""
Repository reorganization validator.

Moved from root _validate_reorg.py to scripts/validation/.
Original file preserved at root for backward compatibility.
"""
# Re-import from original location if it exists
try:
    import importlib.util
    import os
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    spec = importlib.util.spec_from_file_location("_validate_reorg", os.path.join(root, "_validate_reorg.py"))
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
except Exception:
    pass
