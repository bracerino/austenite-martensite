"""Crystallography of the cubic B2 austenite -> monoclinic B19' (or orthorhombic B19) martensite transformation.

Everything here is computed from the lattice parameters only.

Lattice correspondence (variant 1, Otsuka & Ren):
    a_M <-> [1 0 0]_B2,   b_M <-> [0 1 1]_B2,   c_M <-> [0 -1 1]_B2
so a martensite plane (hkl)_M corresponds to the austenite plane C^-T (hkl)_M, which can have
half-integer indices (e.g. (001)_M <-> (0 -1/2 1/2)_B2).

The 12 correspondence variants are obtained by applying the 24 proper cubic rotations (pairs related by the
2-fold axis along b_M = [011]_B2 belong to the same variant).

The angle between normals is evaluated for variant 1 with the martensite placed in the austenite frame
as x = a_M || [100]_B2, y = b_M || [011]_B2, c_M in the x-z plane (so c*_M || [0-11]_B2). This places the
whole monoclinic shear (beta - 90 deg) on the a_M axis.
"""

from dataclasses import dataclass
from functools import lru_cache
from fractions import Fraction
from itertools import permutations, product

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Lattice:
    a: float
    b: float
    c: float
    alpha: float = 90.0
    beta: float = 90.0
    gamma: float = 90.0

    def direct_matrix(self):
        """Rows are the a, b, c vectors in a Cartesian frame (a || x, b in the x-y plane)."""
        al, be, ga = np.radians([self.alpha, self.beta, self.gamma])
        ax = np.array([self.a, 0.0, 0.0])
        bx = np.array([self.b * np.cos(ga), self.b * np.sin(ga), 0.0])
        cx = self.c * np.cos(be)
        cy = self.c * (np.cos(al) - np.cos(be) * np.cos(ga)) / np.sin(ga)
        cz = np.sqrt(max(self.c ** 2 - cx ** 2 - cy ** 2, 0.0))
        return np.array([ax, bx, [cx, cy, cz]])

    def reciprocal_matrix(self):
        """Rows are a*, b*, c* (without 2*pi) in the same Cartesian frame as direct_matrix."""
        return np.linalg.inv(self.direct_matrix()).T

    def d_spacing(self, hkl):
        g = np.atleast_2d(hkl) @ self.reciprocal_matrix()
        with np.errstate(divide="ignore"):
            return 1.0 / np.linalg.norm(g, axis=1)


# Columns are the martensite basis vectors expressed in austenite (B2) lattice coordinates.
CORRESPONDENCE = np.array([[1, 0, 0],
                           [0, 1, -1],
                           [0, 1, 1]], dtype=float)
PLANE_TRANSFORM = np.linalg.inv(CORRESPONDENCE).T  # (hkl)_A = PLANE_TRANSFORM @ (hkl)_M

# Martensite (variant 1) Cartesian frame expressed in the B2 cubic frame: rows = x, y, z unit vectors.
_M_FRAME_IN_A = np.array([[1, 0, 0],
                          [0, 1, 1],
                          [0, -1, 1]], dtype=float)
_M_FRAME_IN_A /= np.linalg.norm(_M_FRAME_IN_A, axis=1)[:, None]


def _cubic_rotations():
    rots = []
    for perm in permutations(range(3)):
        for signs in product((1, -1), repeat=3):
            m = np.zeros((3, 3))
            for i, p in enumerate(perm):
                m[i, p] = signs[i]
            if np.isclose(np.linalg.det(m), 1):
                rots.append(m)
    return rots


def _cubic_point_group():
    rots = _cubic_rotations()
    return rots + [-r for r in rots]


def _variant_rotations():
    """All 24 proper cubic rotations, each tagged with its correspondence variant (1..12).

    Two rotations differing by the 2-fold axis along b_M = [011]_B2 give the same variant; they map
    (hkl)_M and its equivalent (-h k -l)_M, so both are kept to make the M <-> A lookup symmetric.
    """
    b_dir = CORRESPONDENCE[:, 1]
    a_dir = CORRESPONDENCE[:, 0]
    keys, tagged = {}, []
    for r in _cubic_rotations():
        rb = tuple(np.round(r @ b_dir).astype(int))
        ra = tuple(np.round(r @ a_dir).astype(int))
        key = (rb, frozenset({ra, tuple(-x for x in ra)}))
        tagged.append((keys.setdefault(key, len(keys) + 1), r))
    return tagged


CUBIC_OPS = _cubic_point_group()
VARIANT_ROTATIONS = _variant_rotations()
MONOCLINIC_OPS = [np.diag(d) for d in [(1, 1, 1), (-1, -1, -1), (-1, 1, -1), (1, -1, 1)]]
ORTHORHOMBIC_OPS = [np.diag(d) for d in product((1, -1), repeat=3)]


@lru_cache(maxsize=None)
def _multiplicity(hkl, ops_name):
    ops = {"cubic": CUBIC_OPS, "monoclinic": MONOCLINIC_OPS, "orthorhombic": ORTHORHOMBIC_OPS}[ops_name]
    return len({tuple(np.round(op @ np.asarray(hkl, float), 6)) for op in ops})


def _fmt_index(x):
    fr = Fraction(float(x)).limit_denominator(12)
    if fr.denominator == 1:
        return str(fr.numerator)
    if fr == Fraction(1, 2):
        return "½"
    if fr == Fraction(-1, 2):
        return "-½"
    return f"{fr.numerator}/{fr.denominator}"


def format_hkl(hkl):
    return "(" + " ".join(_fmt_index(x) for x in hkl) + ")"


def austenite_allowed(hkl):
    """B2 (Pm-3m, primitive): every integer (hkl) is allowed; half-integer planes are fictitious."""
    return bool(np.allclose(hkl, np.round(hkl), atol=1e-6))


def martensite_allowed(hkl):
    """B19' (P2_1/m) and B19 (Pmcm/Pmma): 0k0 with k odd is extinct."""
    h, k, l = (int(round(v)) for v in hkl)
    return not (h == 0 and l == 0 and k % 2 != 0)


@lru_cache(maxsize=8)
def correspondence_pairs(max_index: int = 4, orthorhombic: bool = False) -> pd.DataFrame:
    """Plane pairs (independent of lattice parameters): every martensite plane with |h|,|k|,|l| <= max_index
    and every distinct austenite plane it maps to under the 12 correspondence variants."""
    m_sym = "orthorhombic" if orthorhombic else "monoclinic"
    rng = range(-max_index, max_index + 1)
    m_planes = np.array([p for p in product(rng, rng, rng) if any(p)], dtype=float)
    a_planes_v1 = m_planes @ PLANE_TRANSFORM.T

    rows = []
    for hkl_m, hkl_a1 in zip(m_planes, a_planes_v1):
        tm = tuple(hkl_m)
        lbl_m, mult_m, allowed_m = format_hkl(tm), _multiplicity(tm, m_sym), martensite_allowed(tm)
        seen = set()
        for v, rot in VARIANT_ROTATIONS:
            ta = tuple(float(x) + 0.0 for x in np.round(rot @ hkl_a1, 6))
            if ta in seen:
                continue
            seen.add(ta)
            rows.append((lbl_m, tm, mult_m, allowed_m, ta, v))

    df = pd.DataFrame(rows, columns=["martensite", "hkl_M", "mult_M", "allowed_M", "hkl_A", "variant"])
    uniq_a = df["hkl_A"].unique()
    df["austenite"] = df["hkl_A"].map({h: format_hkl(h) for h in uniq_a})
    df["mult_A"] = df["hkl_A"].map({h: _multiplicity(h, "cubic") for h in uniq_a})
    df["allowed_A"] = df["hkl_A"].map({h: austenite_allowed(h) for h in uniq_a})
    return df


def build_correspondence(austenite: Lattice, martensite: Lattice, max_index: int = 4) -> pd.DataFrame:
    """Correspondence table with d-spacings, angle between normals and transformation strains."""
    df = correspondence_pairs(max_index, bool(np.isclose(martensite.beta, 90))).copy()

    rec_m_in_a = martensite.reciprocal_matrix() @ _M_FRAME_IN_A  # a*, b*, c* in the B2 cubic frame
    rec_a = austenite.reciprocal_matrix()

    hkl_m = np.array(df["hkl_M"].tolist())
    g_m = hkl_m @ rec_m_in_a
    g_a = (hkl_m @ PLANE_TRANSFORM.T) @ rec_a  # variant 1 partner; d and angle are the same for every variant
    d_m = 1.0 / np.linalg.norm(g_m, axis=1)
    d_a = 1.0 / np.linalg.norm(g_a, axis=1)
    cosang = np.abs(np.sum(g_m * g_a, axis=1)) * d_m * d_a

    df["dM"] = d_m
    df["dA"] = d_a
    df["angle"] = np.degrees(np.arccos(np.clip(cosang, -1, 1)))
    df["strain"] = (df["dM"] - df["dA"]) / df["dA"] * 100.0
    df["strain_shear"] = np.radians(df["angle"]) * 100.0
    return df


def d_to_twotheta(d, wavelength):
    d = np.asarray(d, dtype=float)
    s = wavelength / (2.0 * d)
    with np.errstate(invalid="ignore"):
        tt = 2.0 * np.degrees(np.arcsin(s))
    return np.where(np.abs(s) <= 1, tt, np.nan)


# ---------- peak profile functions (all normalised to unit height at x0) ----------

def gaussian(x, x0, fwhm):
    return np.exp(-4.0 * np.log(2.0) * ((x - x0) / fwhm) ** 2)


def lorentzian(x, x0, fwhm):
    return 1.0 / (1.0 + 4.0 * ((x - x0) / fwhm) ** 2)


def pseudo_voigt(x, x0, fwhm, eta=0.5):
    return eta * lorentzian(x, x0, fwhm) + (1.0 - eta) * gaussian(x, x0, fwhm)


def pearson_vii(x, x0, fwhm, m=1.5):
    k = 2.0 ** (1.0 / m) - 1.0
    return (1.0 + 4.0 * k * ((x - x0) / fwhm) ** 2) ** (-m)


def caglioti_fwhm(two_theta, u, v, w):
    """Caglioti: FWHM^2 = U tan^2(theta) + V tan(theta) + W (degrees 2theta)."""
    t = np.tan(np.radians(two_theta) / 2.0)
    return np.sqrt(np.clip(u * t ** 2 + v * t + w, 1e-8, None))
