import sys

x = open(sys.argv[1])
y = open(sys.argv[2])

inX = x.readlines()
inY = y.readlines()

interX = {}
interY = {}

for item in inX:
	interX[item] = 1
for item in inY:
	if interX.has_key(item):
		del interX[item]

for item in inY:
	interY[item] = 1
for item in inX:
	if interY.has_key(item):
		del interY[item]

print "Items in %s not in %s" % (sys.argv[1],sys.argv[2])
for item in interX.keys():
	print item[:-1]

print "Items in %s not in %s" % (sys.argv[2],sys.argv[1])
for item in interY.keys():
	print item[:-1]
