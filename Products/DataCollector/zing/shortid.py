import string
from uuid import uuid4

ALPHABET = string.ascii_letters + string.digits
ALPHABET_LEN = len(ALPHABET)

def shortid():
    output = ""
    number = uuid4().int
    while number:
        number, digit = divmod(number, ALPHABET_LEN)
        output += ALPHABET[digit]
    return output
