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

    load_config("signals.zcml", Products.Jobber)

    # All calls to celery need the 'app instance' for zenjobs.
    sys.argv[1:] = ["-A", "Products.Jobber.zenjobs"] + sys.argv[1:]

    sys.exit(main())
