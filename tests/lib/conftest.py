"""Force a headless Agg backend for all lib figure tests."""

import matplotlib

matplotlib.use("Agg")
