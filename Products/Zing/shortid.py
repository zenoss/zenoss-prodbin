##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
