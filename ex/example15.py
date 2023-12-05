def minDeletionSize(A: list[str]) -> int:        
    return sum([list(col) != sorted(col) for col in zip(*A)])
            
