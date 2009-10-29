class DirectException(Exception):
    pass


try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        raise DirectException("No JSON library available. Please install"
                              " simplejson or upgrade to Python 2.6.")


class DirectRouter(object):
    """
    Basic Ext.Direct router class.

    Ext.Direct allows one to create an API that communicates with a single URL,
    which then routes requests to the appropriate method. The client-side API
    object matches the server-side API object.

    This base class parses an Ext.Direct request, which contains the name of
    the method and any data that should be passed, and routes the data to the
    approriate method. It then receives the output of that call and puts it
    into the data structure expected by Ext.Direct.

    Call an instance of this class with the JSON from an Ext.Direct request.
    """
    def __call__(self, body):
        """
        """
        # Decode the request data
        body = json.loads(body)
        self._body = body

        # Double-check that this request is meant for this class
        action = body.get('action')
        clsname = self.__class__.__name__
        if action != clsname:
            raise DirectException(("Action specified in request ('%s') is"
                                  " not named %s.") % (action, clsname))

        # Pull out the method name and make sure it exists on this class
        method = body.get('method')
        if not method:
            raise DirectException("No method specified. Is this a valid"
                                  " Ext.Direct request?")
        try:
            _targetfn = getattr(self, method)
        except AttributeError:
            raise DirectException("'%s' is not the name of a method on %s" % (
                method, clsname
            ))

        # Pull out any arguments. Sent as an array containing a hash map, so
        # get the first member.
        data = body.get('data')
        if not data:
            data = {}
        else:
            data = data[0]

        # Cast all keys as strings, in case of encoding or other wrinkles
        data = dict((str(k), v) for k,v in data.iteritems())
        self._data = data

        # Finally, call the target method, passing in the data
        result = _targetfn(**data)

        return json.dumps({
            'type':'rpc',
            'tid': body['tid'],
            'action': action,
            'method': method,
            'result': result
        })


class DirectProviderDefinition(object):
    """
    Turns a L{DirectRouter} subclass into JavaScript object representing the
    config of the client-side API.

    Inspects the given subclass and retrieves the names of all public methods,
    then defines those as actions on the Ext.Direct provider, and creates the
    JS that adds the provider.

    See http://extjs.com/products/extjs/direct.php for a full explanation of
    protocols and features of Ext.Direct.
    """
    def __init__(self, routercls, url, ns):
        """
        @param routercls: A L{DirectRouter} subclass
        @type routercls: class
        @param url: The url at which C{routercls} is available
        @type url: str
        @param ns: The client-side namespace in which the provider should live.
                   The provider will be available at [ns].[routercls.__name__].
                   For example, if ns is 'Zenoss.remote' and routercls is named
                   'EventConsole', client-side code would call
                   C{Zenoss.remote.EventConsole.my_method(params, callback)}.
        """
        self.routercls = routercls
        self.url = url
        self.ns = ns

    def render(self):
        """
        Generate and return an Ext.Direct provider definition, wrapped in a
        <script> tag and ready for inclusion in an HTML document.
        """
        attrs = (a for a in self.routercls.__dict__ if not a.startswith('_'))
        methodtpl = '{name:"%s", len:1}'
        methods = ",".join(methodtpl % a for a in attrs)
        source = """
<script type="text/javascript">
    Ext.Direct.addProvider({
        type: 'remoting',
        url: '%(url)s',
        actions: {
            "%(clsname)s":[
              %(methods)s
            ]
        },
        namespace: '%(ns)s'
    });
</script>""" % dict(url=self.url, ns=self.ns, clsname=self.routercls.__name__,
                   methods=methods)
        return source.strip()

