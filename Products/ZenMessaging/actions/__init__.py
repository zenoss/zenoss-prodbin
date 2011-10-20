
# TODO: ----- delete this file when all calls are converted. -----

from Products.ZenMessaging.audit import audit

def sendUserAction(actionTargetType, actionName, **kwargs):
    """Deprecated"""
    category = '.'.join(('Deprecated', actionTargetType, actionName))
    audit(category, **kwargs)
