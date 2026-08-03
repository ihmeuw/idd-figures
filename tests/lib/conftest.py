"""Force a headless Agg backend for all lib figure tests."""

import matplotlib as mpl

mpl.use("Agg")
