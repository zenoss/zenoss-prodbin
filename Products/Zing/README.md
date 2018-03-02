
## Zing package

This package contains all the necessary logic to send Facts to zing-connector. Two classes to do it:


### zing_connector.ZingConnectorClient:

ZingConnectorClient creates a new client everytime a new object is created.

```
from zope.component import createObject
client = createObject('ZingConnectorClient')
if client.ping():
    client.send_facts(FACTS)
```

### zing_connector.ZingConnectorProxy:

ZingConnectorProxy creates a ZingConnectorClient for each Zope thread and clients will be reused during the time zope is running. The constructor takes a `context` that should be a persistent object. If `context` is not a persistent object, then a new client will be created every time a new ZingConnectorProxy object is created.

```
from Products.Zing.interfaces import IZingConnectorProxy
zing_connector = IZingConnectorProxy(context)
if zing_connector.ping():
    zing_connector.send_facts(FACTS)
```