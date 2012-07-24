##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''Callhome mechanism. Reports anonymous statistics back to Zenoss, Inc.
'''

import base64
import cPickle
import logging
import os
import random
import string
import time
import zlib

import transaction
from persistent.dict import PersistentDict
from zope.component import getUtilitiesFor

from Globals import Persistent
from Products.ZenCallHome.transport.crypt import encrypt, decrypt
from Products.ZenCallHome.transport.interfaces import IReturnPayloadProcessor
from Products.ZenUtils.Version import Version
from Products.Zuul import getFacade
from zenoss.protocols.services.zep import ZepConnectionError

CHECKIN_WAIT = 60*60*24 # number of seconds between successful checkins
CHECKIN_ATTEMPT_WAIT = 60*60*2 # number of seconds between checkin attempts (per method)

logger = logging.getLogger('zen.callhome')

def is_callhome_disabled(dmd):
    return not getattr(dmd, 'versionCheckOptIn', True)

class CallHome(object):
    def __init__(self, dmd):
        self.dmd = dmd
        try:
            self.callHome = dmd.callHome
        except AttributeError:
            dmd.callHome = CallHomeData()
            self.callHome = dmd.callHome
            
    def attempt(self, method):
        '''
        Decide whether or not to attempt a callhome. This is computed from the time
        elapsed from last successful callhome, or time elapsed from the last attempt
        via the method passed in with the 'method' param.
        '''        
        if is_callhome_disabled(self.dmd) and not self.callHome.requestCallhome:
            return False
        
        now = long(time.time())
        
        # If we have waited long enough between checkings or attempts (or one
        # has been requested), and we have metrics to send and are not currently
        # updating them, then attempt a callhome
        if (now - self.callHome.lastAttempt[method] > CHECKIN_ATTEMPT_WAIT and \
            now - self.callHome.lastSuccess > CHECKIN_WAIT) or \
            self.callHome.requestCallhome:
            if self.callHome.metrics and not self.callHome.requestMetricsGather:
                self.callHome.lastAttempt[method] = now
                self.callHome.requestCallhome = False
                return True
        return False
    
    def get_payload(self):
        '''
        Retrieve the current callhome payload to send.
        '''
        payload = {}
        
        # product info
        payload['product'] = self.dmd.getProductName()
        payload['uuid'] = self.dmd.uuid or "NOT ACTIVATED"
        payload['symkey'] = self.callHome.symmetricKey
        payload['metrics'] = self.callHome.metrics
        
        return encrypt(cPickle.dumps(payload), self.callHome.publicKey)
    
    def save_return_payload(self, returnPayload):
        '''
        Process and save the data returned from the callhome server. This always
        includes versioning and crypto key changes, and may include other data
        to be processed by plugins to the IReturnPayloadProcessor interface.
        '''
        try:
            returnPayload = zlib.decompress(base64.urlsafe_b64decode(returnPayload))
            returnPayload = cPickle.loads(returnPayload)
        except:
            logger.debug('Error decoding return payload from server')
            return
        
        if all(x in returnPayload for x in ('currentPublicKey', 'revocationList')):
            # TODO: VERIFY revocation list, and apply
            newPubkey = returnPayload.get('currentPublicKey')
            if self.callHome.publicKey != newPubkey:
                self.callHome.publicKey = newPubkey
        
        if 'encrypted' in returnPayload:
            data = cPickle.loads(decrypt(returnPayload.get('encrypted'),
                                         self.callHome.symmetricKey))
            
            if 'latestVersion' in data:
                # Save the latest version, and send a message if new version available
                self.dmd.lastVersionCheck = long(time.time())
                available = Version.parse('Zenoss ' + data['latestVersion'])
                if getattr(self.dmd, 'availableVersion', '') != available.short():
                    self.dmd.availableVersion = available.short()
                    if self.dmd.About.getZenossVersion() < available:
                        try:
                            import socket
                            zep = getFacade('zep')
                            summary = 'A new version of Zenoss (%s) has been released' % \
                                      available.short()
                            zep.create(summary, 'Info', socket.getfqdn())
                        except ZepConnectionError:
                            logger.warning("ZEP not running - can't send new version event")
            
            # Go through other data in the return payload, and process
            for name, utility in getUtilitiesFor(IReturnPayloadProcessor):
                if name in data:
                    utility.process(self.dmd, data[name])
        
        self.callHome.lastSuccess = long(time.time())
        return


class CallHomeData(Persistent):
    def __init__(self):
        self.lastSuccess = 0
        self.requestCallhome = False
        
        self.lastAttempt = PersistentDict()
        self.lastAttempt['browserjs'] = 0
        self.lastAttempt['directpost'] = 0
        
        self.publicKey = 'EC7EFA98'
        self.symmetricKey = ''.join(random.choice(string.ascii_letters +
                                                  string.digits) for x in range(64))
        
        self.metrics = None
        self.lastMetricsGather = 0
        self.requestMetricsGather = False
