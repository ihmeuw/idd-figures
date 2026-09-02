/* C99 kernel for the beeswarm core's circle path (extraction step 4,
 * 2026-09-02): a transliteration of idd_figures.beeswarm_core at D = 1.
 * Arrays of doubles in, positions out; libm only. Every function returns 0
 * on success and 1 when some point has no valid position.
 *
 * Tie-break rule (must match the Python): among candidates whose value is
 * within TOL of the minimum, take the largest first preference key, then
 * the largest second key, then the first encountered. */
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define TOL 1e-9

static int pick(int n, const double *values, const double *p1, const double *p2) {
    double vmin = INFINITY;
    for (int i = 0; i < n; i++) if (values[i] < vmin) vmin = values[i];
    double best1 = -INFINITY;
    for (int i = 0; i < n; i++) if (values[i] <= vmin + TOL && p1[i] > best1) best1 = p1[i];
    if (p2 == NULL) {
        for (int i = 0; i < n; i++) if (values[i] <= vmin + TOL && p1[i] >= best1 - TOL) return i;
        return 0;
    }
    double best2 = -INFINITY;
    for (int i = 0; i < n; i++)
        if (values[i] <= vmin + TOL && p1[i] >= best1 - TOL && p2[i] > best2) best2 = p2[i];
    for (int i = 0; i < n; i++)
        if (values[i] <= vmin + TOL && p1[i] >= best1 - TOL && p2[i] >= best2 - TOL) return i;
    return 0;
}

/* ---- value-exact step: smallest |shift| outside every forbidden interval ---- */

typedef struct { double *L, *H, *cands, *ash; } swarm_scratch;

static int min_shift_position(double ai, double bi, int k, const double *PA, const double *PB,
                              int one_sided, double *out, swarm_scratch *sc) {
    int m = 0;
    for (int j = 0; j < k; j++) {
        double dv = bi - PB[j];
        if (fabs(dv) < 1.0) {
            double h = sqrt(1.0 - dv * dv);
            sc->L[m] = PA[j] - h; sc->H[m] = PA[j] + h; m++;
        }
    }
    if (m == 0) { *out = ai; return 0; }
    int inside = 0;
    for (int j = 0; j < m; j++) if (ai > sc->L[j] + TOL && ai < sc->H[j] - TOL) { inside = 1; break; }
    if (!inside) { *out = ai; return 0; }
    int nc = 0;
    for (int pass = 0; pass < 2; pass++) {
        for (int j = 0; j < m; j++) {
            double c = pass == 0 ? sc->H[j] : sc->L[j];
            int bad = 0;
            for (int t = 0; t < m; t++) if (c > sc->L[t] + TOL && c < sc->H[t] - TOL) { bad = 1; break; }
            if (bad) continue;
            if (one_sided && c < ai - TOL) continue;
            sc->cands[nc] = c; sc->ash[nc] = fabs(c - ai); nc++;
        }
    }
    if (nc == 0) return 1;
    *out = sc->cands[pick(nc, sc->ash, sc->cands, NULL)];
    return 0;
}

int bs_layout_swarm(int64_t n, const double *off, const double *val, const int64_t *order,
                    int one_sided, double *out) {
    double *PA = malloc(n * sizeof(double)), *PB = malloc(n * sizeof(double));
    swarm_scratch sc = { malloc(n * sizeof(double)), malloc(n * sizeof(double)),
                         malloc(2 * n * sizeof(double)), malloc(2 * n * sizeof(double)) };
    memcpy(out, off, n * sizeof(double));
    int k = 0, rc = 0;
    for (int64_t s = 0; s < n; s++) {
        int64_t i = order[s];
        double ai = off[i];
        if (k && min_shift_position(off[i], val[i], k, PA, PB, one_sided, &ai, &sc)) { rc = 1; break; }
        PA[k] = ai; PB[k] = val[i]; k++; out[i] = ai;
    }
    free(PA); free(PB); free(sc.L); free(sc.H); free(sc.cands); free(sc.ash);
    return rc;
}

/* ---- phi-penalized step ---- */

/* Lagrange condition in s = distance of the multiplier from its nearer pole
 * (one of da, db is exactly 0, so no cancellation); bisection then Newton.
 * Mirrors beeswarm_core._ellipse_closest exactly. */
static double G_ell(double s, double A, double B, double da, double db) {
    double u = A / (s + da), v = B / (s + db);
    return u * u + v * v - 1.0;
}

static double dG_ell(double s, double A, double B, double da, double db) {
    double sa = s + da, sb = s + db;
    return -2.0 * A * A / (sa * sa * sa) - 2.0 * B * B / (sb * sb * sb);
}

static void ellipse_closest(double qx, double qy, double alpha, double beta, double *ex, double *ey) {
    double sx = qx >= 0 ? 1.0 : -1.0, sy = qy >= 0 ? 1.0 : -1.0;
    double ax = fmax(fabs(qx), 1e-9 * alpha), ay = fmax(fabs(qy), 1e-9 * beta);
    double a2 = alpha * alpha, b2 = beta * beta;
    double m = fmin(a2, b2), da = a2 - m, db = b2 - m;
    double A = alpha * ax, B = beta * ay;
    double lo = 1e-12 * m;
    double hi = fmax(a2, b2) + m + alpha * ax + beta * ay;
    for (int it = 0; it < 25; it++) {
        if (G_ell(hi, A, B, da, db) > 0) hi = hi * 2.0 + fmax(a2, b2); else break;
    }
    for (int it = 0; it < 44; it++) {
        double mid = 0.5 * (lo + hi);
        if (G_ell(mid, A, B, da, db) > 0) lo = mid; else hi = mid;
    }
    double s = 0.5 * (lo + hi);
    for (int it = 0; it < 3; it++) {
        double step = s - G_ell(s, A, B, da, db) / dG_ell(s, A, B, da, db);
        s = step > lo ? step : lo;
    }
    *ex = a2 * ax / (s + da) * sx;
    *ey = b2 * ay / (s + db) * sy;
}

typedef struct {
    double *na, *ndv, *c0s, *ab, *wa, *wb;   /* size n each */
    double *cx, *cy, *cost;                 /* grown on demand */
    int cap;
} phi_scratch;

static void phi_reserve(phi_scratch *sc, int need) {
    if (need <= sc->cap) return;
    sc->cap = need + 64;
    sc->cx = realloc(sc->cx, sc->cap * sizeof(double));
    sc->cy = realloc(sc->cy, sc->cap * sizeof(double));
    sc->cost = realloc(sc->cost, sc->cap * sizeof(double));
}

static int phi_best(double ai, double bi, int k, const double *PA, const double *PB, double phi,
                    int one_sided, int has_bounds, double blo, double bhi,
                    double *oa, double *ob, double *ocost, phi_scratch *sc) {
    const double thresh2 = (1.0 - TOL) * (1.0 - TOL);
    const double sqphi = sqrt(phi);
    int m0 = 0, collide = 0;
    for (int j = 0; j < k; j++) {
        double dv = PB[j] - bi;
        if (fabs(dv) < 1.0) {
            sc->na[m0] = PA[j]; sc->ndv[m0] = dv; m0++;
            if ((PA[j] - ai) * (PA[j] - ai) + dv * dv < thresh2) collide = 1;
        }
    }
    if (m0 == 0 || !collide) { *oa = ai; *ob = bi; *ocost = 0.0; return 0; }
    /* pure-offset fallback */
    int nc = 0;
    for (int pass = 0; pass < 2; pass++) {
        for (int j = 0; j < m0; j++) {
            double da = sqrt(1.0 - sc->ndv[j] * sc->ndv[j]);
            double c = pass == 0 ? sc->na[j] + da : sc->na[j] - da;
            int ok = 1;
            for (int t = 0; t < m0; t++) {
                double d = c - sc->na[t];
                if (d * d + sc->ndv[t] * sc->ndv[t] < thresh2) { ok = 0; break; }
            }
            if (!ok) continue;
            if (one_sided && c < ai - TOL) continue;
            sc->c0s[nc] = c; sc->ab[nc] = fabs(c - ai); nc++;
        }
    }
    if (nc == 0) return 1;
    double best_a = sc->c0s[pick(nc, sc->ab, sc->c0s, NULL)], best_b = bi;
    double c0 = (best_a - ai) * (best_a - ai);
    double delta = sqrt(c0 / phi);
    int mW = 0;
    for (int j = 0; j < k; j++) {
        double dv = PB[j] - bi;
        if (fabs(dv) < 1.0 + delta) { sc->wa[mW] = PA[j]; sc->wb[mW] = PB[j]; mW++; }
    }
    phi_reserve(sc, mW * (mW - 1) + 7 * mW + 2);
    int nk = 0;
    for (int j = 0; j < mW; j++) {  /* metric projection onto each circle */
        double ex, ey;
        ellipse_closest(ai - sc->wa[j], (bi - sc->wb[j]) * sqphi, 1.0, sqphi, &ex, &ey);
        sc->cx[nk] = sc->wa[j] + ex; sc->cy[nk] = sc->wb[j] + ey / sqphi; nk++;
    }
    for (int i = 0; i < mW; i++) {   /* circle-circle intersections */
        for (int j = i + 1; j < mW; j++) {
            double pdx = sc->wa[j] - sc->wa[i], pdy = sc->wb[j] - sc->wb[i];
            double pd2 = pdx * pdx + pdy * pdy;
            if (pd2 > TOL * TOL && pd2 < 4.0) {
                double pdist = sqrt(pd2), h = sqrt(fmax(1.0 - pd2 / 4.0, 0.0));
                double mx = 0.5 * (sc->wa[i] + sc->wa[j]), my = 0.5 * (sc->wb[i] + sc->wb[j]);
                double ux = -pdy / pdist, uy = pdx / pdist;
                sc->cx[nk] = mx + h * ux; sc->cy[nk] = my + h * uy; nk++;
                sc->cx[nk] = mx - h * ux; sc->cy[nk] = my - h * uy; nk++;
            }
        }
    }
    if (one_sided) {   /* circle x baseline */
        for (int j = 0; j < mW; j++) {
            double dy2 = 1.0 - (ai - sc->wa[j]) * (ai - sc->wa[j]);
            if (dy2 > 0) {
                double hh = sqrt(dy2);
                sc->cx[nk] = ai; sc->cy[nk] = sc->wb[j] + hh; nk++;
                sc->cx[nk] = ai; sc->cy[nk] = sc->wb[j] - hh; nk++;
            }
        }
    }
    if (has_bounds) {  /* circle x frame edges (+ corner with baseline) */
        double vbs[2] = { blo, bhi };
        for (int q = 0; q < 2; q++) {
            double vb = vbs[q];
            for (int j = 0; j < mW; j++) {
                double dx2 = 1.0 - (vb - sc->wb[j]) * (vb - sc->wb[j]);
                if (dx2 > 0) {
                    double hh = sqrt(dx2);
                    sc->cx[nk] = sc->wa[j] + hh; sc->cy[nk] = vb; nk++;
                    sc->cx[nk] = sc->wa[j] - hh; sc->cy[nk] = vb; nk++;
                }
            }
            if (one_sided) { sc->cx[nk] = ai; sc->cy[nk] = vb; nk++; }
        }
    }
    /* filter: dominated, constraint, then validity (invalid -> inf cost) */
    int nkeep = 0;
    for (int c = 0; c < nk; c++) {
        double cx = sc->cx[c], cy = sc->cy[c];
        double cost = (cx - ai) * (cx - ai) + phi * (cy - bi) * (cy - bi);
        if (cost > c0 * (1.0 + 1e-12)) continue;
        if (one_sided && cx < ai - TOL) continue;
        if (has_bounds && (cy < blo || cy > bhi)) continue;
        for (int j = 0; j < mW; j++) {
            double dx = cx - sc->wa[j], dy = cy - sc->wb[j];
            if (dx * dx + dy * dy < thresh2) { cost = INFINITY; break; }
        }
        sc->cx[nkeep] = cx; sc->cy[nkeep] = cy; sc->cost[nkeep] = cost; nkeep++;
    }
    double best_c = c0;
    if (nkeep) {
        int j = pick(nkeep, sc->cost, sc->cx, sc->cy);
        if (sc->cost[j] < c0 - 1e-12) { best_a = sc->cx[j]; best_b = sc->cy[j]; best_c = sc->cost[j]; }
    }
    *oa = best_a; *ob = best_b; *ocost = best_c;
    return 0;
}

static phi_scratch phi_scratch_alloc(int64_t n) {
    phi_scratch sc;
    sc.na = malloc(n * sizeof(double)); sc.ndv = malloc(n * sizeof(double));
    sc.c0s = malloc(2 * n * sizeof(double)); sc.ab = malloc(2 * n * sizeof(double));
    sc.wa = malloc(n * sizeof(double)); sc.wb = malloc(n * sizeof(double));
    sc.cx = NULL; sc.cy = NULL; sc.cost = NULL; sc.cap = 0;
    return sc;
}

static void phi_scratch_free(phi_scratch *sc) {
    free(sc->na); free(sc->ndv); free(sc->c0s); free(sc->ab); free(sc->wa); free(sc->wb);
    free(sc->cx); free(sc->cy); free(sc->cost);
}

int bs_layout_phi(int64_t n, const double *off, const double *val, const int64_t *order,
                  double phi, int one_sided, int has_bounds, double blo, double bhi,
                  double *out_a, double *out_b) {
    double *PA = malloc(n * sizeof(double)), *PB = malloc(n * sizeof(double));
    phi_scratch sc = phi_scratch_alloc(n);
    memcpy(out_a, off, n * sizeof(double));
    memcpy(out_b, val, n * sizeof(double));
    int k = 0, rc = 0;
    for (int64_t s = 0; s < n; s++) {
        int64_t i = order[s];
        double a, b, c;
        if (phi_best(off[i], val[i], k, PA, PB, phi, one_sided, has_bounds, blo, bhi, &a, &b, &c, &sc)) {
            rc = 1; break;
        }
        PA[k] = a; PB[k] = b; k++;
        out_a[i] = a; out_b[i] = b;
    }
    free(PA); free(PB); phi_scratch_free(&sc);
    return rc;
}

/* Per-point step exported for parity debugging and tests. */
int bs_phi_best(double ai, double bi, int64_t k, const double *PA, const double *PB, double phi,
                int one_sided, int has_bounds, double blo, double bhi, double *out3) {
    phi_scratch sc = phi_scratch_alloc(k > 0 ? k : 1);
    double a, b, c;
    int rc = phi_best(ai, bi, (int)k, PA, PB, phi, one_sided, has_bounds, blo, bhi, &a, &b, &c, &sc);
    phi_scratch_free(&sc);
    out3[0] = a; out3[1] = b; out3[2] = c;
    return rc;
}

int bs_ellipse_closest(double qx, double qy, double alpha, double beta, double *out2) {
    ellipse_closest(qx, qy, alpha, beta, &out2[0], &out2[1]);
    return 0;
}
