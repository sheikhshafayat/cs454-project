def average(salary: list[int]) -> float:
    salary.sort()
    del salary[0]
    del salary[-1]
    return sum(salary)/len(salary)