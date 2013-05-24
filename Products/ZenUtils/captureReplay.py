#! /usr/bin/env python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """captureReplay
    Common code to capture and replay packets.

    To use:
1. Add the captureReplay mixin to the list of base classes

2. Add the following to the buildOptions method of the base class, after other
   initialization:
    captureReplay.buildOptions()

3. Add the following to the __init__ of the base class, before any other
   option processing:
   self.processCaptureReplayOptions()

4. Define a convertPacketToPython() method to convert a 'raw' packet into a
   Python serializable object.

5. Add a call to the capturePacket() method to capture the packet.

6. Define a replay() method to replay the packet.
"""

import sys
import cPickle
from exceptions import EOFError, IOError
import glob

import Globals
from twisted.internet import defer, reactor
from Products.ZenUtils.Timeout import timeout
from Products.ZenEvents.ZenEventClasses import Error, Warning, Info, \
    Debug

from twisted.python import failure

class FakePacket(object):
    """
    A fake object to make packet replaying feasible.
    """
    def __init__(self):
        self.fake = True


class CaptureReplay(object):
    """
    Base class for packet capture and replay capability.
    Assumes that the other classes provide the following:
    self.buildOptions()
    self.sendEvent()

    Overrides the self.connected() method if called to replay packets.
    """

    def processCaptureReplayOptions(self):
        """
        Inside of the initializing class, call these functions first.
        """
        if self.options.captureFilePrefix and len(self.options.replayFilePrefix) > 0:
            self.log.error( "Can't specify both --captureFilePrefix and -replayFilePrefix" \
                 " at the same time.  Exiting" )
            sys.exit(1)

        if self.options.captureFilePrefix and not self.options.captureAll and \
            self.options.captureIps == '':
            self.log.warn( "Must specify either --captureIps or --captureAll for" + \
                 " --capturePrefix to take effect.  Ignoring option --capturePrefix" )

        if len(self.options.replayFilePrefix) > 0:
            self.connected = self.replayAll
            return

        self.captureSerialNum = 0
        self.captureIps = self.options.captureIps.split(',')

    def convertPacketToPython(*packetInfo):
        """
        Convert arguments into an plain object (no functions) suitable
        for pickling.
        """
        pass

    def capturePacket(self, hostname, *packetInfo):
        """
        Store the raw packet for later examination and troubleshooting.

        @param hostname: packet-sending host's name or IP address
        @type hostname: string
        @param packetInfo: raw packet and other necessary arguments
        @type packetInfo: args
        """
        # Save the raw data if requested to do so
        if not self.options.captureFilePrefix:
            return
        if not self.options.captureAll and hostname not in self.captureIps:
            self.log.debug( "Received packet from %s, but not in %s" % (hostname,
                            self.captureIps))
            return

        self.log.debug( "Capturing packet from %s" % hostname )
        name = "%s-%s-%d" % (self.options.captureFilePrefix, hostname, self.captureSerialNum)
        try:
            packet = self.convertPacketToPython(*packetInfo)
            capFile = open( name, "wb")
            data= cPickle.dumps(packet, cPickle.HIGHEST_PROTOCOL)
            capFile.write(data)
            capFile.close()
            self.captureSerialNum += 1
        except Exception:
            self.log.exception("Couldn't write capture data to '%s'" % name )

    def replayAll(self):
        """
        Replay all captured packets using the files specified in
        the --replayFilePrefix option and then exit.

        Note that this calls the Twisted stop() method
        """
        if hasattr(self, 'configure'):
            d = self.configure()
            d.addCallback(self._replayAll)
        else:
            self._replayAll()
    
    def _replayAll(self, ignored=None):
        # Note what you are about to see below is a direct result of optparse
        # adding in the arguments *TWICE* each time --replayFilePrefix is used.
        files = []
        for filespec in self.options.replayFilePrefix:
            files += glob.glob( filespec + '*' )

        self.loaded = 0
        self.replayed = 0
        for file in set(files):
            self.log.debug( "Attempting to read packet data from '%s'" % file )
            try:
                fp = open( file, "rb" )
                packet= cPickle.load(fp)
                fp.close()
                self.loaded += 1

            except (IOError, EOFError):
                fp.close()
                self.log.exception( "Unable to load packet data from %s" % file )
                continue

            self.log.debug("Calling application-specific replay() method")
            self.replay(packet)

        self.replayStop()

    def replay(self, packet):
        """
        Replay a captured packet.  This must be overridden.

        @param packet: raw packet
        @type packet: binary
        """
        pass
    
    def replayStop(self):
        """
        Twisted method that we use to override the default stop() method
        for when we are replaying packets.  This version waits to make
        sure that all of our deferreds have exited before pulling the plug.
        """
        if self.replayed == self.loaded:
            self.log.info("Loaded and replayed %d packets" % self.replayed)
            reactor.stop()
        else:
            reactor.callLater(1, self.replayStop)

    def buildCaptureReplayOptions(self, parser):
        """
        This should be called explicitly in the base class' buildOptions
        """
        parser.add_option('--captureFilePrefix',
                               dest='captureFilePrefix',
                               default=None,
                               help="Directory and filename to use as a template" + \
                               "  to store captured raw trap packets.")
        parser.add_option('--captureAll',
                               dest='captureAll',
                               action='store_true',
                               default=False,
                               help="Capture all packets.")
        parser.add_option('--captureIps',
                               dest='captureIps',
                               default='',
                               help="Comma-separated list of IP addresses to capture.")
        parser.add_option('--replayFilePrefix',
                               dest='replayFilePrefix',
                               action='append',
                               default=[],
             help="Filename prefix containing captured packet data. Can specify more than once.")
