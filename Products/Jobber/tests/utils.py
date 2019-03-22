##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import contextlib
import sys
import traceback


@contextlib.contextmanager
def subTest(**params):
    try:
        yield
    except Exception:
        _, _, tb = sys.exc_info()
        # formatted_tb = ''.join(
        #     traceback.format_list(traceback.extract_tb(tb)[1:]),
        # )
        _, _, fn, _ = traceback.extract_tb(tb, 2)[1]
        print(
            "\n{}\nFAIL: {} ({})\n{}".format(
                "=" * 80, fn,
                ", ".join("{}={}".format(k, v) for k, v in params.items()),
                "-" * 80,
            ), end='',
        )
        raise
