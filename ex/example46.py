def peakIndexInMountainArray(self, arr: list[int]) -> int:
    l,r = 0,len(arr)-1
    while l<=r:
        m = (l+r)//2
        if (arr[m]>=arr[m-1])and (arr[m]>=arr[m+1]):
            return m
        else:
            if arr[m-1]>arr[m]:
                r = m-1
            else:
                l = m+1
