import Pyro.core
import sys

Pyro.core.initClient(0)
zem = Pyro.core.getProxyForURI("PYROLOC://localhost:7766/ZEServer")
