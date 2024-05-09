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

    # Dynamic configuration shenanigans because Celery can't be re-configured
    # after its initial configuration has been set.
    _configure_celery()

    load_config("signals.zcml", Products.Jobber)

    # All calls to celery need the 'app instance' for zenjobs.
    sys.argv[1:] = ["-A", "Products.Jobber.zenjobs"] + sys.argv[1:]

    sys.exit(main())


def _configure_celery():
    import argparse
    import sys
    from Products.Jobber import config

    parser = argparse.ArgumentParser()
    parser.add_argument("--config-file")

    args, remainder = parser.parse_known_args()
    if not args.config_file:
        return

    cfg = config.getConfig(args.config_file)
    config.ZenCeleryConfig = config.CeleryConfig.from_config(cfg)
    sys.argv[1:] = remainder
