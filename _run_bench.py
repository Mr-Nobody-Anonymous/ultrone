import sys, traceback
try:
    import pytest
    rc = pytest.main(["tests/test_fault_injection.py", "-q", "-p", "no:cacheprovider"])
    sys.stdout.write(f"\nPYTEST_EXIT={rc}\n")
except BaseException:
    sys.stdout.write(traceback.format_exc())
