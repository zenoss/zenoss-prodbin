#!/usr/bin/python2.1

import Sybase
import string
import pprint
import sys

proc, server, username, password = sys.argv

db = Sybase.connect(server, username, password)

c = db.cursor()

c.execute("select count(*) from status where Class=100;")

row=c.fetchone()
print row[0]


