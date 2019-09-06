from pprint import pprint
from collections import defaultdict, namedtuple

Rect = namedtuple('Rect', ['X0', 'Y0', 'X1', 'Y1'])


def dictToRect(d):
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


def reduceRectDicts(rectList):
    if not rectList:
        return rectList
    assert rectList
    R = [dictToRect(d) for d in rectList]
    assert R

    reducedR = reduceRects(R)

    numBefore = len(R)
    areaBefore = areaList(R)
    numAfter = len(reducedR)
    areaAfter = areaList(reducedR)
    print("&& rects %d -> %d | area %d -> %d %.1f%%" % (
        numBefore, numAfter, areaBefore, areaAfter, 100.0 * areaAfter / areaBefore))
    for i, r in enumerate(sorted(R)):
        print("%3d: %s %d %.1f%%" % (i, r, area(r), 100.0 * area(r) / areaBefore))
    print("-" * 80)
    for i, r in enumerate(sorted(reducedR)):
        print("%3d: %s %d %.1f%%" % (i, r, area(r), 100.0 * area(r) / areaAfter))
    print("-" * 80)

    return [rectToDict(r) for r in reducedR]


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
    byX = defaultdict(list)
    for r in rects:
        byX[r.X0].append(r)
    X = sorted(byX)
    merged = []
    for x in X:
        xrects = byX[x]
        r0 = xrects[0]
        for r in xrects[1:]:
            # if r is below r0 and in same column then merge
            if r0.X0 == r.X0 and r0.X1 == r.X1 and r0.Y1 == r.Y0:
                r0 = Rect(r0.X0, r0.Y0, r0.X1, r.Y1)
            else:
                merged.append(r0)
                r0 = r
        merged.append(r0)
    return merged


def mergeH(rects):
    byY = defaultdict(list)
    for r in rects:
        y1 = r[1]
        byY[r.Y0].append(r)
    Y = sorted(byY)
    merged = []
    for y in Y:
        yrects = byY[y]
        r0 = yrects[0]
        for r in yrects[1:]:
            # If r is to the right of r0 and in same row then merge
            if r0.Y0 == r.Y0 and r0.Y1 == r.Y1 and r0.X1 == r.X0:
                r0 = Rect(r0.X0, r0.Y0, r.X1, r0.Y1)
            else:
                merged.append(r0)
                r0 = r
        merged.append(r0)
    return merged



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
    return [Rect(x0, y0, x1, y1)
        for x0, x1 in zip(X[:-1], X[1:])
             for y0, y1 in zip(Y[:-1], Y[1:])
             if inRects(R, x0, y0)]


def inRects(R, x, y):
    """inRects returns True if (x, y) is in any of the rectangles in R.
    """
    return any(x0 <= x < x1 and y0 <= y < y1 for x0, y0, x1, y1 in R)


R = [
    (0, 0, 2, 2),  # + 4   4
    (1, 1, 3, 3),  # x 3   7
    (2, 1, 4, 3),  # o 2   9
    (1, 1, 4, 4),  # % 3  12
    (0, 0, 4, 3),  # $ 3  15
    (0, 0, 4, 4),  # & 1  16
]

R = [Rect(x0, x1, y0, y1) for x0, x1, y0, y1 in R]

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
    return sum(area(r) for r in R)


def area(r):
    return (r.X1 - r.X0) * (r.Y1 - r.Y0)


if __name__ == '__main__':
    main()
