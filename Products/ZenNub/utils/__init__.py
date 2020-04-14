def remove_prefix(s, prefix):
    if s.startswith(prefix):
        return s[len(prefix):]
    return s

def replace_prefix(s, prefix, replace):
    if s.startswith(prefix):
        return s.replace(prefix, replace, 1)
    return s

def parent_dcs(path):
    # return a list of parent paths, lowest to highest level, for a given
    # device/class path.
    for l in reversed(range(2, path.count('/') + 1)):
        yield '/'.join(path.split('/')[0:l])
    if path.count('/') > 1:
        yield '/'

def all_parent_dcs(path):
    # return a list of the supplied path plus its parents.
    yield path
    for parent in parent_dcs(path):
        yield parent
