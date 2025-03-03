##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import urllib2
import json
import jwt

def getJWKS(jwks_url):
    try:
        resp = urllib2.urlopen(url=jwks_url, timeout=10).read()
        return json.loads(resp)
    except Exception as e:
        # we probably want to handle an error here somehow
        return None

def publicKeysFromJWKS(jwks):
    public_keys = {}
    for key in jwks['keys']:
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
        public_keys[key['kid']] = public_key
    return public_keys

def getBearerToken(request):
    auth = request._auth
    if auth is None or len(auth) < 9 or auth[:7].lower() != 'bearer ':
        return None
    return auth.split()[-1]
