def convertToBase7(num):
    """
    :type num: int
    :rtype: str
    """
    if num < 0:
        return '-' + str(convertToBase7(-num))
    elif num < 7:
        return str(num)
    else:
        return str(convertToBase7(num//7)) + str(num % 7)