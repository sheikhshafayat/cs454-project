from collections import defaultdict
def uniqueOccurrences(self, arr: list[int]) -> bool:
    occurences = defaultdict(int)
    for i in arr:
        occurences[i] += 1
    for i in occurences.values():
        if list(occurences.values()).count(i) > 1:
            return False
    return True