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
#define BS_PI 3.14159265358979323846  /* M_PI is not C99 */

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

/* ---- collision shapes: the circle (closed form) or a set of convex Minkowski
 * polygons K_pq built once in Python (beeswarm_shapes.PolygonShape.K), passed
 * flat: kv = x0,y0,x1,y1,... for all K, koff[q]..koff[q+1] the vertex range of
 * K number q. Mirrors PolygonShape.forbidden / _silhouette op for op. ---- */

typedef struct {
    int64_t nK;             /* 0 -> unit circle */
    const int64_t *koff;    /* nK + 1 vertex offsets */
    const double *kv;       /* flat vertices */
    double *bmin, *bmax;    /* per-K vertical extent, computed at entry */
    double half_height;     /* near-filter window (circle: 1) */
    double stack_height;    /* no-shift contact height (circle: 1) */
} shape_t;

static void shape_prep(shape_t *sh) {
    for (int64_t q = 0; q < sh->nK; q++) {
        double mn = INFINITY, mx = -INFINITY;
        for (int64_t e = sh->koff[q]; e < sh->koff[q + 1]; e++) {
            double b = sh->kv[2 * e + 1];
            if (b < mn) mn = b;
            if (b > mx) mx = b;
        }
        sh->bmin[q] = mn; sh->bmax[q] = mx;
    }
}

/* Horizontal cut of convex polygon q at height h. 1 if the line cuts the
 * interior (lo < hi), else 0: touching at a vertex or along a top/bottom
 * edge is not overlap. Same arithmetic as beeswarm_shapes._silhouette. */
static int silhouette(const shape_t *sh, int64_t q, double h, double *lo, double *hi) {
    if (!(h > sh->bmin[q] + TOL && h < sh->bmax[q] - TOL)) return 0;
    int64_t v0 = sh->koff[q], nv = sh->koff[q + 1] - v0;
    double mn = INFINITY, mx = -INFINITY;
    for (int64_t e = 0; e < nv; e++) {
        int64_t f = (e + 1) % nv;
        double pa = sh->kv[2 * (v0 + e)], pb = sh->kv[2 * (v0 + e) + 1];
        double qa = sh->kv[2 * (v0 + f)], qb = sh->kv[2 * (v0 + f) + 1];
        double pbh = pb - h, qbh = qb - h;
        if (pbh * qbh < 0.0) {
            double denom = qb - pb;
            double t = -pbh / denom;
            double a = pa + t * (qa - pa);
            if (a < mn) mn = a;
            if (a > mx) mx = a;
        }
        if (fabs(pbh) <= TOL) {
            if (pa < mn) mn = pa;
            if (pa > mx) mx = pa;
        }
    }
    if (!(mx - mn > TOL)) return 0;  /* also false when nothing was hit (inf - -inf is inf... guard below) */
    if (mn == INFINITY) return 0;
    *lo = mn; *hi = mx;
    return 1;
}

/* Absolute forbidden intervals (L, H) for a mark at value bi against the k
 * placed marks. Returns the count. Capacity must be >= k * max(nK, 1). */
static int64_t forbidden_intervals(const shape_t *sh, double bi, int64_t k, const double *PA,
                                   const double *PB, double *L, double *H) {
    int64_t m = 0;
    if (sh->nK == 0) {
        for (int64_t j = 0; j < k; j++) {
            double dv = bi - PB[j];
            if (fabs(dv) < 1.0) {
                double hh = sqrt(1.0 - dv * dv);
                L[m] = PA[j] - hh; H[m] = PA[j] + hh; m++;
            }
        }
        return m;
    }
    for (int64_t j = 0; j < k; j++) {
        double dv = bi - PB[j];
        if (!(fabs(dv) < sh->half_height)) continue;
        for (int64_t q = 0; q < sh->nK; q++) {
            double lo, hi;
            if (silhouette(sh, q, dv, &lo, &hi)) { L[m] = PA[j] + lo; H[m] = PA[j] + hi; m++; }
        }
    }
    return m;
}

/* ---- value-exact step: smallest |shift| outside every forbidden interval ---- */

typedef struct { double *L, *H, *cands, *ash; } swarm_scratch;

static swarm_scratch swarm_scratch_alloc(int64_t n, int64_t nK) {
    int64_t cap = n * (nK > 1 ? nK : 1);
    swarm_scratch sc = { malloc(cap * sizeof(double)), malloc(cap * sizeof(double)),
                         malloc(2 * cap * sizeof(double)), malloc(2 * cap * sizeof(double)) };
    return sc;
}

static void swarm_scratch_free(swarm_scratch *sc) { free(sc->L); free(sc->H); free(sc->cands); free(sc->ash); }

static int min_shift_position(double ai, double bi, int64_t k, const double *PA, const double *PB,
                              int one_sided, double *out, swarm_scratch *sc, const shape_t *sh) {
    int64_t m = forbidden_intervals(sh, bi, k, PA, PB, sc->L, sc->H);
    if (m == 0) { *out = ai; return 0; }
    int inside = 0;
    for (int64_t j = 0; j < m; j++) if (ai > sc->L[j] + TOL && ai < sc->H[j] - TOL) { inside = 1; break; }
    if (!inside) { *out = ai; return 0; }
    int64_t nc = 0;
    for (int pass = 0; pass < 2; pass++) {
        for (int64_t j = 0; j < m; j++) {
            double c = pass == 0 ? sc->H[j] : sc->L[j];
            int bad = 0;
            for (int64_t t = 0; t < m; t++) if (c > sc->L[t] + TOL && c < sc->H[t] - TOL) { bad = 1; break; }
            if (bad) continue;
            if (one_sided && c < ai - TOL) continue;
            sc->cands[nc] = c; sc->ash[nc] = fabs(c - ai); nc++;
        }
    }
    if (nc == 0) return 1;
    *out = sc->cands[pick((int)nc, sc->ash, sc->cands, NULL)];
    return 0;
}

int bs_layout_swarm(int64_t n, const double *off, const double *val, const int64_t *order,
                    int one_sided, int64_t nK, const int64_t *koff, const double *kv,
                    double half_height, double stack_height, double *out) {
    shape_t sh = { nK, koff, kv, malloc((nK + 1) * sizeof(double)), malloc((nK + 1) * sizeof(double)),
                   nK ? half_height : 1.0, nK ? stack_height : 1.0 };
    shape_prep(&sh);
    double *PA = malloc(n * sizeof(double)), *PB = malloc(n * sizeof(double));
    swarm_scratch sc = swarm_scratch_alloc(n, nK);
    memcpy(out, off, n * sizeof(double));
    int64_t k = 0; int rc = 0;
    for (int64_t s = 0; s < n; s++) {
        int64_t i = order[s];
        double ai = off[i];
        if (k && min_shift_position(off[i], val[i], k, PA, PB, one_sided, &ai, &sc, &sh)) { rc = 1; break; }
        PA[k] = ai; PB[k] = val[i]; k++; out[i] = ai;
    }
    free(PA); free(PB); swarm_scratch_free(&sc); free(sh.bmin); free(sh.bmax);
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
    double *na, *ndv, *c0s, *ab, *wa, *wb;   /* size n each (c0s, ab: 2n) */
    double *w;                               /* gravity weights, size n */
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

/* The analytic candidate positions for the phi step against the window
 * marks (wa, wb) in sc: projections, circle-circle intersections, constraint
 * line hits. Writes sc->cx/cy, returns the count. Shared with gravity; the
 * arithmetic mirrors beeswarm_core._phi_candidates. */
static int phi_candidates(double ai, double bi, int mW, double sqphi, int one_sided,
                          int has_bounds, double blo, double bhi, phi_scratch *sc) {
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
    return nk;
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
    int nk = phi_candidates(ai, bi, mW, sqphi, one_sided, has_bounds, blo, bhi, sc);
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
    sc.w = malloc(n * sizeof(double));
    sc.cx = NULL; sc.cy = NULL; sc.cost = NULL; sc.cap = 0;
    return sc;
}

static void phi_scratch_free(phi_scratch *sc) {
    free(sc->na); free(sc->ndv); free(sc->c0s); free(sc->ab); free(sc->wa); free(sc->wb);
    free(sc->w); free(sc->cx); free(sc->cy); free(sc->cost);
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

/* ---- gravity: phi's step with a position-dependent price and a density
 * basin (mirrors beeswarm_core._gravity_*). Exhaustive search inside the
 * closed-form window; exact feasibility; optimal up to the grid spacing. ---- */

typedef struct { double g, kappa, beta, sigma, lam, h; int64_t M; int exhaustive; } gravity_params;

static gravity_params gravity_from_array(const double *gp) {
    gravity_params p = { gp[0], gp[1], gp[2], gp[3], gp[4], gp[5], (int64_t)gp[6], gp[7] > 0.5 };
    return p;
}

/* w_j = exp(-|PA_j - ai| / lam) for the current mark; also returns W = sum w_j. */
static double gravity_weights(double ai, int64_t k, const double *PA, const gravity_params *gp, double *w) {
    double W = 0.0;
    for (int64_t j = 0; j < k; j++) { w[j] = exp(-fabs(PA[j] - ai) / gp->lam); W += w[j]; }
    return W;
}

static double gravity_cost1(double x, double y, double ai, double bi, int64_t k, const double *PA,
                            const double *PB, const double *w, double phi, const gravity_params *gp) {
    double doff = x - ai, dval = y - bi;
    double d2o = doff * doff;
    double cost = d2o * (1.0 + (gp->g * gp->kappa) * d2o) + phi * (dval * dval);
    if (gp->g == 0.0 || gp->beta == 0.0 || k == 0) return cost;
    double inv = 1.0 / (2.0 * gp->sigma * gp->sigma), rho = 0.0;
    for (int64_t j = 0; j < k; j++) {
        double dx = x - PA[j], dy = y - PB[j];
        rho += w[j] * exp(-(dx * dx + dy * dy) * inv);
    }
    return cost - (gp->g * gp->beta) * rho;
}

/* 0 ok, 1 no valid position. Mirrors _gravity_best step for step. */
static int gravity_best(double ai, double bi, int64_t k, const double *PA, const double *PB, double phi,
                        const gravity_params *gp, int one_sided, int has_bounds, double blo, double bhi,
                        double *oa, double *ob, double *ocost, phi_scratch *sc) {
    const double thresh2 = (1.0 - TOL) * (1.0 - TOL);
    /* gate: anchor stays when feasible */
    int m0 = 0, collide = 0;
    for (int64_t j = 0; j < k; j++) {
        double dv = PB[j] - bi;
        if (fabs(dv) < 1.0) {
            sc->na[m0] = PA[j]; sc->ndv[m0] = dv; m0++;
            if ((PA[j] - ai) * (PA[j] - ai) + dv * dv < thresh2) collide = 1;
        }
    }
    if (m0 == 0 || !collide) { *oa = ai; *ob = bi; *ocost = 0.0; return 0; }
    /* reference: pure-offset fallback (phi's rule) and the window */
    int nv = 0;
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
            sc->c0s[nv] = c; sc->ab[nv] = fabs(c - ai); nv++;
        }
    }
    if (nv == 0) return 1;
    double best_a = sc->c0s[pick(nv, sc->ab, sc->c0s, NULL)], best_b = bi;
    double W = gravity_weights(ai, k, PA, gp, sc->w);
    double c0_g = gravity_cost1(best_a, bi, ai, bi, k, PA, PB, sc->w, phi, gp);
    if (!(gp->g > 0.0)) W = 0.0;
    double bonus = gp->g * gp->beta * W;
    double delta = sqrt((c0_g + bonus) / phi);
    double Delta = sqrt(c0_g + bonus);
    if (gp->g > 0.0 && gp->beta > 0.0 && k > 0) {
        /* lossless window tightening: rho on the window <= sum_j w_j * max_box K_j;
           two fixed iterations, same arithmetic as _gravity_reference */
        double inv = 1.0 / (2.0 * gp->sigma * gp->sigma);
        for (int it = 0; it < 2; it++) {
            double xlo = one_sided ? ai : ai - Delta, xhi = ai + Delta;
            double ylo = bi - delta, yhi = bi + delta;
            double Weff = 0.0;
            for (int64_t j = 0; j < k; j++) {
                double dxs = fmax(0.0, fmax(xlo - PA[j], PA[j] - xhi));
                double dys = fmax(0.0, fmax(ylo - PB[j], PB[j] - yhi));
                Weff += sc->w[j] * exp(-(dxs * dxs + dys * dys) * inv);
            }
            bonus = gp->g * gp->beta * Weff;
            delta = sqrt((c0_g + bonus) / phi);
            Delta = sqrt(c0_g + bonus);
        }
    }
    /* window marks */
    int mW = 0;
    for (int64_t j = 0; j < k; j++) {
        double dv = PB[j] - bi;
        if (fabs(dv) < 1.0 + delta) { sc->wa[mW] = PA[j]; sc->wb[mW] = PB[j]; mW++; }
    }
    double sqphi = sqrt(phi);
    int nA = phi_candidates(ai, bi, mW, sqphi, one_sided, has_bounds, blo, bhi, sc);
    /* sample counts (upper bounds) for capacity */
    double hgrid = gp->h;
    double xlo = one_sided ? ai : ai - Delta;
    double xstop = ai + Delta + hgrid / 2.0;
    int64_t nx = (int64_t)ceil((xstop - xlo) / hgrid); if (nx < 0) nx = 0;
    double ylo = bi - delta, yhi = bi + delta;
    if (has_bounds) { if (blo > ylo) ylo = blo; if (bhi < yhi) yhi = bhi; }
    int64_t ny = 0;
    if (yhi >= ylo) { ny = (int64_t)ceil((yhi + hgrid / 2.0 - ylo) / hgrid); if (ny < 0) ny = 0; }
    int64_t nS = gp->exhaustive ? gp->M * mW + nx * ny + (one_sided ? ny : 0) + (has_bounds ? 2 * nx : 0) : 0;
    phi_reserve(sc, nA + nv + nS + 8);
    int nk = nA;
    /* pure-offset alternatives, only when strictly cheaper than the fallback */
    for (int t = 0; t < nv; t++) {
        double c = gravity_cost1(sc->c0s[t], bi, ai, bi, k, PA, PB, sc->w, phi, gp);
        if (c < c0_g - 1e-12) { sc->cx[nk] = sc->c0s[t]; sc->cy[nk] = bi; nk++; }
    }
    if (gp->exhaustive) {
        int64_t s0 = nk;
        for (int j = 0; j < mW; j++)          /* arc samples, j-major */
            for (int64_t m = 0; m < gp->M; m++) {
                double th = (2.0 * BS_PI * (double)m) / (double)gp->M;
                sc->cx[nk] = sc->wa[j] + cos(th); sc->cy[nk] = sc->wb[j] + sin(th); nk++;
            }
        for (int64_t ix = 0; ix < nx; ix++)   /* interior grid, x-major */
            for (int64_t iy = 0; iy < ny; iy++) {
                sc->cx[nk] = xlo + (double)ix * hgrid; sc->cy[nk] = ylo + (double)iy * hgrid; nk++;
            }
        if (one_sided)
            for (int64_t iy = 0; iy < ny; iy++) { sc->cx[nk] = ai; sc->cy[nk] = ylo + (double)iy * hgrid; nk++; }
        if (has_bounds) {
            double vbs[2] = { blo, bhi };
            for (int q = 0; q < 2; q++)
                for (int64_t ix = 0; ix < nx; ix++) { sc->cx[nk] = xlo + (double)ix * hgrid; sc->cy[nk] = vbs[q]; nk++; }
        }
        /* dedupe samples against the analytic candidates (1e-4 D): the exact
           point must win its ties, which is what keeps the g = 0 analytic
           parity bit-exact */
        int64_t out = s0;
        for (int64_t t = s0; t < nk; t++) {
            int same = 0;
            for (int a = 0; a < nA; a++)
                if (fabs(sc->cx[t] - sc->cx[a]) <= 1e-4 && fabs(sc->cy[t] - sc->cy[a]) <= 1e-4) { same = 1; break; }
            if (!same) { sc->cx[out] = sc->cx[t]; sc->cy[out] = sc->cy[t]; out++; }
        }
        nk = (int)out;
    }
    /* filter: dominated, constraints, then validity against the window marks */
    int nkeep = 0;
    for (int c = 0; c < nk; c++) {
        double cx = sc->cx[c], cy = sc->cy[c];
        double cost = gravity_cost1(cx, cy, ai, bi, k, PA, PB, sc->w, phi, gp);
        if (cost > c0_g + 1e-12 * fabs(c0_g)) continue;
        if (one_sided && cx < ai - TOL) continue;
        if (has_bounds && (cy < blo || cy > bhi)) continue;
        for (int j = 0; j < mW; j++) {
            double dx = cx - sc->wa[j], dy = cy - sc->wb[j];
            if (dx * dx + dy * dy < thresh2) { cost = INFINITY; break; }
        }
        sc->cx[nkeep] = cx; sc->cy[nkeep] = cy; sc->cost[nkeep] = cost; nkeep++;
    }
    double best_c = c0_g;
    if (nkeep) {
        int j = pick(nkeep, sc->cost, sc->cx, sc->cy);
        if (sc->cost[j] < c0_g - 1e-12) { best_a = sc->cx[j]; best_b = sc->cy[j]; best_c = sc->cost[j]; }
    }
    *oa = best_a; *ob = best_b; *ocost = best_c;
    return 0;
}

int bs_gravity_best(double ai, double bi, int64_t k, const double *PA, const double *PB, double phi,
                    const double *gparams, int one_sided, int has_bounds, double blo, double bhi, double *out3) {
    gravity_params gp = gravity_from_array(gparams);
    phi_scratch sc = phi_scratch_alloc(k > 0 ? k : 1);
    double a, b, c;
    int rc = gravity_best(ai, bi, k, PA, PB, phi, &gp, one_sided, has_bounds, blo, bhi, &a, &b, &c, &sc);
    phi_scratch_free(&sc);
    out3[0] = a; out3[1] = b; out3[2] = c;
    return rc;
}

int bs_layout_gravity(int64_t n, const double *off, const double *val, const int64_t *order, double phi,
                      const double *gparams, int one_sided, int has_bounds, double blo, double bhi,
                      double *out_a, double *out_b) {
    gravity_params gp = gravity_from_array(gparams);
    double *PA = malloc(n * sizeof(double)), *PB = malloc(n * sizeof(double));
    phi_scratch sc = phi_scratch_alloc(n);
    memcpy(out_a, off, n * sizeof(double));
    memcpy(out_b, val, n * sizeof(double));
    int64_t k = 0; int rc = 0;
    for (int64_t s = 0; s < n; s++) {
        int64_t i = order[s];
        double a, b, c;
        if (gravity_best(off[i], val[i], k, PA, PB, phi, &gp, one_sided, has_bounds, blo, bhi, &a, &b, &c, &sc)) {
            rc = 1; break;
        }
        PA[k] = a; PB[k] = b; k++;
        out_a[i] = a; out_b[i] = b;
    }
    free(PA); free(PB); phi_scratch_free(&sc);
    return rc;
}

/* ---- spine-drop: dynamic lowest-lander placement (mirrors _spine_drop_layout) ---- */

typedef struct { const double *cat, *val; } sort_ctx;
static sort_ctx g_sort;  /* qsort has no context argument in C99; single-threaded use */

static int cmp_cat_val_idx(const void *pa, const void *pb) {
    int64_t i = *(const int64_t *)pa, j = *(const int64_t *)pb;
    if (g_sort.cat[i] < g_sort.cat[j]) return -1;
    if (g_sort.cat[i] > g_sort.cat[j]) return 1;
    if (g_sort.val[i] < g_sort.val[j]) return -1;  /* stable argsort within a category */
    if (g_sort.val[i] > g_sort.val[j]) return 1;
    return (i < j) ? -1 : (i > j);
}

static int cmp_int64(const void *a, const void *b) {
    int64_t x = *(const int64_t *)a, y = *(const int64_t *)b;
    return (x < y) ? -1 : (x > y);
}

typedef struct { double dist, lower; int64_t k; } binkey;

static int cmp_binkey_mid(const void *a, const void *b) {  /* (dist, lower) then k */
    const binkey *x = a, *y = b;
    if (x->dist < y->dist) return -1;
    if (x->dist > y->dist) return 1;
    if (x->lower < y->lower) return -1;
    if (x->lower > y->lower) return 1;
    return (x->k < y->k) ? -1 : (x->k > y->k);
}
static int cmp_binkey_asc(const void *a, const void *b) {
    const binkey *x = a, *y = b; return (x->k < y->k) ? -1 : (x->k > y->k);
}
static int cmp_binkey_desc(const void *a, const void *b) { return cmp_binkey_asc(b, a); }

typedef struct {
    char *cached, *feas;          /* per point: is there a cached evaluation; was it feasible */
    double *shift, *cost, *a, *b; /* cached key parts and landing */
    const double *val;            /* third key element */
} eval_cache;

/* Python key tuple (|shift|, cost, val, i), with (inf,) for infeasible. */
static int keycmp(const eval_cache *c, int64_t i, int64_t j) {
    if (!c->feas[i] && !c->feas[j]) return 0;
    if (!c->feas[i]) return 1;
    if (!c->feas[j]) return -1;
    if (c->shift[i] != c->shift[j]) return c->shift[i] < c->shift[j] ? -1 : 1;
    if (c->cost[i] != c->cost[j]) return c->cost[i] < c->cost[j] ? -1 : 1;
    if (c->val[i] != c->val[j]) return c->val[i] < c->val[j] ? -1 : 1;
    return (i < j) ? -1 : (i > j);
}

typedef struct {
    const double *off, *val;
    double *PA, *PB; int64_t k;
    double phi; int one_sided, has_bounds; double blo, bhi;
    swarm_scratch ssc; phi_scratch psc;
    const shape_t *sh;
    const gravity_params *gp;   /* NULL: phi or drop step */
} placer;

/* One placement attempt against the currently placed marks. 0 ok, 1 infeasible. */
static int place_point(placer *P, int64_t i, double *a, double *b, double *cost) {
    if (P->gp != NULL)
        return gravity_best(P->off[i], P->val[i], P->k, P->PA, P->PB, P->phi, P->gp, P->one_sided,
                            P->has_bounds, P->blo, P->bhi, a, b, cost, &P->psc);
    if (P->phi <= 0.0) {
        double out;
        if (min_shift_position(P->off[i], P->val[i], P->k, P->PA, P->PB, P->one_sided, &out, &P->ssc, P->sh))
            return 1;
        *a = out; *b = P->val[i]; *cost = (out - P->off[i]) * (out - P->off[i]);
        return 0;
    }
    return phi_best(P->off[i], P->val[i], (int)P->k, P->PA, P->PB, P->phi, P->one_sided,
                    P->has_bounds, P->blo, P->bhi, a, b, cost, &P->psc);
}

static void eval_point(placer *P, eval_cache *c, int64_t i) {
    double a, b, cost;
    c->cached[i] = 1;
    if (place_point(P, i, &a, &b, &cost)) { c->feas[i] = 0; return; }
    c->feas[i] = 1; c->shift[i] = fabs(a - P->off[i]); c->cost[i] = cost; c->a[i] = a; c->b[i] = b;
}

static int spine_drop_impl(int64_t n, const double *cat, const double *off, const double *val,
                           double phi, int one_sided, int has_bounds, double blo, double bhi,
                           int bin_order, int64_t nK, const int64_t *koff, const double *kv,
                           double half_height, double stack_height, const gravity_params *gp,
                           double *out_a, double *out_b) {
    shape_t sh = { nK, koff, kv, malloc((nK + 1) * sizeof(double)), malloc((nK + 1) * sizeof(double)),
                   nK ? half_height : 1.0, nK ? stack_height : 1.0 };
    shape_prep(&sh);
    const double thresh = sh.stack_height - TOL;
    int rc = 0;
    memcpy(out_a, off, n * sizeof(double));
    memcpy(out_b, val, n * sizeof(double));

    placer P = { off, val, malloc(n * sizeof(double)), malloc(n * sizeof(double)), 0,
                 phi, one_sided, has_bounds, blo, bhi,
                 swarm_scratch_alloc(n, nK), phi_scratch_alloc(n), &sh, gp };
    int64_t *ord = malloc(n * sizeof(int64_t));
    int64_t *up = malloc(n * sizeof(int64_t)), *down = malloc(n * sizeof(int64_t));
    int64_t *spine = malloc(n * sizeof(int64_t)), *spine_sorted = malloc(n * sizeof(int64_t));
    double *v = malloc(n * sizeof(double)), *sv = malloc(n * sizeof(double));
    char *in_spine = malloc(n);
    int64_t *rest = malloc(n * sizeof(int64_t)), *rest_bin = malloc(n * sizeof(int64_t));
    binkey *keys = malloc((n + 1) * sizeof(binkey));
    char *seen = malloc((n + 1));
    int64_t *qids = malloc(n * sizeof(int64_t));
    int64_t *qstart = malloc((n + 1) * sizeof(int64_t)), *qlen = malloc((n + 1) * sizeof(int64_t));
    int64_t *qremain = malloc((n + 1) * sizeof(int64_t));
    char *removed = calloc(n, 1);
    eval_cache C = { calloc(n, 1), calloc(n, 1), malloc(n * sizeof(double)), malloc(n * sizeof(double)),
                     malloc(n * sizeof(double)), malloc(n * sizeof(double)), val };
    int64_t nq = 0, nqids = 0;

    for (int64_t i = 0; i < n; i++) ord[i] = i;
    g_sort.cat = cat; g_sort.val = val;
    qsort(ord, n, sizeof(int64_t), cmp_cat_val_idx);

    for (int64_t c0 = 0; c0 < n && !rc;) {
        int64_t c1 = c0;
        while (c1 < n && cat[ord[c1]] == cat[ord[c0]]) c1++;
        const int64_t *srt = ord + c0;
        int64_t m = c1 - c0, mid = (m - 1) / 2;
        for (int64_t j = 0; j < m; j++) v[j] = val[srt[j]];
        /* spine: median, then alternating up / down, points that fit with no shift */
        int64_t nu = 0, nd = 0;
        double last = v[mid];
        for (int64_t j = mid + 1; j < m; j++) if (v[j] - last >= thresh) { up[nu++] = j; last = v[j]; }
        last = v[mid];
        for (int64_t j = mid - 1; j >= 0; j--) if (last - v[j] >= thresh) { down[nd++] = j; last = v[j]; }
        int64_t mm = nu < nd ? nu : nd, ns = 0;
        spine[ns++] = mid;
        for (int64_t t = 0; t < mm; t++) { spine[ns++] = up[t]; spine[ns++] = down[t]; }
        if (nu > mm) for (int64_t t = mm; t < nu; t++) spine[ns++] = up[t];
        else for (int64_t t = mm; t < nd; t++) spine[ns++] = down[t];
        for (int64_t t = 0; t < ns && !rc; t++) {  /* spine dots placed first, validated */
            int64_t i = srt[spine[t]];
            double a, b, cost;
            if (place_point(&P, i, &a, &b, &cost)) { rc = 1; break; }
            P.PA[P.k] = a; P.PB[P.k] = b; P.k++;
            out_a[i] = a; out_b[i] = b;
        }
        if (rc) break;
        memcpy(spine_sorted, spine, ns * sizeof(int64_t));
        qsort(spine_sorted, ns, sizeof(int64_t), cmp_int64);
        for (int64_t t = 0; t < ns; t++) sv[t] = v[spine_sorted[t]];
        double vm = v[mid];
        memset(in_spine, 0, m);
        for (int64_t t = 0; t < ns; t++) in_spine[spine[t]] = 1;
        int64_t nr = 0;
        for (int64_t j = 0; j < m; j++) if (!in_spine[j]) rest[nr++] = j;  /* ascending value */
        if (nr == 0) { c0 = c1; continue; }
        /* bins: searchsorted(sv, v, side=left) = number of spine values < v */
        int64_t nk = 0;
        memset(seen, 0, ns + 1);
        for (int64_t t = 0; t < nr; t++) {
            int64_t kk = 0;
            while (kk < ns && sv[kk] < v[rest[t]]) kk++;
            rest_bin[t] = kk;
            if (!seen[kk]) {
                seen[kk] = 1;
                binkey b; b.k = kk;
                if (kk > 0 && kk < ns) {
                    double d1 = fabs(sv[kk - 1] - vm), d2 = fabs(sv[kk] - vm);
                    b.dist = d1 > d2 ? d1 : d2; b.lower = sv[kk - 1];
                } else if (kk == 0) { b.dist = fabs(sv[0] - vm); b.lower = -INFINITY; }
                else { b.dist = fabs(sv[ns - 1] - vm); b.lower = sv[ns - 1]; }
                keys[nk++] = b;
            }
        }
        qsort(keys, nk, sizeof(binkey),
              bin_order == 1 ? cmp_binkey_asc : bin_order == 2 ? cmp_binkey_desc : cmp_binkey_mid);
        for (int64_t q = 0; q < nk; q++) {  /* one queue per bin, points ascending in value */
            qstart[nq] = nqids; qlen[nq] = 0;
            for (int64_t t = 0; t < nr; t++)
                if (rest_bin[t] == keys[q].k) { qids[nqids++] = srt[rest[t]]; qlen[nq]++; }
            qremain[nq] = qlen[nq]; nq++;
        }
        c0 = c1;
    }

    /* sweeps: each non-empty bin places its current lowest lander; a cached
       key is a lower bound (placements only add obstacles), so only the
       apparent winner is re-evaluated until it still beats the runner-up */
    while (!rc) {
        int64_t total = 0;
        for (int64_t q = 0; q < nq; q++) total += qremain[q];
        if (total == 0) break;
        int placed = 0;
        for (int64_t q = 0; q < nq; q++) {
            if (qremain[q] == 0) continue;
            int64_t best = -1, second = -1;
            for (;;) {
                for (int64_t t = 0; t < qlen[q]; t++) {
                    int64_t i = qids[qstart[q] + t];
                    if (!removed[i] && !C.cached[i]) eval_point(&P, &C, i);
                }
                best = -1; second = -1;
                for (int64_t t = 0; t < qlen[q]; t++) {
                    int64_t i = qids[qstart[q] + t];
                    if (removed[i]) continue;
                    if (best < 0 || keycmp(&C, i, best) < 0) { second = best; best = i; }
                    else if (second < 0 || keycmp(&C, i, second) < 0) second = i;
                }
                eval_point(&P, &C, best);  /* refresh the apparent winner */
                if (second < 0 || keycmp(&C, best, second) <= 0) break;
            }
            if (!C.feas[best]) continue;  /* nothing in this bin can be placed yet */
            removed[best] = 1; qremain[q]--; C.cached[best] = 0;
            P.PA[P.k] = C.a[best]; P.PB[P.k] = C.b[best]; P.k++;
            out_a[best] = C.a[best]; out_b[best] = C.b[best];
            placed = 1;
        }
        if (!placed) rc = 1;  /* some points have no valid position at this size */
    }

    free(P.PA); free(P.PB); swarm_scratch_free(&P.ssc);
    phi_scratch_free(&P.psc); free(sh.bmin); free(sh.bmax);
    free(ord); free(up); free(down); free(spine); free(spine_sorted); free(v); free(sv);
    free(in_spine); free(rest); free(rest_bin); free(keys); free(seen); free(qids);
    free(qstart); free(qlen); free(qremain); free(removed);
    free(C.cached); free(C.feas); free(C.shift); free(C.cost); free(C.a); free(C.b);
    return rc;
}

int bs_spine_drop(int64_t n, const double *cat, const double *off, const double *val,
                  double phi, int one_sided, int has_bounds, double blo, double bhi,
                  int bin_order, int64_t nK, const int64_t *koff, const double *kv,
                  double half_height, double stack_height, double *out_a, double *out_b) {
    return spine_drop_impl(n, cat, off, val, phi, one_sided, has_bounds, blo, bhi, bin_order,
                           nK, koff, kv, half_height, stack_height, NULL, out_a, out_b);
}

int bs_spine_drop_gravity(int64_t n, const double *cat, const double *off, const double *val,
                          double phi, const double *gparams, int one_sided, int has_bounds,
                          double blo, double bhi, int bin_order, double *out_a, double *out_b) {
    gravity_params gp = gravity_from_array(gparams);
    int64_t koff0[1] = { 0 };
    double kv0[2] = { 0.0, 0.0 };
    return spine_drop_impl(n, cat, off, val, phi, one_sided, has_bounds, blo, bhi, bin_order,
                           0, koff0, kv0, 1.0, 1.0, &gp, out_a, out_b);
}
