"""Run one script under splitguard as documented (`import splitguard.auto` before scikit-learn is imported) and
print its findings as JSON. Invoked with splitguard's own interpreter: python splitguard_wrapper.py SCRIPT"""

import json
import os
import runpy
import sys

import splitguard.auto  # noqa: F401  (documented one-line mode; must precede the script's sklearn imports)
from splitguard import _core

script = os.path.abspath(sys.argv[1])
status, error = "ok", None
try:
    sys.argv = [script]
    runpy.run_path(script, run_name="__main__")
except BaseException as e:  # noqa: BLE001
    status, error = "error", f"{type(e).__name__}: {e}"
found = _core.report()
os.environ["SPLITGUARD_DISABLE"] = "1"
print("SPLITGUARD_JSON " + json.dumps({"status": status, "error": error, "findings": [
    {"estimator": f.estimator, "pattern": f.pattern, "call_site": f.call_site, "leaked": f.leaked_rows,
     "fit_rows": f.fit_rows} for f in found]}))
