def arrayPairSum(nums):
    """
    :type nums: List[int]
    :rtype: int
    """
    nums.sort()
    return sum(nums[::2])