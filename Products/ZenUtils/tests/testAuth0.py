##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


"""Tests for Products.ZenUtils.Auth0 module."""
import base64
import copy
import json
import jwt
from jwt.algorithms import RSAAlgorithm
import time
import mock

import unittest
from Products.ZenUtils.Auth0 import Auth0
import logging
log = logging.getLogger("ZenUtils.tests.Auth0")
log.setLevel(logging.DEBUG)

test_conf ={
    'audience': 'https://dev.zing.ninja',
    'tenantkey': 'https://dev.zing.ninja/tenant',
    'whitelist': ['test'],
    'tenant': 'https://zenoss-cloud-preview.auth0.com/',
    'emailkey': 'https://dev.zing.ninja/email'
}


with mock.patch('Products.ZenUtils.Auth0.getAuth0Conf', return_value=test_conf) as mock_getAuth0Conf:
    conf = mock_getAuth0Conf()

now = int(time.time())
kid = "bilbo.baggins@hobbiton.example"
jwt_claims = {
     u'aud': [conf["audience"], conf["tenant"] + 'userinfo'],
     u'azp': u'V0gfsQCv6xT6jWKFEwv2ZVfGXz2YDDr6',
     u'exp': now + + 24*60*60,
     u'https://dev.zing.ninja/connection': u'zenoss-com',
     u'https://dev.zing.ninja/email': u'testuser@zenoss.com',
     u'https://dev.zing.ninja/restrictionfilters': base64.b64encode('{"filters":[]}'),
     u'https://dev.zing.ninja/tenant': u'test',
     u'https://zenoss.com/groups': [u'Group 1', u'Group 2'],
     u'https://zenoss.com/roles': [u'CZ0:ZenManager', u'ZC:Manager'],
     u'iat': now,
     u'iss': conf["tenant"],
     u'scope': u'openid profile offline_access',
     u'sub': u'google-apps|testuser@zenoss.com'
}
jwt_headers = {
     "kid": kid
}

jwk_private_key = {
     "kty": "RSA",
     "kid": kid,
     "use": "sig",
     "n": "n4EPtAOCc9AlkeQHPzHStgAbgs7bTZLwUBZdR8_KuKPEHLd4rHVTeT-O-XV2jRojdNhxJWTDvNd7nqQ0VEiZQHz_AJmSCpMaJMRBSFKrKb2wqVwGU_NsYOYL-QtiWN2lbzcEe6XC0dApr5ydQLrHqkHHig3RBordaZ6Aj-oBHqFEHYpPe7Tpe-OfVfHd1E6cS6M1FZcD1NNLYD5lFHpPI9bTwJlsde3uhGqC0ZCuEHg8lhzwOHrtIQbS0FVbb9k3-tVTU4fg_3L_vniUFAKwuCLqKnS2BYwdq_mzSnbLY7h_qixoR7jig3__kRhuaxwUkRz5iaiQkqgc5gHdrNP5zw",
     "e": "AQAB",
     "d": "bWUC9B-EFRIo8kpGfh0ZuyGPvMNKvYWNtB_ikiH9k20eT-O1q_I78eiZkpXxXQ0UTEs2LsNRS-8uJbvQ-A1irkwMSMkK1J3XTGgdrhCku9gRldY7sNA_AKZGh-Q661_42rINLRCe8W-nZ34ui_qOfkLnK9QWDDqpaIsA-bMwWWSDFu2MUBYwkHTMEzLYGqOe04noqeq1hExBTHBOBdkMXiuFhUq1BU6l-DqEiWxqg82sXt2h-LMnT3046AOYJoRioz75tSUQfGCshWTBnP5uDjd18kKhyv07lhfSJdrPdM5Plyl21hsFf4L_mHCuoFau7gdsPfHPxxjVOcOpBrQzwQ",
     "p": "3Slxg_DwTXJcb6095RoXygQCAZ5RnAvZlno1yhHtnUex_fp7AZ_9nRaO7HX_-SFfGQeutao2TDjDAWU4Vupk8rw9JR0AzZ0N2fvuIAmr_WCsmGpeNqQnev1T7IyEsnh8UMt-n5CafhkikzhEsrmndH6LxOrvRJlsPp6Zv8bUq0k",
     "q": "uKE2dh-cTf6ERF4k4e_jy78GfPYUIaUyoSSJuBzp3Cubk3OCqs6grT8bR_cu0Dm1MZwWmtdqDyI95HrUeq3MP15vMMON8lHTeZu2lmKvwqW7anV5UzhM1iZ7z4yMkuUwFWoBvyY898EXvRD-hdqRxHlSqAZ192zB3pVFJ0s7pFc",
     "dp": "B8PVvXkvJrj2L-GYQ7v3y9r6Kw5g9SahXBwsWUzp19TVlgI-YV85q1NIb1rxQtD-IsXXR3-TanevuRPRt5OBOdiMGQp8pbt26gljYfKU_E9xn-RULHz0-ed9E9gXLKD4VGngpz-PfQ_q29pk5xWHoJp009Qf1HvChixRX59ehik",
     "dq": "CLDmDGduhylc9o7r84rEUVn7pzQ6PF83Y-iBZx5NT-TpnOZKF1pErAMVeKzFEl41DlHHqqBLSM0W1sOFbwTxYWZDm6sI6og5iTbwQGIC3gnJKbi_7k_vJgGHwHxgPaX2PnvP-zyEkDERuf-ry4c_Z11Cq9AqC2yeL6kdKT1cYF8",
     "qi": "3PiqvXQN0zwMeE-sBvZgi289XP9XCQF3VWqPzMKnIgQp7_Tugo6-NZBKCQsMf3HaEGBjTVJs_jcK8-TRXvaKe-7ZMaQj8VfBdYkssbu0NKDDhjJ-GtiseaDVWt7dcH0cfwxgFUHpQh7FoCrjFJ6h6ZEpMF6xmujs4qMpPz8aaI4"
}
jwk_public_key = {
     "kty": "RSA",
     "kid": kid,
     "use": "sig",
     "n": "n4EPtAOCc9AlkeQHPzHStgAbgs7bTZLwUBZdR8_KuKPEHLd4rHVTeT-O-XV2jRojdNhxJWTDvNd7nqQ0VEiZQHz_AJmSCpMaJMRBSFKrKb2wqVwGU_NsYOYL-QtiWN2lbzcEe6XC0dApr5ydQLrHqkHHig3RBordaZ6Aj-oBHqFEHYpPe7Tpe-OfVfHd1E6cS6M1FZcD1NNLYD5lFHpPI9bTwJlsde3uhGqC0ZCuEHg8lhzwOHrtIQbS0FVbb9k3-tVTU4fg_3L_vniUFAKwuCLqKnS2BYwdq_mzSnbLY7h_qixoR7jig3__kRhuaxwUkRz5iaiQkqgc5gHdrNP5zw",
     "e": "AQAB"
}


jwk_private_key_rsa = RSAAlgorithm.from_jwk(json.dumps(jwk_private_key))
jwk_public_key_rsa = RSAAlgorithm.from_jwk(json.dumps(jwk_public_key))


class MockRequest:
    def __init__(self):
        self.SESSION = {}
        self.cookies = {}
        self.PATH_INFO = "https://test.zenoss.io/cz0/zport/dmd/itinfrastructure"
        self.QUERY_STRING = None
        self.attrs = {}
        self.response = MockResponse()

    def __getitem__(self, key):
        return self.attrs[key]

    def __setitem__(self, key, value):
        self.attrs[key] = value


class MockResponse:
    def __init__(self):
        self.redirect_url = None
        self.status = None

    def redirect(self, url, lock=1):
        self.redirect_url = url

    def setStatus(self, status_code):
        self.status = status_code


class TestAuth0(unittest.TestCase):

    def setUp(self):
        self.request = MockRequest()
        self.response = MockResponse()
        self.auth0 = Auth0("test", "test")
        self.auth0.cache["keys"] = {kid: jwk_public_key_rsa}
        self.accessToken = jwt.encode(jwt_claims, jwk_private_key_rsa, headers=jwt_headers, algorithm="RS256")

    def test_storeToken(self):
        sessionInfo = self.auth0.storeToken(self.accessToken, self.request, conf)

        self.assertEqual(sessionInfo.userid, jwt_claims[u'https://dev.zing.ninja/email'])
        self.assertEqual(sessionInfo.roles, self.auth0.getRoleAssignments(jwt_claims[u'https://zenoss.com/roles']))

    @mock.patch('Products.ZenUtils.Auth0.getAuth0Conf', return_value=test_conf)
    def  test_challenge(self, mock_getGlobalConfiguration):
        # User with no valid access token must be redirected back to auth0 to obtain one.
        self.request.attrs = {"RESPONSE": self.response}
        result = self.auth0.challenge(self.request, self.response)
        self.assertTrue(result)
        self.assertEqual(self.response.redirect_url, "/czlogin.html?redirect=aHR0cHM6Ly90ZXN0Lnplbm9zcy5pby9jejAvenBvcnQvZG1kL2l0aW5mcmFzdHJ1Y3R1cmU=")

        # User with no CZ role must be redirected to the Zenoss Cloud UI
        no_role_jwt_claims = copy.deepcopy(jwt_claims)
        no_role_jwt_claims[u'https://zenoss.com/roles'] = []
        accessToken_no_role = jwt.encode(no_role_jwt_claims, jwk_private_key_rsa, headers=jwt_headers, algorithm="RS256")
        self.request.cookies = {"accessToken": accessToken_no_role}
        result = self.auth0.challenge(self.request, self.response)
        self.assertTrue(result)
        self.assertEqual(self.response.redirect_url, "/#/?errcode=1")

        # User has a valid access token, and has access to this CZ,
        # but apparently didn't have access to this specific
        # resource must see Unauthorized error handled by Zope
        self.request = MockRequest()
        self.request.attrs = {"RESPONSE": self.response}

        self.request.cookies = {"accessToken": self.accessToken}
        result = self.auth0.challenge(self.request, self.response)
        self.assertTrue(result)
        self.assertEqual(self.request.response.status, 401)


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(TestAuth0),))


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
