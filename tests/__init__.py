"""Test package marker.

Without this file, ``python -m unittest discover`` run from the project root
does not descend into ``tests/`` and reports "Ran 0 tests".

The non-interactive Agg backend is forced so that chart code can run on
machines without a display and ``plt.show()`` never blocks the test run.
"""
import matplotlib

matplotlib.use("Agg")
