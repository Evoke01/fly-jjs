import os
import tempfile

import fly_jjs  # noqa: F401  (sets single-threaded BLAS before any test imports numpy)

# Tests write weights, profiles and configs. Keep them away from the real ~/.fly_jjs
# (this runs before any test module imports fly_jjs).
os.environ.setdefault("FLY_JJS_HOME", tempfile.mkdtemp(prefix="fly_jjs_tests_"))
