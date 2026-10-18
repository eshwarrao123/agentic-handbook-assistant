"""Agentic Handbook Assistant backend application package."""

import sys

# Defense against contaminated PYTHONPATH environment variables pointing across Python versions
# (e.g. C:\Python313\Lib\site-packages in PYTHONPATH while running Python 3.14)
if sys.version_info.major == 3 and sys.version_info.minor != 13:
    sys.path = [p for p in sys.path if "Python313" not in p]
