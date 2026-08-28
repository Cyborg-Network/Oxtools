from typing import List, Tuple

def jaccard_similarity(text1: str, text2: str) -> float:
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union) if union else 0.0


def check_variations(captions: List[str]) -> List[Tuple[int, int, float]]:
    similarities = []
    n = len(captions)

    for i in range(n):
        for j in range(i + 1, n):
            sim = jaccard_similarity(captions[i], captions[j])
            similarities.append((i, j, sim))

    return similarities