"""ctypes bridge to the C99 beeswarm kernel (extraction step 4, 2026-09-02).

The kernel is ``_c/beeswarm_core.c``; ``build()`` compiles it with gcc into
``_c/libbeeswarm_core.so`` next to the source (gitignored via ``*.so``), and
``lib()`` loads it on first use, building if needed. ctypes was chosen over
cffi because it is in the standard library and the venv has no cffi; a
shipped package would use a proper extension and wheels (see the record's
Step 5). The functions mirror ``beeswarm_core._layout_swarm`` and
``_layout_phi`` exactly: dimensionless inputs (D = 1), same tie-break rule.
"""

import ctypes
import functools
import pathlib
import subprocess

import numpy as np
from numpy.ctypeslib import ndpointer

_HERE = pathlib.Path(__file__).resolve().parent / "_c"
SRC = _HERE / "beeswarm_core.c"
LIB = _HERE / "libbeeswarm_core.so"
_F64 = ndpointer(np.float64, flags="C_CONTIGUOUS")
_I64 = ndpointer(np.int64, flags="C_CONTIGUOUS")


def build():
    """Compile the kernel. One gcc invocation, libm only."""
    cmd = ["gcc", "-O2", "-std=c99", "-shared", "-fPIC", "-o", str(LIB), str(SRC), "-lm"]
    subprocess.run(cmd, check=True)  # noqa: S603  fixed argv, no user input
    return LIB


def available():
    """True if a compiled kernel at least as new as its source is present. Never
    builds: compiling implicitly inside a consumer's site-packages is not
    acceptable, so "auto" dispatch asks this and ``build()`` stays explicit."""
    return LIB.exists() and LIB.stat().st_mtime >= SRC.stat().st_mtime


@functools.cache
def lib():
    """Load the compiled kernel, building it first if missing or stale. Raises
    RuntimeError when it cannot be provided (no compiler, read-only tree)."""
    if not available():
        try:
            build()
        except (OSError, subprocess.CalledProcessError) as exc:
            msg = f"beeswarm C kernel unavailable ({exc}); build it with idd_figures.beeswarm_c.build()"
            raise RuntimeError(msg) from exc
    L = ctypes.CDLL(str(LIB))
    L.bs_layout_swarm.restype = ctypes.c_int
    L.bs_layout_swarm.argtypes = [ctypes.c_int64, _F64, _F64, _I64, ctypes.c_int, _F64]
    L.bs_layout_phi.restype = ctypes.c_int
    L.bs_layout_phi.argtypes = [
        ctypes.c_int64,
        _F64,
        _F64,
        _I64,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        _F64,
        _F64,
    ]
    L.bs_phi_best.restype = ctypes.c_int
    L.bs_phi_best.argtypes = [
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int64,
        _F64,
        _F64,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        _F64,
    ]
    L.bs_spine_drop.restype = ctypes.c_int
    L.bs_spine_drop.argtypes = [
        ctypes.c_int64,
        _F64,
        _F64,
        _F64,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        _F64,
        _F64,
    ]
    L.bs_ellipse_closest.restype = ctypes.c_int
    L.bs_ellipse_closest.argtypes = [
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        _F64,
    ]
    return L


def ellipse_closest(qx, qy, alpha, beta):
    """C twin of ``beeswarm_core._ellipse_closest`` for one query point."""
    out = np.empty(2)
    lib().bs_ellipse_closest(float(qx), float(qy), float(alpha), float(beta), out)
    return out[0], out[1]


def phi_best(ai, bi, PA, PB, phi, one_sided=False, val_bounds=None):
    """C twin of ``beeswarm_core._phi_best`` (one point). Returns (a, b, cost) or None."""
    PA = np.ascontiguousarray(PA, dtype=np.float64)
    PB = np.ascontiguousarray(PB, dtype=np.float64)
    out = np.empty(3)
    has_b = val_bounds is not None
    lo, hi = (float(val_bounds[0]), float(val_bounds[1])) if has_b else (0.0, 0.0)
    rc = lib().bs_phi_best(
        float(ai), float(bi), PA.size, PA, PB, float(phi), int(one_sided), int(has_b), lo, hi, out
    )
    return None if rc else (out[0], out[1], out[2])


def _prep(off, val, order):
    off = np.ascontiguousarray(off, dtype=np.float64)
    val = np.ascontiguousarray(val, dtype=np.float64)
    order = np.ascontiguousarray(order, dtype=np.int64)
    if not (off.shape == val.shape == order.shape):
        msg = "off, val, order must have the same length"
        raise ValueError(msg)
    return off, val, order


def layout_swarm(off, val, order, one_sided=False):
    """C twin of ``beeswarm_core._layout_swarm``. Returns new offsets or None."""
    off, val, order = _prep(off, val, order)
    out = np.empty_like(off)
    rc = lib().bs_layout_swarm(off.size, off, val, order, int(one_sided), out)
    return None if rc else out


def layout_phi(off, val, order, phi, one_sided=False, val_bounds=None):
    """C twin of ``beeswarm_core._layout_phi``. Returns (new_off, new_val) or None."""
    off, val, order = _prep(off, val, order)
    out_a = np.empty_like(off)
    out_b = np.empty_like(val)
    has_b = val_bounds is not None
    lo, hi = (float(val_bounds[0]), float(val_bounds[1])) if has_b else (0.0, 0.0)
    rc = lib().bs_layout_phi(
        off.size, off, val, order, float(phi), int(one_sided), int(has_b), lo, hi, out_a, out_b
    )
    return None if rc else (out_a, out_b)


_BIN_ORDER = {"middle-out": 0, "ascending": 1, "descending": 2}


def spine_drop(cat, off, val, phi=None, one_sided=False, val_bounds=None, bin_order="middle-out"):
    """C twin of ``beeswarm_core._spine_drop_layout`` for the circle shape.
    Returns (new_off, new_val) or None."""
    if bin_order not in _BIN_ORDER:
        msg = f"bin_order must be 'middle-out', 'ascending', or 'descending', got {bin_order!r}"
        raise ValueError(msg)
    cat = np.ascontiguousarray(cat, dtype=np.float64)
    off, val, _ = _prep(off, val, np.zeros(len(off), dtype=np.int64))
    if cat.shape != off.shape:
        msg = "cat, off, val must have the same length"
        raise ValueError(msg)
    out_a = np.empty_like(off)
    out_b = np.empty_like(val)
    has_b = val_bounds is not None
    lo, hi = (float(val_bounds[0]), float(val_bounds[1])) if has_b else (0.0, 0.0)
    rc = lib().bs_spine_drop(
        off.size,
        cat,
        off,
        val,
        float(phi) if phi is not None else -1.0,
        int(one_sided),
        int(has_b),
        lo,
        hi,
        _BIN_ORDER[bin_order],
        out_a,
        out_b,
    )
    return None if rc else (out_a, out_b)
