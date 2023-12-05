def busyStudent(startTime: list[int], endTime: list[int], queryTime: int) -> int: 
    res=0
    for start,end in zip(startTime,endTime):
        if(queryTime>=start and queryTime<=end):
            res+=1
    return res