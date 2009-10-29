import unittest

class TestEvents(unittest.TestCase):
    pass

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(TestEvents),
    ))

if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
