#!/usr/bin/env python
# ############################################################################
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# ############################################################################
"""
replaceZenpackPath is an argument filter for zenpack commands running in a
serviced container.  It converts the zenpack path from a relative path (on
the host) to the corresponding absolute path in the container and writes the
new arguments to stdout, separated by semicolons.

e.g.,
  --install relative/path/to/zenpack.egg
becomes
  --install;/mnt/pwd/relative/path/to/zenpack.egg
"""

import sys
import os.path

# serviced mounts the cwd at this directory
CWD_MOUNT_POINT = '/mnt/pwd'

def replaceZenpackPath(argv):
    try:
        pathIndex = argv.index('--install') + 1
        path = argv[pathIndex]
    except (ValueError, IndexError):
        return argv

    newPath = os.path.join(CWD_MOUNT_POINT, path)
    if not os.path.exists(newPath):
        raise IOError(path)

    return [i if i != path else newPath for i in argv]


def main(argv):
    try:
        argv = replaceZenpackPath(sys.argv[1:])
        print ';'.join(argv),
        return 0
    except IOError as e:
        print >> sys.stderr, "Unable to open ZenPack file: '%s'" % e
        print >> sys.stderr, "For installation in container the ZenPack must " \
                             "be located in the current working directory and " \
                             "must be specified with a relative path."
    return 1


if __name__ == '__main__':
    status = main(sys.argv)
    exit(status)
