#!/usr/bin/env python3

def frange(start, stop, step):
    i = start
    while i < stop:
        yield i
        i += step

def RMSD(X, Y):
    from numpy import sqrt
    dist = pairwiseDistanceSquared(X, Y)
    return sqrt(1/dist.shape[0] * dist.min(axis=0).sum())

def pairwiseDistanceSquared(X, Y):
    return ((X[None, :, :] - Y[:, None, :]) ** 2).sum(axis=2)

def argmin(seq, key=lambda x: x):
    amin = next(s)
    for s in seq:
        if key(s) < key(amin):
            amin = s
    return current

def globalAlignment(X, Y, w=0.5):
    from numpy import array
    from math import pi

    D = X.shape[1]
    if D != 2:
        raise NotImplementedError("Not implemented for D != 2")

    error = float('inf')
    for theta in frange(0, 2*pi, pi/4):
        rotation = array([[cos(theta), -sin(theta)],
                          [sin(theta), cos(theta)]])
        estimate = driftRigid(X, Y, w, (rotation, array([0.0, 0.0]), 1.0))
        for _ in range(100):
            try:
                R, t, s = next(estimate)
            except StopIteration:
                break
        new_error = RMSD(X, s * R.dot(Y.T).T + t)
        if new_error < error:
            ret = R, t, s
            error = new_error
    return ret


def driftRigid(X, Y, w=0.5, initial_guess=None):
    from numpy.linalg import svd, det
    from numpy import exp, trace, diag
    from numpy import eye, zeros
    from numpy import seterr
    from math import pi

    if not (X.ndim == Y.ndim == 2):
        raise ValueError("Expecting 2D input data, got {}D and {}D"
                         .format(X.ndim, Y.ndim))
    if X.shape[1] != Y.shape[1]:
        raise ValueError("Expecting points with matching dimensionality, got {} and {}"
                         .format(X.shape[1:], Y.shape[1:]))
    if not (0 <= w <= 1):
        raise ValueError("w must be in the range [0..1], got {}"
                         .format(w))

    D = X.shape[1]
    N = len(X)
    M = len(Y)

    sigma_squared = 1 / (D*M*N) * pairwiseDistanceSquared(X, Y).sum()

    if initial_guess is not None:
        R, t, s = initial_guess
    else:
        R, t, s = eye(D), zeros(D), 1.0

    old_exceptions = seterr(divide='raise', over='raise', under='raise')

    while True:
        # E-step
        pairwise_dist_squared = pairwiseDistanceSquared(X, s * R.dot(Y.T).T + t)
        try:
            P = (exp(-1/(2*sigma_squared) * pairwise_dist_squared)
                / (exp(-1/(2*sigma_squared) * pairwise_dist_squared).sum(axis=0)
                    + (2 * pi * sigma_squared) ** (D/2)
                    * w / (1-w) * M / N))
        except FloatingPointError:
            seterr(**old_exceptions)
            break

        # M-step
        N_p = P.sum()
        mu_x = 1 / N_p * X.T.dot(P.T.sum(axis=1))
        mu_y = 1 / N_p * Y.T.dot(P.sum(axis=1))
        X_hat = X - mu_x.T
        Y_hat = Y - mu_y.T
        A = X_hat.T.dot(P.T).dot(Y_hat)
        U, _, VT = svd(A)
        C = eye(D)
        C[-1, -1] = det(U.dot(VT))
        R = U.dot(C).dot(VT)
        s = trace(A.T.dot(R)) / trace(Y_hat.T.dot(diag(P.sum(axis=1))).dot(Y_hat))
        t = mu_x - s * R.dot(mu_y)
        sigma_squared = 1 / (N_p * D) * (trace(X_hat.T.dot(diag(P.T.sum(axis=1))).dot(X_hat))
                                         - s * trace(A.T.dot(R)))

        yield R, t, s

if __name__ == "__main__":
    from math import sin, cos, pi
    from numpy.random import rand, seed
    from numpy import array
    from matplotlib import pyplot as plt

    seed(4)

    pt1 = rand(12, 2)
    plt.scatter(pt1[:, 0], pt1[:, 1], color='blue')

    translation = array([0.1, 0.3])
    scale = 0.5

    errors = []

    for theta in frange(0, 2*pi, pi/20):
        rotation = array([[cos(theta), -sin(theta)],
                        [sin(theta), cos(theta)]])
        pt2 = rotation.dot(pt1[:10].T).T * scale + translation
        plt.scatter(pt2[:, 0], pt2[:, 1], color='red', alpha=0.5)

        R, t, s = globalAlignment(pt1, pt2)
        p_fitted = R.dot(pt2.T).T * s + t
        plt.scatter(p_fitted[:, 0], p_fitted[:, 1], color='green', marker='+')
        errors.append((theta, RMSD(pt1, p_fitted)))

    plt.figure()
    plt.plot(*zip(*errors))
    plt.show()
