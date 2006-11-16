def test_suite():
    from Products import ZenModel as product
    from Products.ZenTestRunner import getTestSuites
    return getTestSuites(product)
