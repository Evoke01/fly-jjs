import os
import tempfile

# Tests write weights, profiles and configs. Keep them away from the real ~/.fly_jjs
# (this runs before any test module imports fly_jjs).
os.environ.setdefault("FLY_JJS_HOME", tempfile.mkdtemp(prefix="fly_jjs_tests_"))
