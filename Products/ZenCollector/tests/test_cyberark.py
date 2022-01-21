##############################################################################
#
# Copyright (C) Zenoss, Inc. 2022, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import httplib

from unittest import TestCase
from mock import call, Mock, patch
from twisted.internet.interfaces import IOpenSSLClientConnectionCreator
from zope.interface.verify import verifyObject

from Products.ZenCollector.cyberark import (
    _CFG_QUERY,
    _CFG_URL,
    _CFG_PORT,
    _CFG_CERT_PATH,
    _default_config,
    _cyberark_flag,
    get_cyberark,
    load_certificates,
    CyberArk,
    CyberArkManager,
    CyberArkClient,
    CyberArkProperty,
)

PATH = {'src': 'Products.ZenCollector.cyberark'}


class TestFunctions(TestCase):

    def setUp(t):
        t.log_patcher = patch("{src}.log".format(**PATH), autospec=True)
        t.log = t.log_patcher.start()
        t.addCleanup(t.log_patcher.stop)

        t.getGlobalConfiguration_patcher = patch(
            '{src}.getGlobalConfiguration'.format(**PATH),
            name='getGlobalConfiguration',
            autospec=True,
        )
        t.getGlobalConfiguration = t.getGlobalConfiguration_patcher.start()
        t.addCleanup(t.getGlobalConfiguration_patcher.stop)

    def test_get_cyberark_no_config(t):
        config_mock = {}
        t.getGlobalConfiguration.return_value = config_mock

        result = get_cyberark()
        t.assertIsNone(result)
        t.log.info.assert_called_once_with(
            "CyberArk unavailable. No configuration found.",
        )

    @patch("{src}.CyberArk".format(**PATH), autospec=True)
    def test_get_cyberark_failed(t, _cyberark):
        t.getGlobalConfiguration.return_value = {
            "cyberark-url": "https://vault",
        }
        _cyberark.from_dict.side_effect = Exception("boom")

        result = get_cyberark()
        t.assertIsNone(result)
        t.log.exception.assert_called_once_with(
            "CyberArk failed to initialize.",
        )

    @patch("{src}.load_certificates".format(**PATH))
    def test_get_cyberark_bad_certs(t, _load_certs):
        t.getGlobalConfiguration.return_value = {
            "cyberark-url": "https://vault",
        }
        _load_certs.side_effect = Exception("boom")

        result = get_cyberark()
        t.assertIsNone(result)
        t.log.exception.assert_called_once_with(
            "CyberArk failed to initialize.",
        )

    @patch("{src}.CyberArkManager".format(**PATH), autospec=True)
    def test_get_cyberark_success(t, _manager):
        t.getGlobalConfiguration.return_value = {
            "cyberark-url": "https://vault",
            "cyberark-query": "/foo",
        }
        _manager.from_dict.return_value = _manager

        result = get_cyberark()
        t.assertIsInstance(result, CyberArk)
        t.assertIs(result._manager, _manager)
        t.assertEqual(result._base_query, "/foo")


class TestCyberArk(TestCase):

    class Conf(object):
        def __init__(self, query):
            self.configId = "dev1"
            self.zProp1 = "value1"
            self.zProp2 = "%s?h=g" % query

    def setUp(t):
        t.log_patcher = patch("{src}.log".format(**PATH), autospec=True)
        t.log = t.log_patcher.start()
        t.addCleanup(t.log_patcher.stop)

        t.queryUtility_patcher = patch(
            "{src}.queryUtility".format(**PATH), autospec=True,
        )
        t.queryUtility = t.queryUtility_patcher.start()
        t.addCleanup(t.queryUtility_patcher.stop)

        t.client = Mock(spec=CyberArkClient)
        t.manager = CyberArkManager(100, t.client)

    @patch("{src}.CyberArkManager".format(**PATH), autospec=True)
    def test_from_dict(t, _manager):
        query = "/foo/bar"
        conf = {_CFG_QUERY: query}
        mgr = _manager.from_dict.return_value

        vault = CyberArk.from_dict(conf)
        t.assertEqual(vault._base_query, query)
        t.assertEqual(vault._manager, mgr)
        _manager.from_dict.assert_called_once_with(conf)

    def test_update_config_no_value(t):
        query = "/foo/bar"
        vault = CyberArk(query, t.manager)
        conf = t.Conf(query)

        vault.update_config(conf)

        t.assertTrue(getattr(conf, _cyberark_flag, None))
        t.assertEqual(conf.zProp2, "")
        t.assertEqual(conf.zProp1, "value1")

        props = t.manager.getPropertiesFor(conf.configId)
        t.assertEqual(len(props), 1)
        prop = props[0]
        t.assertEqual(prop.deviceId, conf.configId)
        t.assertEqual(prop.name, "zProp2")
        t.assertEqual(prop.value, None)
        t.assertEqual(prop.query, "%s?h=g" % query)

    def test_update_config_has_value(t):
        query = "/foo/bar"
        vault = CyberArk(query, t.manager)
        conf = t.Conf(query)

        status = httplib.OK
        result = """{"Content": "stuff"}"""
        t.client.request.return_value = (status, result)

        vault.update_config(conf)

        t.assertTrue(getattr(conf, _cyberark_flag, None))
        t.assertEqual(conf.zProp2, "stuff")
        t.assertEqual(conf.zProp1, "value1")

        props = t.manager.getPropertiesFor(conf.configId)
        t.assertEqual(len(props), 1)
        prop = props[0]
        t.assertEqual(prop.deviceId, conf.configId)
        t.assertEqual(prop.name, "zProp2")
        t.assertEqual(prop.value, "stuff")
        t.assertEqual(prop.query, "%s?h=g" % query)

    def test_update_config_no_props(t):
        query = "/foo/bar"
        vault = CyberArk(query, t.manager)
        conf = t.Conf(query)
        conf.zProp2 = "value2"

        vault.update_config(conf)

        t.assertFalse(None)
        t.assertFalse(getattr(conf, _cyberark_flag, None))
        t.assertEqual(conf.zProp2, "value2")
        t.assertEqual(conf.zProp1, "value1")

        props = t.manager.getPropertiesFor(conf.configId)
        t.assertEqual(len(props), 0)


class TestCyberArkManager(TestCase):

    def setUp(t):
        t.log_patcher = patch("{src}.log".format(**PATH), autospec=True)
        t.log = t.log_patcher.start()
        t.addCleanup(t.log_patcher.stop)

        t.queryUtility_patcher = patch(
            "{src}.queryUtility".format(**PATH), autospec=True,
        )
        t.queryUtility = t.queryUtility_patcher.start()
        t.addCleanup(t.queryUtility_patcher.stop)

    def test_add(t):
        client = Mock(spec=CyberArkClient)
        ttl = 100
        devId = "thedevice"
        zprop = "password"
        query = _default_config[_CFG_QUERY] + "foo&safe=Test&object=bar"
        mgr = CyberArkManager(ttl, client)

        mgr.add(devId, zprop, query)

        props = mgr.getPropertiesFor(devId)
        t.assertEqual(len(props), 1)

        prop = props[0]
        t.assertEqual(prop.deviceId, devId)
        t.assertEqual(prop.name, zprop)
        t.assertEqual(prop.query, query)
        t.assertIsNone(prop.value)

    def test_update_nominal(t):
        client = Mock(spec=CyberArkClient)
        status = httplib.OK
        result = """{"Content": "stuff"}"""
        client.request.return_value = (status, result)

        ttl = 100
        devId = "thedevice"
        zprop = "password"
        query = _default_config[_CFG_QUERY] + "foo&safe=Test&object=bar"
        mgr = CyberArkManager(ttl, client)
        mgr.add(devId, zprop, query)

        mgr.update(devId)
        client.request.assert_called_once_with(query)
        t.assertEqual("stuff", mgr.getPropertiesFor(devId)[0].value)

    def test_update_from_cache(t):
        client = Mock(spec=CyberArkClient)
        status = httplib.OK
        result = """{"Content": "stuff"}"""
        client.request.return_value = (status, result)

        ttl = 100
        dev1 = "device1"
        dev2 = "device2"
        zprop = "password"
        query = _default_config[_CFG_QUERY] + "foo&safe=Test&object=bar"
        mgr = CyberArkManager(ttl, client)

        mgr.add(dev1, zprop, query)
        mgr.add(dev2, zprop, query)

        mgr.update(dev1)
        mgr.update(dev2)

        client.request.assert_called_once_with(query)
        t.assertEqual("stuff", mgr.getPropertiesFor(dev1)[0].value)
        t.assertEqual("stuff", mgr.getPropertiesFor(dev2)[0].value)

    def test_update_notfound(t):
        client = Mock(spec=CyberArkClient)
        status = httplib.NOT_FOUND
        result = """{}"""
        client.request.return_value = (status, result)

        ttl = 100
        devId = "thedevice"
        zprop = "password"
        query = _default_config[_CFG_QUERY] + "foo&safe=Test&object=bar"
        mgr = CyberArkManager(ttl, client)

        expected = call(
            "Invalid value for 'object' or 'safe' parameters in query  "
            "device=%s zproperty=%s query=%s",
            devId, zprop, query,
        )

        mgr.add(devId, zprop, query)

        mgr.update(devId)
        client.request.assert_called_once_with(query)
        t.assertIsNone(mgr.getPropertiesFor(devId)[0].value)
        actual = t.log.error.mock_calls[0]
        t.assertEqual(expected, actual)

    def test_update_forbidden(t):
        client = Mock(spec=CyberArkClient)
        status = httplib.FORBIDDEN
        result = """{}"""
        client.request.return_value = (status, result)

        ttl = 100
        devId = "thedevice"
        zprop = "password"
        query = _default_config[_CFG_QUERY] + "foo&safe=Test&object=bar"
        mgr = CyberArkManager(ttl, client)

        expected = call(
            "Access not allowed (invalid value appid parameter?)  "
            "device=%s zproperty=%s query=%s",
            devId, zprop, query,
        )

        mgr.add(devId, zprop, query)

        mgr.update(devId)
        client.request.assert_called_once_with(query)
        t.assertIsNone(mgr.getPropertiesFor(devId)[0].value)
        actual = t.log.error.mock_calls[0]
        t.assertEqual(expected, actual)

    def test_update_other(t):
        client = Mock(spec=CyberArkClient)
        status = 410
        result = """{}"""
        client.request.return_value = (status, result)

        ttl = 100
        devId = "thedevice"
        zprop = "password"
        query = _default_config[_CFG_QUERY] + "foo&safe=Test&object=bar"
        mgr = CyberArkManager(ttl, client)

        expected = call(
            "CyberArk request failed  "
            "status=%s %s device=%s zproperty=%s query=%s ",
            status, httplib.responses.get(status),
            devId, zprop, query,
        )

        mgr.add(devId, zprop, query)

        mgr.update(devId)
        client.request.assert_called_once_with(query)
        t.assertIsNone(mgr.getPropertiesFor(devId)[0].value)
        actual = t.log.error.mock_calls[0]
        t.assertEqual(expected, actual)

    def test_update_failure(t):
        client = Mock(spec=CyberArkClient)
        ex = RuntimeError("boom")
        client.request.side_effect = ex

        ttl = 100
        devId = "thedevice"
        zprop = "password"
        query = _default_config[_CFG_QUERY] + "foo&safe=Test&object=bar"
        mgr = CyberArkManager(ttl, client)

        expected = call(
            "Failed to execute CyberArk query - %s  "
            "device=%s zproperty=%s query=%s",
            ex, devId, zprop, query,
        )

        mgr.add(devId, zprop, query)

        mgr.update(devId)
        client.request.assert_called_once_with(query)
        t.assertIsNone(mgr.getPropertiesFor(devId)[0].value)
        actual = t.log.error.mock_calls[0]
        t.assertEqual(expected, actual)


class TestCyberArkClient(TestCase):

    def setUp(t):
        t.log_patcher = patch("{src}.log".format(**PATH), autospec=True)
        t.log = t.log_patcher.start()
        t.addCleanup(t.log_patcher.stop)

        t.load_certificates_patcher = patch(
            "{src}.load_certificates".format(**PATH), autospec=True,
        )
        t.load_certificates = t.load_certificates_patcher.start()
        t.addCleanup(t.load_certificates_patcher.stop)

        t.agent_patcher = patch(
            "{src}.client.Agent".format(**PATH), autospec=True,
        )
        t.agent = t.agent_patcher.start()
        t.addCleanup(t.agent_patcher.stop)

        t.readBody_patcher = patch(
            "{src}.client.readBody".format(**PATH), autospec=True,
        )
        t.readBody = t.readBody_patcher.start()
        t.addCleanup(t.readBody_patcher.stop)

    def test_from_dict(t):
        url = "https://vault"
        port = "443"
        path = "/foo/bar"
        conf = {
            _CFG_URL: url,
            _CFG_PORT: port,
            _CFG_CERT_PATH: path,
        }

        client = CyberArkClient.from_dict(conf)
        t.assertEqual(client.base_url, url)
        t.load_certificates.assert_called_once_with(url, path)

    def test_non_standard_port(t):
        url = "https://vault/alias"
        port = "8443"
        options = Mock()
        client = CyberArkClient(url, port, options)
        t.assertEqual(client.base_url, "https://vault:8443")
        t.assertEqual(client.base_path, "/alias")

    def test_url_normalization(t):
        url = "https://vault:443/alias"
        port = "443"
        options = Mock()
        client = CyberArkClient(url, port, options)
        t.assertEqual(client.base_url, "https://vault")
        t.assertEqual(client.base_path, "/alias")

    def test_no_path(t):
        url = "https://vault"
        port = "443"
        options = Mock()
        client = CyberArkClient(url, port, options)
        t.assertEqual(client.base_url, "https://vault")
        t.assertEqual(client.base_path, "")

    def test_request(t):
        client = CyberArkClient("https://vault", 443, Mock())
        expected_result = t.readBody.return_value
        ag = t.agent.return_value
        expected_code = ag.request.return_value.code

        dfr = client.request("/bar/baz?appid=foo&object=foo")
        code, result = dfr.result
        t.assertEqual(result, expected_result)
        t.assertEqual(code, expected_code)
        ag.request.assert_called_once_with(
            "GET",
            "https://vault/bar/baz?appid=foo&object=foo",
            None,
            None
        )

    def test_request_with_extra_path(t):
        client = CyberArkClient("https://vault/alias", 443, Mock())
        expected_result = t.readBody.return_value
        ag = t.agent.return_value
        expected_code = ag.request.return_value.code

        dfr = client.request("/bar/baz?appid=foo&object=foo")
        code, result = dfr.result
        t.assertEqual(result, expected_result)
        t.assertEqual(code, expected_code)
        ag.request.assert_called_once_with(
            "GET",
            "https://vault/alias/bar/baz?appid=foo&object=foo",
            None,
            None
        )

    def test_request_failure(t):
        client = CyberArkClient("https://vault", 443, Mock())
        ex = RuntimeError("boom")
        t.agent.return_value.request.side_effect = ex

        dfr = client.request("/bar/baz?appid=foo&object=foo")
        dfr.addErrback(lambda x: x.value)
        t.assertEqual(ex, dfr.result)
        t.log.exception.assert_called_once_with(
            "Request failed url=%s",
            "https://vault/bar/baz?appid=foo&object=foo",
        )

    def test_readBody_failure(t):
        client = CyberArkClient("https://vault", 443, Mock())
        ex = RuntimeError("boom")

        def go_boom(*args, **kw):
            raise ex

        t.readBody.side_effect = go_boom

        dfr = client.request("/bar/baz?appid=foo&object=foo")
        dfr.addErrback(lambda x: x.value)
        t.assertEqual(ex, dfr.result)
        t.log.exception.assert_called_once_with(
            "Failed to read message body  url=%s",
            "https://vault/bar/baz?appid=foo&object=foo",
        )


class TestCyberArkProperty(TestCase):

    def test_init(t):
        dev = "device1"
        zprop = "prop1"
        query = "/foo/bar?h=g"

        prop = CyberArkProperty(dev, zprop, query)

        t.assertEqual(prop.deviceId, dev)
        t.assertEqual(prop.name, zprop)
        t.assertEqual(prop.query, query)
        t.assertIsNone(prop.value)


rootCA_crt = """
-----BEGIN CERTIFICATE-----
MIIC1jCCAj+gAwIBAgIUDmS1sDHq5ZxY2xMz3OVPbT/LjfgwDQYJKoZIhvcNAQEL
BQAwfTELMAkGA1UEBhMCVVMxDjAMBgNVBAgMBVRleGFzMQ8wDQYDVQQHDAZBdXN0
aW4xDzANBgNVBAoMBlplbm9zczEMMAoGA1UECwwDRGV2MQ8wDQYDVQQDDAZaZW5v
c3MxHTAbBgkqhkiG9w0BCQEWDmRldkB6ZW5vc3MuY29tMB4XDTIyMDEyNjE3MDc0
NFoXDTI2MTIzMTE3MDc0NFowfTELMAkGA1UEBhMCVVMxDjAMBgNVBAgMBVRleGFz
MQ8wDQYDVQQHDAZBdXN0aW4xDzANBgNVBAoMBlplbm9zczEMMAoGA1UECwwDRGV2
MQ8wDQYDVQQDDAZaZW5vc3MxHTAbBgkqhkiG9w0BCQEWDmRldkB6ZW5vc3MuY29t
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQD5NUfsKhsfkDOQfiuJCzdk3GHD
A6J2ISD0cCRyhfqLWbu6Gz6yjmLMSrwqzp9xSPqbHTo3uC916aRdOREnOLeeNgMD
eHTQKbtEooNMXaeU0WwTHbWmsT6XI8tifAiMFsALsuZtXrObr1NFWPMSxOdrqnjg
FycFdbZB6Rvys1hiaQIDAQABo1MwUTAdBgNVHQ4EFgQU3RLbuadNNemGXzwMtv+P
+PytrgswHwYDVR0jBBgwFoAU3RLbuadNNemGXzwMtv+P+PytrgswDwYDVR0TAQH/
BAUwAwEB/zANBgkqhkiG9w0BAQsFAAOBgQBXRCxYTdityAm0zK+MvpETpWZxNOdV
ZBFIohave+TAnpTyb8YpC1fCK/8dY4Q53yL/MNW9XosKI+5eQa+8X/FNEXv1TwNs
gHbYHHO7onDPDzkQoXBC0K65m8fSTsdbxazjG2UddyfWkI9wjESkE6yZjgtN52T3
90Q7rR7mG9d9cA==
-----END CERTIFICATE-----
"""

client_crt = """
-----BEGIN CERTIFICATE-----
MIICfDCCAeUCFCIyzicXHM920mzh6McYBfIKAmeQMA0GCSqGSIb3DQEBCwUAMH0x
CzAJBgNVBAYTAlVTMQ4wDAYDVQQIDAVUZXhhczEPMA0GA1UEBwwGQXVzdGluMQ8w
DQYDVQQKDAZaZW5vc3MxDDAKBgNVBAsMA0RldjEPMA0GA1UEAwwGWmVub3NzMR0w
GwYJKoZIhvcNAQkBFg5kZXZAemVub3NzLmNvbTAeFw0yMjAxMjYxNzEwMDBaFw0y
NjEyMzExNzEwMDBaMH0xCzAJBgNVBAYTAlVTMQ4wDAYDVQQIDAVUZXhhczEPMA0G
A1UEBwwGQXVzdGluMQ8wDQYDVQQKDAZaZW5vc3MxDDAKBgNVBAsMA0RldjEPMA0G
A1UEAwwGWmVub3NzMR0wGwYJKoZIhvcNAQkBFg5kZXZAemVub3NzLmNvbTCBnzAN
BgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEAwYaLu8f8Hd9yTqGCfFXb1P60LEzlGUom
mStO06zfk3FFz9MBEbVHX53+92R/xhKVfUiRa967COM4y6XJHnfPD/sFBCir4z4+
ApLRV8jEsWYP/sDG59nZDZm+IUqOwqWfYlvJWpbOlFC5s1q4xeECemM88c9poKAZ
AW3H9oM/pR0CAwEAATANBgkqhkiG9w0BAQsFAAOBgQDDH+LvhUfdLTGF2L/KwHxw
KdWs1KEoFUqI2kD9nUVDj0WoX6pSE8/txRS3Pw2PsA2KahAPTAOZJcLVy5rbUCvF
+DgiPegUZ/btgGrrT5NfTPtkb1E8wNsz+XOEwzlzNakA08Lec6q/vBewJVm2duMd
bqCsKPJj+yBv0nMqFWgVmQ==
-----END CERTIFICATE-----
"""

client_pem = """
-----BEGIN RSA PRIVATE KEY-----
MIICWwIBAAKBgQDBhou7x/wd33JOoYJ8VdvU/rQsTOUZSiaZK07TrN+TcUXP0wER
tUdfnf73ZH/GEpV9SJFr3rsI4zjLpcked88P+wUEKKvjPj4CktFXyMSxZg/+wMbn
2dkNmb4hSo7CpZ9iW8lals6UULmzWrjF4QJ6Yzzxz2mgoBkBbcf2gz+lHQIDAQAB
AoGANo+lY7rdVNrDknGspTtbsDBjQb4oNToXqcVxAvLRUfN0mERIH+L5DXcxBDS8
ZW6l4N2NyljQaJAPWjMSgdmLcdrhzABsicKQ1/gkjsfNK8Rz0IzlfR/MuljrFC6s
ZUeWuBsd5wp8/RrFXZVcNypV7mvJ/iJGZnoZqrAwn5bNS20CQQD06C8inRZRjhZC
wtvl/XQaiPsgoez8J8VU2lHMhIvFiJWp4dztoPsBi74MQcF/TgoItn2AmOtZOtph
3H7y1GMLAkEAykqRvYv6eoNbmMZFvDvyVJu2rbVAn0qWJz988oLrmduWWAMy5L2Z
pShUAnkBRT7FbXWYAjeSUEX8PITflQGxdwJAe6ic3CpbMZS/0rfXFprSO++8dW6t
XWirb7vIn66xcG0VvLCJwAaPluk7ba7qB+CcmmeimQMdmnFoAQ+3nd71nwJAA5Yy
41N6C3YMx7asQdwmPc3M/WN7U9e0tdlwU7RyjPXRwpm760ZZVQ5T/v86QIoOYhR1
r4Rgub+j60bH2BKBnQJAIDZfnhUFv6eYy6I/yPcQ+sIOjC7X1/6XjjPNMAeOheVn
zUc7lh/1HLm55dzLz2Csrosc5YX3ZV99h58Mm5k+Vw==
-----END RSA PRIVATE KEY-----
"""


class TestLoadCertificates(TestCase):

    def setUp(t):
        t.FilePath_patcher = patch(
            "{src}.FilePath".format(**PATH),
            autospec=True,
        )
        t.FilePath = t.FilePath_patcher.start()
        t.addCleanup(t.FilePath_patcher.stop)

        def content(path):
            m = Mock()
            if path.endswith("RootCA.crt"):
                m.getContent.return_value = rootCA_crt
            elif path.endswith("client.crt"):
                m.getContent.return_value = client_crt
            elif path.endswith("client.pem"):
                m.getContent.return_value = client_pem
            return m

        t.FilePath.side_effect = content

    def test_load_certificates(t):
        result = load_certificates("https://vault", "/var/zenoss/cyberark")
        t.assertTrue(verifyObject(IOpenSSLClientConnectionCreator, result))
