# utils/setlist_order.py

from typing import List, Dict

def camelot_distance(key1: str, key2: str) -> int:
    """
    Compute a simple “harmonic distance” on the Camelot wheel:
      - 0 if identical
      - 1 if same number different letter OR adjacent number same letter (with wrap 12⇄1)
      - 2 otherwise
    """
    if not key1 or not key2 or key1 == key2:
        return 0 if key1 == key2 else 2

    try:
        num1, let1 = int(key1[:-1]), key1[-1]
        num2, let2 = int(key2[:-1]), key2[-1]
    except ValueError:
        return 2

    # same number, different letter
    if num1 == num2 and let1 != let2:
        return 1

    # adjacent number, same letter
    if let1 == let2:
        if abs(num1 - num2) == 1 or {num1, num2} == {1, 12}:
            return 1

    return 2


def hybrid_order(tracks: List[Dict]) -> List[Dict]:
    """
    Greedy hybrid ordering:
     1. Sort by energy (BPM ascending).
     2. Within that, at each step pick the next track
        that minimizes harmonic distance from the current key.
    """
    # 1) sort by BPM
    pool = sorted(tracks, key=lambda t: t.get("bpm") or 0)
    sequence: List[Dict] = []

    if not pool:
        return sequence

    # 2) start with lowest-BPM track
    current = pool.pop(0)
    sequence.append(current)

    # 3) greedily pick the next best harmonic fit among remaining
    while pool:
        candidates = [t for t in pool if (t.get("bpm") or 0) >= (current.get("bpm") or 0)]
        if not candidates:
            candidates = pool

        best = min(
            candidates,
            key=lambda t: camelot_distance(current.get("key", ""), t.get("key", ""))
        )
        sequence.append(best)
        pool.remove(best)
        current = best

    return sequence
