def defangIPaddr(address: str) -> str:
    return address.replace('.', '[.]')
