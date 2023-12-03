
import example3
def test_sample():
	example3.intersect(0, 1, 0, 1, 0, 1, 1, 0)
	example3.intersect(0, 1, 0, 1, 0, 5, 1, 0)
	example3.intersect(0, 1, 0, 1, 0, 5, 1, -5)
	example3.intersect(0, 1, 0, 1, -5, 5, 1, -5)
	example3.intersect(0, 0, 0, 1, -5, 5, 1, -5)
	example3.intersect(0, 0, 0, 1, -5, 5, -3, -5)
	example3.intersect(0, 0, 0, -4, -5, 5, -3, -5)
	example3.intersect(0, 1, 0, -4, -5, 5, -3, -5)
	example3.intersect(0, 1, 1, 0, 0, 1, 1, 1)
	example3.intersect(0, 1, 1, 0, 0, 2, 1, 1)