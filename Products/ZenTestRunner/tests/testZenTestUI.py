def test_suite():
    from Products import ZenTestUI as product
    from Products.ZenTestRunner import getTestSuites
    return getTestSuites(product)
