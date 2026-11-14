"""Small continuous references with outward Taylor bounds on the full-power slice."""
import heapq
import itertools
from pathlib import Path
import sys

import numpy as np
from numba import njit
from scipy.optimize import minimize

for folder in ('Gate_2', 'Gate_2B', 'Gate_3'):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]/folder))
import oracle as original
from enclosures import dotbox, up, dn, mix


@njit(cache=True, fastmath=False)
def gram(h):
    k, _, S = h.shape
    g, G = np.empty((k, S)), np.empty((k, S))
    I, J = np.triu_indices(k, 1)
    r, R = np.empty((len(I), S)), np.empty((len(I), S))
    for i in range(k):
        for s in range(S):
            g[i, s], G[i, s] = dotbox(h[i, :, s], h[i, :, s])
    for e in range(len(I)):
        i, j = I[e], J[e]
        for s in range(S):
            a, b = dotbox(h[i, :, s], h[j, :, s])
            r[e, s] = max(0., dn(dn(a*a)/up(G[i, s]*G[j, s])))
            R[e, s] = min(1., up(up(b*b)/dn(g[i, s]*g[j, s])))
    return g, G, r, R


@njit(cache=True, fastmath=False)
def taylor(pa, ed, g, G, rho, rhomax, lo, hi, PT, T):
    k = len(lo)
    centre = (lo+hi)//2
    gl, gu = np.empty(k), np.empty(k)
    value = 0.
    for s in range(len(pa)):
        i, j = pa[s]
        e = ed[s]
        a, A = dn(centre[i]/PT), up(centre[i]/PT)
        b, B = dn(centre[j]/PT), up(centre[j]/PT)
        value = up(value+mix(g, G, i, j, s, rho[e, s], a, A, b, B, T))
        c0, c1 = max(0., dn(1-rhomax[e, s])), up(1-rho[e, s])
        for u, v in ((i, j), (j, i)):
            x0, x1 = dn(g[u, s]*dn(lo[u]/PT)), up(G[u, s]*up(hi[u]/PT))
            y0, y1 = dn(g[v, s]*dn(lo[v]/PT)), up(G[v, s]*up(hi[v]/PT))
            d0 = dn(dn(dn(1+x0)+y0)+dn(dn(c0*x0)*y0))
            d1 = up(up(up(1+x1)+y1)+up(up(c1*x1)*y1))
            l = dn(dn(dn(2*dn(1+dn(c0*y0)))/d1)-up(1/dn(1+x0)))
            u1 = up(up(up(2*up(1+up(c1*y1)))/d0)-dn(1/up(1+x1)))
            gl[u] = min(dn(g[u, s]*l), dn(G[u, s]*l))
            gu[u] = max(up(g[u, s]*u1), up(G[u, s]*u1))
    # A convex piecewise-linear function reaches its maximum at a slice vertex.
    best = -np.inf
    budget = k*PT//10
    for free in range(k):
        for mask in range(1 << (k-1)):
            p = lo.copy()
            bit = 0
            for j in range(k):
                if j != free:
                    p[j] = hi[j] if mask & (1 << bit) else lo[j]
                    bit += 1
            p[free] = budget-(p.sum()-p[free])
            if p[free] < lo[free] or p[free] > hi[free]:
                continue
            increment = 0.
            for j in range(k):
                a, b = dn((p[j]-centre[j])/PT), up((p[j]-centre[j])/PT)
                increment = up(increment+max(up(gl[j]*a), up(gl[j]*b), up(gu[j]*a), up(gu[j]*b)))
            best = max(best, increment)
    return up(value+best)


def single(h, mats, limit=32768):
    k = len(h)
    assert k in (2, 4)
    PT, Q, T = original.PT, original.Q, original.T
    budget = k*PT//10
    P, Ed = mats
    g, G, r, R = gram(h)
    rec, _, _ = original.solve(h)
    original.replay(h, rec)
    cap = np.nextafter(int(rec['U'])/int(rec['den']), np.inf)
    lb = int(rec['L'])/int(rec['den'])
    nominal = original.nominal(h, *np.triu_indices(k, 1))
    prices = np.array([0., 2., 4., 6., 8., 10., 12., 16., 20.])
    bounds = [(PT//20, PT//5)]*k
    for pa in P:
        a, b = pa.T
        tones = np.arange(k//2)
        ga, gb = nominal[0][a, tones], nominal[0][b, tones]
        rr = nominal[1][original.edgeid(k, a, b), tones]
        def neg(p):
            x, y = p[a]*ga, p[b]*gb
            return -np.sum(np.log1p(x)+np.log1p(y)+2*np.log1p(-rr*(x/(1+x))*(y/(1+y))))
        for initial in (np.full(k, .1), np.tile([.05, .15], k//2)):
            result = minimize(neg, initial, method='SLSQP', bounds=[(.05, .2)]*k,
                              constraints=[dict(type='eq', fun=lambda p: k*.1-p.sum())],
                              options=dict(maxiter=100, ftol=1e-12))
            p = original.project(result.x)
            v = original.filt(h, pa, p)
            lb = max(lb, float(original.lower(h, p, pa, v, np.zeros((k//2, 2, 2)), T).sum())/Q)
    lo, hi = np.array([a for a, _ in bounds]), np.array([b for _, b in bounds])
    def upper(j, a, b):
        return min(cap, original.bound(P[j], Ed[j], g, G, r, a, b, prices, T),
                   taylor(P[j], Ed[j], g, G, r, R, a, b, PT, T))
    heap = [(-upper(j, lo, hi), j, j, lo, hi) for j in range(len(P))]
    heapq.heapify(heap)
    count, uid, fixed = 0, len(P), -np.inf
    norm = k/2*np.log(2)
    while heap and max(-heap[0][0], fixed)-lb > 1e-6*norm and count < limit:
        ng, _, j, a, b = heapq.heappop(heap)
        if -ng <= lb:
            continue
        axis = np.argmax(b-a)
        midpoint = (a[axis]+b[axis])//2
        if midpoint <= a[axis]:
            fixed = max(fixed, -ng)
            continue
        for side in (0, 1):
            x, y = a.copy(), b.copy()
            if side:
                y[axis] = midpoint
            else:
                x[axis] = midpoint
            if x.sum() > budget or y.sum() < budget:
                continue
            x = np.maximum(x, budget-y.sum()+y)
            y = np.minimum(y, budget-x.sum()+x)
            if np.any(x > y):
                continue
            value = min(-ng, upper(j, x, y))
            if value > lb:
                heapq.heappush(heap, (-value, uid, j, x, y))
                uid += 1
        count += 1
    ceiling = max(lb, fixed, -heap[0][0] if heap else -np.inf)
    assert lb <= ceiling <= cap
    return dict(lo_nats=lb, hi_nats=ceiling, split_boxes=count)


def self_check():
    from exact_two import bound as exact
    rng = np.random.default_rng(81281)
    for _ in range(8):
        h = np.ascontiguousarray((rng.normal(size=(2, 4, 1))+1j*rng.normal(size=(2, 4, 1)))*4)
        ref = single(h, original.schedules(2))
        a, b = exact(h[:, :, 0])
        assert ref['lo_nats'] <= b+1e-12 and a <= ref['hi_nats']+1e-12
        assert ref['hi_nats']-ref['lo_nats'] <= 1e-6*np.log(2)
    for _ in range(8):
        h = np.ascontiguousarray((rng.normal(size=(4, 4, 2))+1j*rng.normal(size=(4, 4, 2)))*4)
        g, G, r, R = gram(h)
        P, Ed = original.schedules(4)
        for j in range(len(P)):
            lo, hi = np.full(4, original.PT//20), np.full(4, original.PT//5)
            bound = taylor(P[j], Ed[j], g, G, r, R, lo, hi, original.PT, original.T)
            for _ in range(16):
                p = original.project(rng.uniform(.05, .2, 4))
                v = original.filt(h, P[j], p)
                rate = original.lower(h, p, P[j], v, np.zeros((2, 2, 2)), original.T).sum()/original.Q
                assert rate <= bound+1e-12
    print('Taylor references enclose exact two-user optima and feasible four-user controls.', flush=True)


if __name__ == '__main__':
    self_check()
