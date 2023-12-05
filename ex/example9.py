def checkIfExist(arr: list[int]) -> bool:
    found = {}
    for num in arr:
        if num * 2 in found:
            return True
        if num % 2 == 0 and num / 2 in found:
            return True
        found[num] = True
    return False