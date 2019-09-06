from pprint import pprint
from collections import defaultdict, namedtuple

Rect = namedtuple('Rect', ['X0', 'Y0', 'X1', 'Y1'])


def dictToRect(r):
    return Rect(**d)


def rectToDict(r):
     return {k: r[i] for i, k in enumerate(Rect._fields)}

if False:
    print(Rect._fields)
    d = {'X0': 10, 'Y0': 11, 'X1': 20, 'Y1': 21 }
    r = Rect(**d)
    print(r)
    d2 = {k: r[i] for i, k in enumerate(Rect._fields)}
    print(d2)
    assert False


R = [
    (0, 0, 2, 2),  # + 4   4
    (1, 1, 3, 3),  # x 3   7
    (2, 1, 4, 3),  # o 2   9
    (1, 1, 4, 4),  # % 3  12
    (0, 0, 4, 3),  # $ 3  15
    (0, 0, 4, 4),  # & 1  16
]

# 3 & % % %
# 2 $ x x o
# 1 + + x o
# 0 + + $ $
#   0 1 2 3


def main():
    print("=" * 80)
    pprint(R)
    for i in range(len(R)):
        print("%d: " % i, end=' ')
        rects = reduceRects(R[:i+1])
        print("rects=%d area=%d" % (len(rects), areaList(rects)))


def areaList(R):
    total = 0
    for r in R:
        total += area(r)
    return total


def area(r):
    x1, y1, x2, y2 = r
    return (x2 - x1) * (y2 - y1)


def reduceRects(R):
    """reduceRects reduces the list of possibly overlapping rectangles in `R` to a reasonably
        compact list of non-overlapping rectangles
    """
    # Get a list of non-overlapping rectangles. There may be many of these.
    rects = toNonOverapping(R)

    # Try to merge as much as possible both vertically and horizontally.
    rects = mergeV(rects)
    rects = mergeH(rects)
    return rects


def mergeV(rects):
    rects = [r.copy() for r in rects]
    byX = defaultdict(list)
    for r in rects:
        x1 = r[0]
        byX[x1].append(r)
    X1 = sorted(byX)
    merged = []
    for x in X1:
        xrects = byX[x]
        r0 = xrects[0]
        for r in xrects[1:]:
            if adjV(r0, r):
                r00 = r0[:]
                r0[3] = r[3]  # r0.y2 = r.y2
            else:
                merged.append(r0)
                r0 = r
        merged.append(r0)
    return merged


def adjV(rA, rB):
    "Return True if B is below A and in same column"
    x1A, y1A, x2A, y2A = rA
    x1B, y1B, x2B, y2B = rB
    return x1A == x1B and x2A == x2B and y2A == y1B


def mergeH(rects):
    rects = [r.copy() for r in rects]
    byY = defaultdict(list)
    for r in rects:
        y1 = r[1]
        byY[y1].append(r)
    Y1 = sorted(byY)
    merged = []
    for y in Y1:
        # print("y=%d --" % y)
        yrects = byY[y]
        # yrects.sort()
        r0 = yrects[0]
        for r in yrects[1:]:
            if adjH(r0, r):
                r00 = r0[:]
                r0[2] = r[2]  # r0.x2 = r.x2
            else:
                merged.append(r0)
                r0 = r
        merged.append(r0)
    return merged


def adjH(rA, rB):
    "Return True if B is to the right of A and in same row"
    x1A, y1A, x2A, y2A = rA
    x1B, y1B, x2B, y2B = rB
    return y1A == y1B and y2A == y2B and x2A == x1B


def areaList(R):
    total = 0
    for r in R:
        total += area(r)
    return total

def area(r):
    x1, y1, x2, y2 = r
    return (x2 - x1) * (y2 - y1)




def toNonOverapping(R):
    """Splits a list of possibly overlapping rectangles into a list of non-overlapping recatangles
        Simple, slow O(N^3) brute-force method. Should be fast enough for N < 100.
        TODO: Optimize
    """
    X0, Y0, X1, Y1 = zip(*R)
    X = sorted(set(X0+X1))
    Y = sorted(set(Y0+Y1))

    # X and Y form a grid of all horizonal and vertical edges of the rectangles in R.  We return the
    # elements of that grid that are covered by R.
    return [[x0, y0, x1, y1]
        for x0, x1 in zip(X[:-1], X[1:])
             for y0, y1 in zip(Y[:-1], Y[1:])
             if inRects(R, x0, y0)]


def inRects(R, x, y):
    """inRects returns True if (x, y) is in any of the rectangles in R.
    """
    return any(x0 <= x < x1 and y0 <= y < y1 for x0, y0, x1, y1 in R)


if __name__ == '__main__':
    main()
