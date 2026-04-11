"""
Non-linear fiber extension search for E677 counterexamples.

Unlike color-extensions.py (which uses affine fibers f(x,y) = Ax+By+C mod K),
this script uses full function tables for the fiber operations, allowing
non-affine structures. Supports optional anti-E255 mode to search for
E677-satisfying magmas that violate E255.

Usage:
  python color-extensions-nonlinear.py <mode> <magma_idx> [max_K]

  mode: "677" (find E677 models) or "anti255" (find E677 ∧ ¬E255 models)
  magma_idx: index into MAGMA_DEFS (0=7/0, 1=9/0, 2=29/0)
  max_K: maximum fiber size (default: 5)
"""

from z3 import *
import sys


# --- Base magma definitions (imported from color-extensions.py) ---
# Only the small ones are practical for non-linear search.

def magmadef_7_0():
    name = "7/0"
    n = 7
    m = dict()
    c = dict()
    m[(0, 0)] = 0; m[(0, 1)] = 1; m[(0, 2)] = 2; m[(0, 3)] = 3; m[(0, 4)] = 4; m[(0, 5)] = 5; m[(0, 6)] = 6; m[(1, 0)] = 4; m[(1, 1)] = 5; m[(1, 2)] = 6; m[(1, 3)] = 0; m[(1, 4)] = 1; m[(1, 5)] = 2; m[(1, 6)] = 3; m[(2, 0)] = 1; m[(2, 1)] = 2; m[(2, 2)] = 3; m[(2, 3)] = 4; m[(2, 4)] = 5; m[(2, 5)] = 6; m[(2, 6)] = 0; m[(3, 0)] = 5; m[(3, 1)] = 6; m[(3, 2)] = 0; m[(3, 3)] = 1; m[(3, 4)] = 2; m[(3, 5)] = 3; m[(3, 6)] = 4; m[(4, 0)] = 2; m[(4, 1)] = 3; m[(4, 2)] = 4; m[(4, 3)] = 5; m[(4, 4)] = 6; m[(4, 5)] = 0; m[(4, 6)] = 1; m[(5, 0)] = 6; m[(5, 1)] = 0; m[(5, 2)] = 1; m[(5, 3)] = 2; m[(5, 4)] = 3; m[(5, 5)] = 4; m[(5, 6)] = 5; m[(6, 0)] = 3; m[(6, 1)] = 4; m[(6, 2)] = 5; m[(6, 3)] = 6; m[(6, 4)] = 0; m[(6, 5)] = 1; m[(6, 6)] = 2;
    c[(0, 0)] = 0; c[(0, 1)] = 1; c[(0, 2)] = 1; c[(0, 3)] = 1; c[(0, 4)] = 1; c[(0, 5)] = 1; c[(0, 6)] = 1; c[(1, 0)] = 2; c[(1, 1)] = 3; c[(1, 2)] = 4; c[(1, 3)] = 5; c[(1, 4)] = 6; c[(1, 5)] = 7; c[(1, 6)] = 8; c[(2, 0)] = 2; c[(2, 1)] = 6; c[(2, 2)] = 3; c[(2, 3)] = 7; c[(2, 4)] = 4; c[(2, 5)] = 8; c[(2, 6)] = 5; c[(3, 0)] = 2; c[(3, 1)] = 7; c[(3, 2)] = 5; c[(3, 3)] = 3; c[(3, 4)] = 8; c[(3, 5)] = 6; c[(3, 6)] = 4; c[(4, 0)] = 2; c[(4, 1)] = 4; c[(4, 2)] = 6; c[(4, 3)] = 8; c[(4, 4)] = 3; c[(4, 5)] = 5; c[(4, 6)] = 7; c[(5, 0)] = 2; c[(5, 1)] = 5; c[(5, 2)] = 8; c[(5, 3)] = 4; c[(5, 4)] = 7; c[(5, 5)] = 3; c[(5, 6)] = 6; c[(6, 0)] = 2; c[(6, 1)] = 8; c[(6, 2)] = 7; c[(6, 3)] = 6; c[(6, 4)] = 5; c[(6, 5)] = 4; c[(6, 6)] = 3;
    t = [(0, 0, 0, 0, ), (1, 2, 6, 1, ), (2, 4, 1, 5, ), (3, 5, 2, 6, ), (4, 8, 4, 7, ), (5, 1, 7, 8, ), (6, 3, 5, 2, ), (7, 6, 8, 3, ), (8, 7, 3, 4, ), ]
    return n, name, m, c, t

def magmadef_9_0():
    name = "9/0"
    n = 9
    m = dict()
    c = dict()
    m[(0, 0)] = 0; m[(0, 1)] = 8; m[(0, 2)] = 4; m[(0, 3)] = 7; m[(0, 4)] = 3; m[(0, 5)] = 2; m[(0, 6)] = 5; m[(0, 7)] = 1; m[(0, 8)] = 6; m[(1, 0)] = 1; m[(1, 1)] = 6; m[(1, 2)] = 5; m[(1, 3)] = 8; m[(1, 4)] = 4; m[(1, 5)] = 0; m[(1, 6)] = 3; m[(1, 7)] = 2; m[(1, 8)] = 7; m[(2, 0)] = 2; m[(2, 1)] = 7; m[(2, 2)] = 3; m[(2, 3)] = 6; m[(2, 4)] = 5; m[(2, 5)] = 1; m[(2, 6)] = 4; m[(2, 7)] = 0; m[(2, 8)] = 8; m[(3, 0)] = 3; m[(3, 1)] = 2; m[(3, 2)] = 7; m[(3, 3)] = 1; m[(3, 4)] = 6; m[(3, 5)] = 5; m[(3, 6)] = 8; m[(3, 7)] = 4; m[(3, 8)] = 0; m[(4, 0)] = 4; m[(4, 1)] = 0; m[(4, 2)] = 8; m[(4, 3)] = 2; m[(4, 4)] = 7; m[(4, 5)] = 3; m[(4, 6)] = 6; m[(4, 7)] = 5; m[(4, 8)] = 1; m[(5, 0)] = 5; m[(5, 1)] = 1; m[(5, 2)] = 6; m[(5, 3)] = 0; m[(5, 4)] = 8; m[(5, 5)] = 4; m[(5, 6)] = 7; m[(5, 7)] = 3; m[(5, 8)] = 2; m[(6, 0)] = 6; m[(6, 1)] = 5; m[(6, 2)] = 1; m[(6, 3)] = 4; m[(6, 4)] = 0; m[(6, 5)] = 8; m[(6, 6)] = 2; m[(6, 7)] = 7; m[(6, 8)] = 3; m[(7, 0)] = 7; m[(7, 1)] = 3; m[(7, 2)] = 2; m[(7, 3)] = 5; m[(7, 4)] = 1; m[(7, 5)] = 6; m[(7, 6)] = 0; m[(7, 7)] = 8; m[(7, 8)] = 4; m[(8, 0)] = 8; m[(8, 1)] = 4; m[(8, 2)] = 0; m[(8, 3)] = 3; m[(8, 4)] = 2; m[(8, 5)] = 7; m[(8, 6)] = 1; m[(8, 7)] = 6; m[(8, 8)] = 5;
    c[(0, 0)] = 0; c[(0, 1)] = 1; c[(0, 2)] = 1; c[(0, 3)] = 1; c[(0, 4)] = 1; c[(0, 5)] = 1; c[(0, 6)] = 1; c[(0, 7)] = 1; c[(0, 8)] = 1; c[(1, 0)] = 2; c[(1, 1)] = 3; c[(1, 2)] = 4; c[(1, 3)] = 5; c[(1, 4)] = 6; c[(1, 5)] = 7; c[(1, 6)] = 8; c[(1, 7)] = 9; c[(1, 8)] = 10; c[(2, 0)] = 2; c[(2, 1)] = 4; c[(2, 2)] = 3; c[(2, 3)] = 8; c[(2, 4)] = 10; c[(2, 5)] = 9; c[(2, 6)] = 5; c[(2, 7)] = 7; c[(2, 8)] = 6; c[(3, 0)] = 2; c[(3, 1)] = 8; c[(3, 2)] = 5; c[(3, 3)] = 3; c[(3, 4)] = 9; c[(3, 5)] = 6; c[(3, 6)] = 4; c[(3, 7)] = 10; c[(3, 8)] = 7; c[(4, 0)] = 2; c[(4, 1)] = 7; c[(4, 2)] = 9; c[(4, 3)] = 10; c[(4, 4)] = 3; c[(4, 5)] = 5; c[(4, 6)] = 6; c[(4, 7)] = 8; c[(4, 8)] = 4; c[(5, 0)] = 2; c[(5, 1)] = 6; c[(5, 2)] = 10; c[(5, 3)] = 7; c[(5, 4)] = 8; c[(5, 5)] = 3; c[(5, 6)] = 9; c[(5, 7)] = 4; c[(5, 8)] = 5; c[(6, 0)] = 2; c[(6, 1)] = 5; c[(6, 2)] = 8; c[(6, 3)] = 4; c[(6, 4)] = 7; c[(6, 5)] = 10; c[(6, 6)] = 3; c[(6, 7)] = 6; c[(6, 8)] = 9; c[(7, 0)] = 2; c[(7, 1)] = 10; c[(7, 2)] = 6; c[(7, 3)] = 9; c[(7, 4)] = 5; c[(7, 5)] = 4; c[(7, 6)] = 7; c[(7, 7)] = 3; c[(7, 8)] = 8; c[(8, 0)] = 2; c[(8, 1)] = 9; c[(8, 2)] = 7; c[(8, 3)] = 6; c[(8, 4)] = 4; c[(8, 5)] = 8; c[(8, 6)] = 10; c[(8, 7)] = 5; c[(8, 8)] = 3;
    t = [(0, 0, 0, 0, ), (1, 2, 10, 1, ), (2, 3, 1, 7, ), (3, 5, 7, 2, ), (4, 6, 4, 9, ), (5, 9, 9, 8, ), (6, 7, 2, 6, ), (7, 1, 5, 4, ), (8, 8, 8, 3, ), (9, 4, 3, 10, ), (10, 10, 6, 5, ), ]
    return n, name, m, c, t


def magmadef_29_0():
    name = "29/0"
    n = 29
    m = dict()
    c = dict()
    m[(0, 0)] = 0; m[(0, 1)] = 28; m[(0, 2)] = 15; m[(0, 3)] = 21; m[(0, 4)] = 17; m[(0, 5)] = 13; m[(0, 6)] = 26; m[(0, 7)] = 9; m[(0, 8)] = 12; m[(0, 9)] = 8; m[(0, 10)] = 25; m[(0, 11)] = 2; m[(0, 12)] = 1; m[(0, 13)] = 27; m[(0, 14)] = 4; m[(0, 15)] = 16; m[(0, 16)] = 10; m[(0, 17)] = 23; m[(0, 18)] = 7; m[(0, 19)] = 14; m[(0, 20)] = 3; m[(0, 21)] = 5; m[(0, 22)] = 19; m[(0, 23)] = 11; m[(0, 24)] = 18; m[(0, 25)] = 6; m[(0, 26)] = 22; m[(0, 27)] = 24; m[(0, 28)] = 20; m[(1, 0)] = 25; m[(1, 1)] = 1; m[(1, 2)] = 28; m[(1, 3)] = 14; m[(1, 4)] = 27; m[(1, 5)] = 16; m[(1, 6)] = 7; m[(1, 7)] = 26; m[(1, 8)] = 10; m[(1, 9)] = 13; m[(1, 10)] = 9; m[(1, 11)] = 24; m[(1, 12)] = 3; m[(1, 13)] = 2; m[(1, 14)] = 15; m[(1, 15)] = 11; m[(1, 16)] = 22; m[(1, 17)] = 8; m[(1, 18)] = 20; m[(1, 19)] = 4; m[(1, 20)] = 5; m[(1, 21)] = 18; m[(1, 22)] = 12; m[(1, 23)] = 17; m[(1, 24)] = 0; m[(1, 25)] = 21; m[(1, 26)] = 23; m[(1, 27)] = 6; m[(1, 28)] = 19; m[(2, 0)] = 8; m[(2, 1)] = 24; m[(2, 2)] = 2; m[(2, 3)] = 28; m[(2, 4)] = 20; m[(2, 5)] = 26; m[(2, 6)] = 15; m[(2, 7)] = 3; m[(2, 8)] = 25; m[(2, 9)] = 11; m[(2, 10)] = 7; m[(2, 11)] = 10; m[(2, 12)] = 23; m[(2, 13)] = 4; m[(2, 14)] = 12; m[(2, 15)] = 21; m[(2, 16)] = 9; m[(2, 17)] = 19; m[(2, 18)] = 5; m[(2, 19)] = 6; m[(2, 20)] = 14; m[(2, 21)] = 13; m[(2, 22)] = 16; m[(2, 23)] = 1; m[(2, 24)] = 27; m[(2, 25)] = 22; m[(2, 26)] = 0; m[(2, 27)] = 17; m[(2, 28)] = 18; m[(3, 0)] = 14; m[(3, 1)] = 9; m[(3, 2)] = 23; m[(3, 3)] = 3; m[(3, 4)] = 28; m[(3, 5)] = 19; m[(3, 6)] = 25; m[(3, 7)] = 5; m[(3, 8)] = 4; m[(3, 9)] = 24; m[(3, 10)] = 12; m[(3, 11)] = 8; m[(3, 12)] = 11; m[(3, 13)] = 22; m[(3, 14)] = 27; m[(3, 15)] = 10; m[(3, 16)] = 18; m[(3, 17)] = 6; m[(3, 18)] = 0; m[(3, 19)] = 20; m[(3, 20)] = 13; m[(3, 21)] = 15; m[(3, 22)] = 2; m[(3, 23)] = 26; m[(3, 24)] = 21; m[(3, 25)] = 1; m[(3, 26)] = 16; m[(3, 27)] = 7; m[(3, 28)] = 17; m[(4, 0)] = 24; m[(4, 1)] = 20; m[(4, 2)] = 10; m[(4, 3)] = 22; m[(4, 4)] = 4; m[(4, 5)] = 28; m[(4, 6)] = 18; m[(4, 7)] = 21; m[(4, 8)] = 6; m[(4, 9)] = 5; m[(4, 10)] = 23; m[(4, 11)] = 13; m[(4, 12)] = 9; m[(4, 13)] = 12; m[(4, 14)] = 11; m[(4, 15)] = 17; m[(4, 16)] = 0; m[(4, 17)] = 1; m[(4, 18)] = 19; m[(4, 19)] = 7; m[(4, 20)] = 26; m[(4, 21)] = 3; m[(4, 22)] = 25; m[(4, 23)] = 27; m[(4, 24)] = 2; m[(4, 25)] = 15; m[(4, 26)] = 8; m[(4, 27)] = 14; m[(4, 28)] = 16; m[(5, 0)] = 17; m[(5, 1)] = 23; m[(5, 2)] = 19; m[(5, 3)] = 11; m[(5, 4)] = 21; m[(5, 5)] = 5; m[(5, 6)] = 28; m[(5, 7)] = 13; m[(5, 8)] = 27; m[(5, 9)] = 0; m[(5, 10)] = 6; m[(5, 11)] = 22; m[(5, 12)] = 7; m[(5, 13)] = 10; m[(5, 14)] = 16; m[(5, 15)] = 1; m[(5, 16)] = 2; m[(5, 17)] = 18; m[(5, 18)] = 8; m[(5, 19)] = 25; m[(5, 20)] = 12; m[(5, 21)] = 24; m[(5, 22)] = 26; m[(5, 23)] = 3; m[(5, 24)] = 14; m[(5, 25)] = 9; m[(5, 26)] = 20; m[(5, 27)] = 4; m[(5, 28)] = 15; m[(6, 0)] = 28; m[(6, 1)] = 16; m[(6, 2)] = 22; m[(6, 3)] = 18; m[(6, 4)] = 12; m[(6, 5)] = 27; m[(6, 6)] = 6; m[(6, 7)] = 11; m[(6, 8)] = 7; m[(6, 9)] = 26; m[(6, 10)] = 1; m[(6, 11)] = 0; m[(6, 12)] = 21; m[(6, 13)] = 8; m[(6, 14)] = 2; m[(6, 15)] = 3; m[(6, 16)] = 17; m[(6, 17)] = 9; m[(6, 18)] = 24; m[(6, 19)] = 13; m[(6, 20)] = 15; m[(6, 21)] = 25; m[(6, 22)] = 4; m[(6, 23)] = 20; m[(6, 24)] = 10; m[(6, 25)] = 19; m[(6, 26)] = 5; m[(6, 27)] = 23; m[(6, 28)] = 14; m[(7, 0)] = 2; m[(7, 1)] = 5; m[(7, 2)] = 1; m[(7, 3)] = 15; m[(7, 4)] = 9; m[(7, 5)] = 8; m[(7, 6)] = 17; m[(7, 7)] = 7; m[(7, 8)] = 28; m[(7, 9)] = 25; m[(7, 10)] = 18; m[(7, 11)] = 27; m[(7, 12)] = 6; m[(7, 13)] = 16; m[(7, 14)] = 21; m[(7, 15)] = 13; m[(7, 16)] = 19; m[(7, 17)] = 14; m[(7, 18)] = 12; m[(7, 19)] = 22; m[(7, 20)] = 4; m[(7, 21)] = 0; m[(7, 22)] = 24; m[(7, 23)] = 10; m[(7, 24)] = 11; m[(7, 25)] = 26; m[(7, 26)] = 3; m[(7, 27)] = 20; m[(7, 28)] = 23; m[(8, 0)] = 16; m[(8, 1)] = 3; m[(8, 2)] = 6; m[(8, 3)] = 2; m[(8, 4)] = 14; m[(8, 5)] = 10; m[(8, 6)] = 9; m[(8, 7)] = 15; m[(8, 8)] = 8; m[(8, 9)] = 28; m[(8, 10)] = 24; m[(8, 11)] = 17; m[(8, 12)] = 26; m[(8, 13)] = 0; m[(8, 14)] = 7; m[(8, 15)] = 18; m[(8, 16)] = 20; m[(8, 17)] = 13; m[(8, 18)] = 21; m[(8, 19)] = 5; m[(8, 20)] = 27; m[(8, 21)] = 23; m[(8, 22)] = 11; m[(8, 23)] = 12; m[(8, 24)] = 25; m[(8, 25)] = 4; m[(8, 26)] = 19; m[(8, 27)] = 1; m[(8, 28)] = 22; m[(9, 0)] = 10; m[(9, 1)] = 15; m[(9, 2)] = 4; m[(9, 3)] = 0; m[(9, 4)] = 3; m[(9, 5)] = 20; m[(9, 6)] = 11; m[(9, 7)] = 1; m[(9, 8)] = 14; m[(9, 9)] = 9; m[(9, 10)] = 28; m[(9, 11)] = 23; m[(9, 12)] = 16; m[(9, 13)] = 25; m[(9, 14)] = 17; m[(9, 15)] = 19; m[(9, 16)] = 7; m[(9, 17)] = 27; m[(9, 18)] = 6; m[(9, 19)] = 26; m[(9, 20)] = 8; m[(9, 21)] = 12; m[(9, 22)] = 13; m[(9, 23)] = 24; m[(9, 24)] = 5; m[(9, 25)] = 18; m[(9, 26)] = 2; m[(9, 27)] = 22; m[(9, 28)] = 21; m[(10, 0)] = 12; m[(10, 1)] = 11; m[(10, 2)] = 14; m[(10, 3)] = 5; m[(10, 4)] = 1; m[(10, 5)] = 4; m[(10, 6)] = 19; m[(10, 7)] = 24; m[(10, 8)] = 2; m[(10, 9)] = 20; m[(10, 10)] = 10; m[(10, 11)] = 28; m[(10, 12)] = 22; m[(10, 13)] = 15; m[(10, 14)] = 18; m[(10, 15)] = 8; m[(10, 16)] = 26; m[(10, 17)] = 0; m[(10, 18)] = 25; m[(10, 19)] = 9; m[(10, 20)] = 16; m[(10, 21)] = 7; m[(10, 22)] = 23; m[(10, 23)] = 6; m[(10, 24)] = 17; m[(10, 25)] = 3; m[(10, 26)] = 21; m[(10, 27)] = 13; m[(10, 28)] = 27; m[(11, 0)] = 18; m[(11, 1)] = 13; m[(11, 2)] = 12; m[(11, 3)] = 20; m[(11, 4)] = 6; m[(11, 5)] = 2; m[(11, 6)] = 5; m[(11, 7)] = 14; m[(11, 8)] = 23; m[(11, 9)] = 3; m[(11, 10)] = 19; m[(11, 11)] = 11; m[(11, 12)] = 28; m[(11, 13)] = 21; m[(11, 14)] = 9; m[(11, 15)] = 25; m[(11, 16)] = 1; m[(11, 17)] = 24; m[(11, 18)] = 10; m[(11, 19)] = 15; m[(11, 20)] = 17; m[(11, 21)] = 22; m[(11, 22)] = 0; m[(11, 23)] = 16; m[(11, 24)] = 4; m[(11, 25)] = 27; m[(11, 26)] = 7; m[(11, 27)] = 8; m[(11, 28)] = 26; m[(12, 0)] = 6; m[(12, 1)] = 17; m[(12, 2)] = 7; m[(12, 3)] = 13; m[(12, 4)] = 19; m[(12, 5)] = 0; m[(12, 6)] = 3; m[(12, 7)] = 27; m[(12, 8)] = 20; m[(12, 9)] = 22; m[(12, 10)] = 4; m[(12, 11)] = 18; m[(12, 12)] = 12; m[(12, 13)] = 28; m[(12, 14)] = 24; m[(12, 15)] = 2; m[(12, 16)] = 23; m[(12, 17)] = 11; m[(12, 18)] = 14; m[(12, 19)] = 16; m[(12, 20)] = 10; m[(12, 21)] = 1; m[(12, 22)] = 15; m[(12, 23)] = 5; m[(12, 24)] = 26; m[(12, 25)] = 8; m[(12, 26)] = 9; m[(12, 27)] = 21; m[(12, 28)] = 25; m[(13, 0)] = 4; m[(13, 1)] = 0; m[(13, 2)] = 16; m[(13, 3)] = 8; m[(13, 4)] = 7; m[(13, 5)] = 18; m[(13, 6)] = 1; m[(13, 7)] = 28; m[(13, 8)] = 26; m[(13, 9)] = 19; m[(13, 10)] = 21; m[(13, 11)] = 5; m[(13, 12)] = 17; m[(13, 13)] = 13; m[(13, 14)] = 3; m[(13, 15)] = 22; m[(13, 16)] = 12; m[(13, 17)] = 20; m[(13, 18)] = 15; m[(13, 19)] = 11; m[(13, 20)] = 23; m[(13, 21)] = 14; m[(13, 22)] = 6; m[(13, 23)] = 25; m[(13, 24)] = 9; m[(13, 25)] = 10; m[(13, 26)] = 27; m[(13, 27)] = 2; m[(13, 28)] = 24; m[(14, 0)] = 5; m[(14, 1)] = 10; m[(14, 2)] = 3; m[(14, 3)] = 24; m[(14, 4)] = 18; m[(14, 5)] = 11; m[(14, 6)] = 27; m[(14, 7)] = 20; m[(14, 8)] = 22; m[(14, 9)] = 16; m[(14, 10)] = 0; m[(14, 11)] = 25; m[(14, 12)] = 8; m[(14, 13)] = 6; m[(14, 14)] = 14; m[(14, 15)] = 28; m[(14, 16)] = 13; m[(14, 17)] = 2; m[(14, 18)] = 9; m[(14, 19)] = 23; m[(14, 20)] = 1; m[(14, 21)] = 26; m[(14, 22)] = 21; m[(14, 23)] = 7; m[(14, 24)] = 19; m[(14, 25)] = 17; m[(14, 26)] = 15; m[(14, 27)] = 12; m[(14, 28)] = 4; m[(15, 0)] = 9; m[(15, 1)] = 2; m[(15, 2)] = 25; m[(15, 3)] = 19; m[(15, 4)] = 10; m[(15, 5)] = 21; m[(15, 6)] = 4; m[(15, 7)] = 23; m[(15, 8)] = 17; m[(15, 9)] = 6; m[(15, 10)] = 26; m[(15, 11)] = 7; m[(15, 12)] = 5; m[(15, 13)] = 14; m[(15, 14)] = 0; m[(15, 15)] = 15; m[(15, 16)] = 28; m[(15, 17)] = 12; m[(15, 18)] = 1; m[(15, 19)] = 8; m[(15, 20)] = 24; m[(15, 21)] = 11; m[(15, 22)] = 27; m[(15, 23)] = 22; m[(15, 24)] = 13; m[(15, 25)] = 20; m[(15, 26)] = 18; m[(15, 27)] = 16; m[(15, 28)] = 3; m[(16, 0)] = 1; m[(16, 1)] = 26; m[(16, 2)] = 20; m[(16, 3)] = 9; m[(16, 4)] = 22; m[(16, 5)] = 3; m[(16, 6)] = 8; m[(16, 7)] = 18; m[(16, 8)] = 5; m[(16, 9)] = 27; m[(16, 10)] = 13; m[(16, 11)] = 4; m[(16, 12)] = 15; m[(16, 13)] = 24; m[(16, 14)] = 25; m[(16, 15)] = 6; m[(16, 16)] = 16; m[(16, 17)] = 28; m[(16, 18)] = 11; m[(16, 19)] = 0; m[(16, 20)] = 7; m[(16, 21)] = 17; m[(16, 22)] = 10; m[(16, 23)] = 21; m[(16, 24)] = 23; m[(16, 25)] = 12; m[(16, 26)] = 14; m[(16, 27)] = 19; m[(16, 28)] = 2; m[(17, 0)] = 27; m[(17, 1)] = 14; m[(17, 2)] = 8; m[(17, 3)] = 23; m[(17, 4)] = 2; m[(17, 5)] = 7; m[(17, 6)] = 0; m[(17, 7)] = 4; m[(17, 8)] = 21; m[(17, 9)] = 12; m[(17, 10)] = 3; m[(17, 11)] = 16; m[(17, 12)] = 25; m[(17, 13)] = 19; m[(17, 14)] = 13; m[(17, 15)] = 26; m[(17, 16)] = 5; m[(17, 17)] = 17; m[(17, 18)] = 28; m[(17, 19)] = 10; m[(17, 20)] = 6; m[(17, 21)] = 20; m[(17, 22)] = 18; m[(17, 23)] = 9; m[(17, 24)] = 22; m[(17, 25)] = 24; m[(17, 26)] = 11; m[(17, 27)] = 15; m[(17, 28)] = 1; m[(18, 0)] = 15; m[(18, 1)] = 7; m[(18, 2)] = 24; m[(18, 3)] = 1; m[(18, 4)] = 13; m[(18, 5)] = 6; m[(18, 6)] = 21; m[(18, 7)] = 22; m[(18, 8)] = 11; m[(18, 9)] = 2; m[(18, 10)] = 17; m[(18, 11)] = 26; m[(18, 12)] = 20; m[(18, 13)] = 3; m[(18, 14)] = 5; m[(18, 15)] = 12; m[(18, 16)] = 27; m[(18, 17)] = 4; m[(18, 18)] = 18; m[(18, 19)] = 28; m[(18, 20)] = 9; m[(18, 21)] = 16; m[(18, 22)] = 14; m[(18, 23)] = 19; m[(18, 24)] = 8; m[(18, 25)] = 23; m[(18, 26)] = 25; m[(18, 27)] = 10; m[(18, 28)] = 0; m[(19, 0)] = 13; m[(19, 1)] = 25; m[(19, 2)] = 0; m[(19, 3)] = 12; m[(19, 4)] = 5; m[(19, 5)] = 22; m[(19, 6)] = 16; m[(19, 7)] = 10; m[(19, 8)] = 1; m[(19, 9)] = 18; m[(19, 10)] = 27; m[(19, 11)] = 14; m[(19, 12)] = 2; m[(19, 13)] = 23; m[(19, 14)] = 8; m[(19, 15)] = 4; m[(19, 16)] = 11; m[(19, 17)] = 21; m[(19, 18)] = 3; m[(19, 19)] = 19; m[(19, 20)] = 28; m[(19, 21)] = 9; m[(19, 22)] = 17; m[(19, 23)] = 15; m[(19, 24)] = 20; m[(19, 25)] = 7; m[(19, 26)] = 24; m[(19, 27)] = 26; m[(19, 28)] = 6; m[(20, 0)] = 26; m[(20, 1)] = 6; m[(20, 2)] = 11; m[(20, 3)] = 4; m[(20, 4)] = 23; m[(20, 5)] = 17; m[(20, 6)] = 12; m[(20, 7)] = 0; m[(20, 8)] = 19; m[(20, 9)] = 21; m[(20, 10)] = 15; m[(20, 11)] = 1; m[(20, 12)] = 24; m[(20, 13)] = 9; m[(20, 14)] = 28; m[(20, 15)] = 7; m[(20, 16)] = 3; m[(20, 17)] = 10; m[(20, 18)] = 22; m[(20, 19)] = 2; m[(20, 20)] = 20; m[(20, 21)] = 27; m[(20, 22)] = 8; m[(20, 23)] = 18; m[(20, 24)] = 16; m[(20, 25)] = 14; m[(20, 26)] = 13; m[(20, 27)] = 25; m[(20, 28)] = 5; m[(21, 0)] = 19; m[(21, 1)] = 4; m[(21, 2)] = 9; m[(21, 3)] = 27; m[(21, 4)] = 16; m[(21, 5)] = 23; m[(21, 6)] = 10; m[(21, 7)] = 25; m[(21, 8)] = 0; m[(21, 9)] = 14; m[(21, 10)] = 8; m[(21, 11)] = 6; m[(21, 12)] = 13; m[(21, 13)] = 18; m[(21, 14)] = 1; m[(21, 15)] = 20; m[(21, 16)] = 15; m[(21, 17)] = 3; m[(21, 18)] = 26; m[(21, 19)] = 24; m[(21, 20)] = 22; m[(21, 21)] = 21; m[(21, 22)] = 28; m[(21, 23)] = 2; m[(21, 24)] = 12; m[(21, 25)] = 5; m[(21, 26)] = 17; m[(21, 27)] = 11; m[(21, 28)] = 7; m[(22, 0)] = 3; m[(22, 1)] = 8; m[(22, 2)] = 21; m[(22, 3)] = 17; m[(22, 4)] = 24; m[(22, 5)] = 9; m[(22, 6)] = 20; m[(22, 7)] = 6; m[(22, 8)] = 15; m[(22, 9)] = 7; m[(22, 10)] = 5; m[(22, 11)] = 12; m[(22, 12)] = 19; m[(22, 13)] = 26; m[(22, 14)] = 23; m[(22, 15)] = 0; m[(22, 16)] = 14; m[(22, 17)] = 16; m[(22, 18)] = 2; m[(22, 19)] = 27; m[(22, 20)] = 25; m[(22, 21)] = 10; m[(22, 22)] = 22; m[(22, 23)] = 28; m[(22, 24)] = 1; m[(22, 25)] = 11; m[(22, 26)] = 4; m[(22, 27)] = 18; m[(22, 28)] = 13; m[(23, 0)] = 7; m[(23, 1)] = 22; m[(23, 2)] = 18; m[(23, 3)] = 25; m[(23, 4)] = 8; m[(23, 5)] = 14; m[(23, 6)] = 2; m[(23, 7)] = 16; m[(23, 8)] = 13; m[(23, 9)] = 4; m[(23, 10)] = 11; m[(23, 11)] = 20; m[(23, 12)] = 27; m[(23, 13)] = 5; m[(23, 14)] = 26; m[(23, 15)] = 24; m[(23, 16)] = 6; m[(23, 17)] = 15; m[(23, 18)] = 17; m[(23, 19)] = 1; m[(23, 20)] = 21; m[(23, 21)] = 19; m[(23, 22)] = 9; m[(23, 23)] = 23; m[(23, 24)] = 28; m[(23, 25)] = 0; m[(23, 26)] = 10; m[(23, 27)] = 3; m[(23, 28)] = 12; m[(24, 0)] = 23; m[(24, 1)] = 19; m[(24, 2)] = 26; m[(24, 3)] = 7; m[(24, 4)] = 15; m[(24, 5)] = 1; m[(24, 6)] = 13; m[(24, 7)] = 12; m[(24, 8)] = 3; m[(24, 9)] = 10; m[(24, 10)] = 14; m[(24, 11)] = 21; m[(24, 12)] = 4; m[(24, 13)] = 17; m[(24, 14)] = 22; m[(24, 15)] = 27; m[(24, 16)] = 25; m[(24, 17)] = 5; m[(24, 18)] = 16; m[(24, 19)] = 18; m[(24, 20)] = 0; m[(24, 21)] = 2; m[(24, 22)] = 20; m[(24, 23)] = 8; m[(24, 24)] = 24; m[(24, 25)] = 28; m[(24, 26)] = 6; m[(24, 27)] = 9; m[(24, 28)] = 11; m[(25, 0)] = 20; m[(25, 1)] = 27; m[(25, 2)] = 13; m[(25, 3)] = 16; m[(25, 4)] = 0; m[(25, 5)] = 12; m[(25, 6)] = 24; m[(25, 7)] = 2; m[(25, 8)] = 9; m[(25, 9)] = 15; m[(25, 10)] = 22; m[(25, 11)] = 3; m[(25, 12)] = 18; m[(25, 13)] = 11; m[(25, 14)] = 6; m[(25, 15)] = 23; m[(25, 16)] = 21; m[(25, 17)] = 26; m[(25, 18)] = 4; m[(25, 19)] = 17; m[(25, 20)] = 19; m[(25, 21)] = 8; m[(25, 22)] = 1; m[(25, 23)] = 14; m[(25, 24)] = 7; m[(25, 25)] = 25; m[(25, 26)] = 28; m[(25, 27)] = 5; m[(25, 28)] = 10; m[(26, 0)] = 21; m[(26, 1)] = 12; m[(26, 2)] = 17; m[(26, 3)] = 6; m[(26, 4)] = 11; m[(26, 5)] = 25; m[(26, 6)] = 14; m[(26, 7)] = 8; m[(26, 8)] = 16; m[(26, 9)] = 23; m[(26, 10)] = 2; m[(26, 11)] = 19; m[(26, 12)] = 10; m[(26, 13)] = 1; m[(26, 14)] = 20; m[(26, 15)] = 5; m[(26, 16)] = 24; m[(26, 17)] = 22; m[(26, 18)] = 27; m[(26, 19)] = 3; m[(26, 20)] = 18; m[(26, 21)] = 4; m[(26, 22)] = 7; m[(26, 23)] = 0; m[(26, 24)] = 15; m[(26, 25)] = 13; m[(26, 26)] = 26; m[(26, 27)] = 28; m[(26, 28)] = 9; m[(27, 0)] = 11; m[(27, 1)] = 18; m[(27, 2)] = 5; m[(27, 3)] = 10; m[(27, 4)] = 26; m[(27, 5)] = 15; m[(27, 6)] = 22; m[(27, 7)] = 17; m[(27, 8)] = 24; m[(27, 9)] = 1; m[(27, 10)] = 20; m[(27, 11)] = 9; m[(27, 12)] = 0; m[(27, 13)] = 7; m[(27, 14)] = 19; m[(27, 15)] = 14; m[(27, 16)] = 4; m[(27, 17)] = 25; m[(27, 18)] = 23; m[(27, 19)] = 21; m[(27, 20)] = 2; m[(27, 21)] = 28; m[(27, 22)] = 3; m[(27, 23)] = 13; m[(27, 24)] = 6; m[(27, 25)] = 16; m[(27, 26)] = 12; m[(27, 27)] = 27; m[(27, 28)] = 8; m[(28, 0)] = 22; m[(28, 1)] = 21; m[(28, 2)] = 27; m[(28, 3)] = 26; m[(28, 4)] = 25; m[(28, 5)] = 24; m[(28, 6)] = 23; m[(28, 7)] = 19; m[(28, 8)] = 18; m[(28, 9)] = 17; m[(28, 10)] = 16; m[(28, 11)] = 15; m[(28, 12)] = 14; m[(28, 13)] = 20; m[(28, 14)] = 10; m[(28, 15)] = 9; m[(28, 16)] = 8; m[(28, 17)] = 7; m[(28, 18)] = 13; m[(28, 19)] = 12; m[(28, 20)] = 11; m[(28, 21)] = 6; m[(28, 22)] = 5; m[(28, 23)] = 4; m[(28, 24)] = 3; m[(28, 25)] = 2; m[(28, 26)] = 1; m[(28, 27)] = 0; m[(28, 28)] = 28;
    for i in range(n):
        for j in range(n):
            c[(i, j)] = 0 if i == j else 1
    t = [(0, 0, 0, 0,), (1, 1, 1, 1,),]
    return n, name, m, c, t


MAGMA_DEFS = [magmadef_7_0, magmadef_9_0, magmadef_29_0]


def analyze_fiber(table_vals, K, label=""):
    """
    Analyze a K×K fiber operation table for structural regularity.
    table_vals[x][y] is the integer result in {0,...,K-1}.
    Returns a dict of properties and a summary string.
    """
    props = {}

    # Idempotent: F[x][x] == x for all x
    props["idempotent"] = all(table_vals[x][x] == x for x in range(K))

    # Commutative: F[x][y] == F[y][x]
    props["commutative"] = all(
        table_vals[x][y] == table_vals[y][x] for x in range(K) for y in range(K)
    )

    # Left projection: F[x][y] == x
    props["left_proj"] = all(table_vals[x][y] == x for x in range(K) for y in range(K))

    # Right projection: F[x][y] == y
    props["right_proj"] = all(table_vals[x][y] == y for x in range(K) for y in range(K))

    # Constant: all values equal some c
    flat = [table_vals[x][y] for x in range(K) for y in range(K)]
    props["constant"] = len(set(flat)) == 1
    if props["constant"]:
        props["constant_val"] = flat[0]

    # Affine: F[x][y] == (a*x + b*y + c) % K for some a,b,c in Z/KZ
    best_affine = None
    best_affine_mismatches = K*K + 1
    for a in range(K):
        for b in range(K):
            for c in range(K):
                mismatches = sum(
                    1 for x in range(K) for y in range(K)
                    if (a*x + b*y + c) % K != table_vals[x][y]
                )
                if mismatches < best_affine_mismatches:
                    best_affine_mismatches = mismatches
                    best_affine = (a, b, c)
    props["affine"] = (best_affine_mismatches == 0)
    props["best_affine"] = best_affine
    props["affine_mismatches"] = best_affine_mismatches

    # Near-affine: fraction of cells matching best affine
    props["affine_coverage"] = (K*K - best_affine_mismatches) / (K*K)

    # Latin square: each value appears exactly K times in each row and column
    rows_latin = all(len(set(table_vals[x])) == K for x in range(K))
    cols_latin = all(len(set(table_vals[x][y] for x in range(K))) == K for y in range(K))
    props["latin"] = rows_latin and cols_latin

    # Associative (quick check — only feasible for small K)
    if K <= 4:
        assoc = True
        for x in range(K):
            for y in range(K):
                for z in range(K):
                    if table_vals[table_vals[x][y]][z] != table_vals[x][table_vals[y][z]]:
                        assoc = False
                        break
                if not assoc:
                    break
            if not assoc:
                break
        props["associative"] = assoc
    else:
        props["associative"] = None  # not checked

    # Build summary
    tags = []
    if props["constant"]:
        tags.append(f"const={props.get('constant_val','?')}")
    elif props["left_proj"]:
        tags.append("left-proj")
    elif props["right_proj"]:
        tags.append("right-proj")
    elif props["affine"]:
        a, b, c = props["best_affine"]
        tags.append(f"affine({a}x+{b}y+{c})")
    else:
        a, b, c = props["best_affine"]
        cov = props["affine_coverage"]
        tags.append(f"near-affine({a}x+{b}y+{c},cov={cov:.2f})")

    if props["idempotent"]:
        tags.append("idem")
    if props["commutative"]:
        tags.append("comm")
    if props["latin"]:
        tags.append("latin")
    if props.get("associative"):
        tags.append("assoc")

    summary = f"F[{label}]: " + ", ".join(tags)
    return props, summary


def summarize_fiber_regularity(fiber_props_list, K, num_colors):
    """Print a summary of which structural patterns dominate across all colors."""
    n = num_colors
    affine_count = sum(1 for p in fiber_props_list if p.get("affine"))
    idem_count = sum(1 for p in fiber_props_list if p.get("idempotent"))
    comm_count = sum(1 for p in fiber_props_list if p.get("commutative"))
    latin_count = sum(1 for p in fiber_props_list if p.get("latin"))
    const_count = sum(1 for p in fiber_props_list if p.get("constant"))
    proj_count = sum(1 for p in fiber_props_list if p.get("left_proj") or p.get("right_proj"))
    avg_cov = sum(p.get("affine_coverage", 0) for p in fiber_props_list) / max(n, 1)

    print(f"  --- Fiber regularity summary ({n} colors, K={K}) ---")
    print(f"  Affine:    {affine_count}/{n}")
    print(f"  NearAff:   avg coverage {avg_cov:.3f}")
    print(f"  Idempotent:{idem_count}/{n}")
    print(f"  Commutative:{comm_count}/{n}")
    print(f"  Latin sq:  {latin_count}/{n}")
    print(f"  Constant:  {const_count}/{n}")
    print(f"  Projection:{proj_count}/{n}")
    if affine_count == n:
        print(f"  => ALL fibers are affine (fully affine extension)")
    elif avg_cov >= 0.9:
        print(f"  => Fibers near-affine (>=90% coverage)")
    elif idem_count == n:
        print(f"  => All fibers idempotent, non-affine")
    else:
        print(f"  => Mixed/irregular fiber structure")


def main_nonlinear(K, magmadef, anti255=False):
    """
    Search for E677-satisfying fiber extensions using full function tables.

    Each fiber operation f_i: Z/KZ × Z/KZ → Z/KZ is a K×K table of values,
    rather than being restricted to affine form.

    If anti255=True, additionally require that E255 fails for at least one element.
    """
    N, m_name, m_m, m_c, m_t = magmadef()
    num_colors = len(m_t)

    s = Solver()
    s.set("timeout", 300000)  # 5 minute timeout per K

    # Fiber operations: F[color][x][y] = result in Z/KZ
    F = [[[Int(f"F_{i}_{x}_{y}") for y in range(K)] for x in range(K)] for i in range(num_colors)]

    # Domain constraints: each F[i][x][y] in {0, ..., K-1}
    for i in range(num_colors):
        for x in range(K):
            for y in range(K):
                s.add(F[i][x][y] >= 0, F[i][x][y] < K)

    # E677 constraints:
    # For the product magma M × Z/KZ with operation:
    #   (a, r) ◇ (b, s) = (m[a][b], F[c[a][b]][r][s])
    # E677: x = y ◇ (x ◇ ((y ◇ x) ◇ y))
    # must hold for all (a,r), (b,s).

    # We encode this for all base elements a,b and all fiber values r,s.
    for a in range(N):
        for b in range(N):
            for r in range(K):
                for s2 in range(K):
                    # Compute y ◇ x = (b,s2) ◇ (a,r)
                    yx_base = m_m[(b, a)]
                    yx_color = m_c[(b, a)]
                    yx_fiber = F[yx_color][s2][r]

                    # Compute (y ◇ x) ◇ y
                    yxy_base = m_m[(yx_base, b)]
                    yxy_color = m_c[(yx_base, b)]
                    # yx_fiber is a Z3 expr, need to select from table
                    # yxy_fiber = F[yxy_color][yx_fiber][s2]
                    # This requires If-chains since yx_fiber is symbolic
                    yxy_fiber = F[yxy_color][0][s2]  # placeholder
                    for v in range(K):
                        yxy_fiber = If(yx_fiber == v, F[yxy_color][v][s2], yxy_fiber)

                    # Compute x ◇ ((y ◇ x) ◇ y)
                    xyxy_base = m_m[(a, yxy_base)]
                    xyxy_color = m_c[(a, yxy_base)]
                    xyxy_fiber = F[xyxy_color][0][0]
                    for v in range(K):
                        xyxy_fiber = If(yxy_fiber == v, F[xyxy_color][r][v], xyxy_fiber)

                    # Compute y ◇ (x ◇ ((y ◇ x) ◇ y))
                    final_base = m_m[(b, xyxy_base)]
                    final_color = m_c[(b, xyxy_base)]
                    final_fiber = F[final_color][0][0]
                    for v in range(K):
                        final_fiber = If(xyxy_fiber == v, F[final_color][s2][v], final_fiber)

                    # E677: result must equal x = (a, r)
                    s.add(final_base == a)  # base equation (should be guaranteed by base magma)
                    s.add(final_fiber == r)

    # Anti-E255 constraints (if requested):
    # E255: x = ((x ◇ x) ◇ x) ◇ x for all x
    # We require this to FAIL for at least one element.
    if anti255:
        anti_clauses = []
        for a in range(N):
            for r in range(K):
                # Compute x ◇ x = (a,r) ◇ (a,r)
                xx_base = m_m[(a, a)]
                xx_color = m_c[(a, a)]
                xx_fiber = F[xx_color][r][r]

                # Compute (x ◇ x) ◇ x
                xxx_base = m_m[(xx_base, a)]
                xxx_color = m_c[(xx_base, a)]
                xxx_fiber = F[xxx_color][0][r]
                for v in range(K):
                    xxx_fiber = If(xx_fiber == v, F[xxx_color][v][r], xxx_fiber)

                # Compute ((x ◇ x) ◇ x) ◇ x
                xxxx_base = m_m[(xxx_base, a)]
                xxxx_color = m_c[(xxx_base, a)]
                xxxx_fiber = F[xxxx_color][0][r]
                for v in range(K):
                    xxxx_fiber = If(xxx_fiber == v, F[xxxx_color][v][r], xxxx_fiber)

                # E255 fails for this element if result != x
                anti_clauses.append(Or(xxxx_base != a, xxxx_fiber != r))

        s.add(Or(*anti_clauses))

    print(f"  constraints added, solving...", flush=True)
    result = s.check()

    if result == sat:
        m = s.model()
        print(f"  SOLUTION FOUND! K={K}, base={m_name}")

        # Extract and print fiber tables; collect for analysis
        fiber_tables = []
        fiber_props_list = []
        for i in range(num_colors):
            table_vals = [
                [m.eval(F[i][x][y], model_completion=True).as_long() for y in range(K)]
                for x in range(K)
            ]
            fiber_tables.append(table_vals)
            props, summary = analyze_fiber(table_vals, K, label=str(i))
            fiber_props_list.append(props)
            print(f"  Fiber F[{i}]:  {summary}")
            for x in range(K):
                print(f"    {table_vals[x]}")

        # Build the full magma table from already-extracted fiber_tables
        total_n = N * K
        table = [[0]*total_n for _ in range(total_n)]
        for a in range(N):
            for b in range(N):
                ab_base = m_m[(a, b)]
                ab_color = m_c[(a, b)]
                for r in range(K):
                    for ss in range(K):
                        fval = fiber_tables[ab_color][r][ss]
                        table[a*K+r][b*K+ss] = ab_base*K + fval

        # Verify E677
        def f(xi, yi):
            return table[yi][xi]  # careful: table[row][col] = row ◇ col

        # Actually: table[a][b] = a ◇ b
        def op(xi, yi):
            return table[xi][yi]

        e677_ok = True
        for x in range(total_n):
            for y in range(total_n):
                yx = op(y, x)
                yxy = op(yx, y)
                xyxy = op(x, yxy)
                result = op(y, xyxy)
                if result != x:
                    e677_ok = False
                    print(f"  E677 FAIL: x={x}, y={y}")
                    break
            if not e677_ok:
                break

        e255_ok = True
        e255_fail_elems = []
        for x in range(total_n):
            xx = op(x, x)
            xxx = op(xx, x)
            xxxx = op(xxx, x)
            if xxxx != x:
                e255_ok = False
                e255_fail_elems.append(x)

        print(f"  E677: {'PASS' if e677_ok else 'FAIL'}")
        print(f"  E255: {'PASS' if e255_ok else 'FAIL'}")
        if e255_fail_elems:
            print(f"  E255 fails at elements: {e255_fail_elems}")
            print(f"  *** COUNTEREXAMPLE FOUND! ***")

        # Fiber regularity summary
        summarize_fiber_regularity(fiber_props_list, K, num_colors)

        # Print full table
        print(f"  Full magma table ({total_n}x{total_n}):")
        for i in range(total_n):
            print("  ", " ".join(str(table[i][j]) for j in range(total_n)))

        return True
    elif result == unsat:
        print(f"  UNSAT for K={K}", flush=True)
        return False
    else:
        print(f"  UNKNOWN/TIMEOUT for K={K}", flush=True)
        return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python color-extensions-nonlinear.py <mode> <magma_idx> [max_K]")
        print("  mode: '677' or 'anti255'")
        print("  magma_idx: 0=7/0, 1=9/0")
        sys.exit(1)

    mode = sys.argv[1]
    magma_idx = int(sys.argv[2])
    max_K = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    anti255 = (mode == "anti255")
    magma = MAGMA_DEFS[magma_idx]

    N, m_name, _, _, _ = magma()
    print(f"Mode: {mode}, Base: {m_name}, max_K: {max_K}", flush=True)

    for K in range(2, max_K + 1):
        print(f"K={K} (product size={N*K}):", flush=True)
        found = main_nonlinear(K, magma, anti255=anti255)
        if found and anti255:
            print("COUNTEREXAMPLE FOUND - STOPPING")
            break
