##############################################################################
#
# Copyright (C) Zenoss, Inc. 2025, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import collections
import json
import os
import re
import sys
import unicodedata
import urllib2

import six

import pathlib2 as pathlib


IANA_URL = "https://www.iana.org/assignments/enterprise-numbers.txt"
IANA_PREFIX = ".1.3.6.1.4.1"


class _EnterpriseOIDs(collections.Mapping):
    def __init__(self, *args, **kw):
        self.__oids = {}
        super(_EnterpriseOIDs, self).__init__(*args, **kw)

    def __getitem__(self, key):
        self.__load()
        return self.__oids[key]

    def __iter__(self):
        self.__load()
        return iter(self.__oids)

    def __len__(self):
        self.__load()
        return len(self.__oids)

    def __load(self):
        if self.__oids:
            return
        pathname = _get_pathname(pathlib.Path(os.environ.get("ZENHOME")))
        if not pathname.exists():
            return
        with open(pathname.as_posix(), "r") as f:
            self.__oids.update(json.load(f, object_pairs_hook=_as_bytes))


EnterpriseOIDs = _EnterpriseOIDs()


def build_enterprise_oids():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        dest="path",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="Path to directory to write the enterprise OID data file",
    )

    args = parser.parse_args()

    pathname = _get_pathname(args.path)
    if not pathname.parent.exists():
        print(
            "Directory not found: {}".format(pathname.parent), file=sys.stderr
        )
        sys.exit(1)

    # Attempt to download the latest enterprise assignments from IANA.
    try:
        instream = urllib2.urlopen(IANA_URL)
        iana_content = instream.read()
        instream.close()
    except IOError:
        print("Unable to retrieve OIDs from IANA.", file=sys.stderr)
        print("  - %s" % IANA_URL, file=sys.stderr)
        sys.exit(1)

    with open(pathname.as_posix(), "wb") as fo:
        oids = _get_oids(iana_content)
        json.dump(oids, fo, indent=4, separators=(",", ": "))

    print("IANA enterprise OID mappings written to file.")
    print("  %s" % pathname)


def _as_bytes(pairs):
    return {str(k): str(v) for k, v in pairs}


def _get_pathname(base):
    return base / "share" / "enterprise_oids.json"


def _get_oids(iana_source):
    oids = {}
    key_template = "{}.{{}}".format(IANA_PREFIX)

    iana_source_iter = iter(iana_source.splitlines())
    for line in iana_source_iter:
        if line.isdigit() and line != "0":
            key = line
            line = iana_source_iter.next().strip()
        else:
            continue

        # Convert unicode strings to ascii .. dropping unicode chars ...
        uline = six.text_type(line.decode("iso-8859-1", "ignore"))
        val = unicodedata.normalize("NFKD", uline).encode("ascii", "ignore")

        # Strip control characters.
        val = re.sub(r"[^\w!.,<>@#$%^&*\/():\"']", " ", val).strip()

        if not val or val in ("Unassigned", "Reserved", "none"):
            continue

        oids[key_template.format(key)] = val

    return oids
