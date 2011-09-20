######################################################################
#
# Copyright 2011 Zenoss, Inc.  All Rights Reserved.
#
# Copyright 2001-2010 by Vinay Sajip. All Rights Reserved.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose and without fee is hereby granted,
# provided that the above copyright notice appear in all copies and that
# both that copyright notice and this permission notice appear in
# supporting documentation, and that the name of Vinay Sajip
# not be used in advertising or publicity pertaining to distribution
# of the software without specific, written prior permission.
# VINAY SAJIP DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING
# ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL
# VINAY SAJIP BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR
# ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER
# IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
######################################################################

"""Creates new loggers from a python logging configuration file."""

import logging
import logging.config

def addLogsFromConfigFile(fname, configDefaults=None):
    """Add new loggers, handlers, and fomatters from a file.

    The file should be in the standard Python log config format described here:
    http://docs.python.org/library/logging.config.html#configuration-file-format

    This code was copied from the Python 2.7 logging.config.fileConfig()
    method, then altered to not require root or wipe existing loggers.
    Unfortunately the standard option "disable_existing_loggers=False" would
    still wipe out their settings and replace root, undoing Zope's log config.
    """
    import ConfigParser

    cp = ConfigParser.ConfigParser(configDefaults)
    if hasattr(fname, 'readline'):
        cp.readfp(fname)
    else:
        cp.read(fname)

    formatters = logging.config._create_formatters(cp)

    # critical section
    logging._acquireLock()
    try:
        logging._handlers.clear()
        del logging._handlerList[:]
        # Handlers add themselves to logging._handlers
        handlers = logging.config._install_handlers(cp, formatters)
        _zen_install_loggers(cp, handlers)
    finally:
        logging._releaseLock()


def _zen_install_loggers(cp, handlers):
    """Create and install loggers, without wiping existing ones."""

    llist = cp.get("loggers", "keys")
    llist = [log.strip() for log in llist.split(",")]
    if 'root' in llist:
        raise Exception('Zenoss logger config files should not have a root logger.')

    #now set up the new ones...
    existing_logger_names = logging.root.manager.loggerDict.keys()
    for log in llist:
        sectname = "logger_%s" % log
        qn = cp.get(sectname, "qualname")
        opts = cp.options(sectname)
        if "propagate" in opts:
            propagate = cp.getint(sectname, "propagate")
        else:
            propagate = 1
        if qn in existing_logger_names:
            raise Exception("Logger already exists: %s" % qn)
        logger = logging.getLogger(qn)
        if "level" in opts:
            level = cp.get(sectname, "level")
            logger.setLevel(logging._levelNames[level])
        for h in logger.handlers[:]:
            logger.removeHandler(h)
        logger.propagate = propagate
        logger.disabled = 0
        hlist = cp.get(sectname, "handlers")
        if len(hlist):
            hlist = hlist.split(",")
            hlist = logging.config._strip_spaces(hlist)
            for hand in hlist:
                logger.addHandler(handlers[hand])
