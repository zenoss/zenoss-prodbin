def test_suite():
    from Products import ZenUITests as product
    from Products.ZenTestRunner import getTestSuites
    return getTestSuites(product)
