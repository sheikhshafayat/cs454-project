def minStartValue(nums: list[int]) -> int:
    res = 1
    for ind,n in enumerate(nums):
        temp = 1-sum(nums[:ind+1])
        if(temp > res):
            res = temp
    return res