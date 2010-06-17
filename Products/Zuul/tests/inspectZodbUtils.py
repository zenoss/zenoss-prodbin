    #
# Utility methods to help inspect a ZODB
#
# Laurence Rowe 21/04/2005
#
# See also $SOFTWARE_HOME/bin/analyze.py
# and http://mail.zope.org/pipermail/zodb-dev/2001-August/001309.html
#
# First open the storage (read-only!) and iterate to the transaction you are
# interested in. recs = list(txn). find the size of each rec by len(rec.data)
# target is rec.oid of the rec you are interested in.
#
# In a zope debug console you can get the object with app._p_jar[rec.oid]
# For some objects (like BTrees.IOBTree.IOBucket) this is pretty useless.
# They represent themselves as their C data structure. Better find their path.
#
# Build a refmap - graph of object references
# (not too slow if the data.fs fits in memory).
# use doSearch to get a reference path (beginnings of other paths are returned
# as additionals). With the list of oids you can reconstruct the path by using
# app._p_jar[oid]. When you reach a python object something useful is shown!
#


from ZODB.serialize import referencesf
def buildRefmap(fs):
    '''build a refmap from a filestorage. look in every record of every
       transaction. build a dict of oid -> list(referenced oids)
    '''
    refmap = {}
    fsi = fs.iterator()

    for txn in fsi:
        for rec in txn:
            pickle, revid = fs.load(rec.oid, rec.version)
            refs = referencesf(pickle)
            refmap[rec.oid] = refs
    
    return refmap

def backrefs(target, refmap):
    '''Return a list of oids in the refmap who reference target
    '''
    oidlist = []
    for oid, refs in refmap.iteritems():
        if target in refs:
            oidlist.append(oid)
    return oidlist

def doSearch(target, refmap):
    '''for a target oid find the path of objects that refer to it.
       break if we reach no more references or find a cycle
    '''
    path = [target]
    additionals = []
    
    while True:
        target = path[-1:].pop()
        brefs = backrefs(target, refmap)
        if not brefs:    
            break
        
        bref = brefs[0]
        if bref in path:
            break
        
        if len(brefs) == 1:
            path.append(bref)
            continue
        
        additionals.append( (target, brefs[1:]) )
        path.append(bref)

    return (path, additionals)


##########################################
# Ian wrote the stuff below this
##########################################

def oids2path(db, app, oids):
    if not isinstance(oids, (list, tuple)):
        oids = (oids,)
    refmap = buildRefmap(db.storage)
    paths = []
    for oid in oids:
        path, additionals = doSearch(oid, refmap)
        s = []
        child = None
        for i, ob in enumerate(path):
            if child is None:
                child = app._p_jar[ob]
            try:
                parent = app._p_jar[path[i+1]]
                for k,v in parent.__dict__.iteritems():
                    if v==child:
                        s.append(k)
                        break
                else:
                    s.append(repr(child))
                child = parent
            except IndexError:
                break
        s.append('app')
        s.reverse()
        paths.append('.'.join(s))
    return paths


