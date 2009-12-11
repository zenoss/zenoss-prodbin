import transaction

def resolve_context(context, default=None):
    """
    Make sure that a given context is an actual object, and not a path to
    the object, by trying to traverse from the dmd if it's a string.
    """
    dmd = get_dmd()
    if dmd:
        if isinstance(context, basestring):
            # Should be a path to the object we want
            if context.startswith('/') and not context.startswith('/zport/dmd'):
                context = context[1:]
            try:
                context = dmd.unrestrictedTraverse(context)
            except (KeyError, AttributeError):
                context = None
    if context is None:
        context = default
    return context


def get_dmd():
    """
    Retrieve the DMD object.
    """
    connections = transaction.get()._synchronizers.data.values()[:]
    connections.reverse()
    # Make sure we don't get the temporary connection
    for cxn in connections:
        if cxn._db.database_name != 'temporary':
            app = cxn.root()['Application']
            return app.zport.dmd


_MARKER = object()
def safe_hasattr(object, name):
    return getattr(object, name, _MARKER) is not _MARKER