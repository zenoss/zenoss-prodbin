##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


def main():
    import sys

    import Products.Jobber

    from celery.bin.celery import main
    from Products.ZenUtils.Utils import load_config
    from Products.ZenUtils.zenpackload import load_zenpacks

    # The Zenoss environment requires that the 'zenoss.zenpacks' entrypoints
    # be explicitely loaded because celery doesn't know to do that.
    # Not loading those entrypoints means that celery will be unaware of
    # any celery 'task' definitions in the ZenPacks.
    load_zenpacks()

    load_config("signals.zcml", Products.Jobber)

    # All calls to celery need the 'app instance' for zenjobs.
    sys.argv[1:] = ["-A", "Products.Jobber.zenjobs"] + sys.argv[1:]

    sys.exit(main())
