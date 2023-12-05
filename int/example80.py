dictionary = {}
def climbStairs(n):
    """
    :type n: int
    :rtype: int
    """
    number = 0
    if n == 0 or n == 1:
        return 1
    if n in dictionary:
        return dictionary[n]
    else:
        number += climbStairs(n - 1) + climbStairs(n - 2)
        dictionary[n] = number
    return number