import Pyro.core
import sys

Pyro.core.initClient(0)
zdm = Pyro.core.getProxyForURI("PYROLOC://localhost:7766/EventServer")
uri = zdm.openDatabase("zentinel")
zdb = Pyro.core.getProxyForURI(uri)

