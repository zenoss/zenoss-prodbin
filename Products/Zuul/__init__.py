import zope.component
from Products.ZenModel.interfaces import IDataRoot

def initialize(registrar):
    app = registrar._ProductContext__app
    dmd = app.zport.dmd
    zope.component.provideUtility(dmd, provides=IDataRoot)
