
# TODO: ----- delete this file when all calls are converted. -----

class ActionTargetType(object):
    """DEPRECATED"""

    Unknown     = 'Unknown'     # use sparingly, for unexpected values.
    ManualEntry = 'ManualEntry'

    # users
    Login       = 'Login'
    User        = 'User'
    Group       = 'Group'
    Role        = 'Role'

    # devices
    Class       = 'Class'
    Organizer   = 'Organizer'
    Device      = 'Device'
    Component   = 'Component'
    Location    = 'Location'
    zProperty   = 'zProperty'

    # templates
    Template    = 'Template'
    DataSource  = 'RRDDataSource'
    DataPoint   = 'RRDDataPoint'
    Graph       = 'Graph'
    GraphPoint  = 'GraphPoint'
    GraphDefinition = 'GraphDefinition'
    Threshold   = 'ThresholdClass'

    # other
    Hub         = 'Hub'
    Collector   = 'Collector'
    Dashboard   = 'Dashboard'
    ZenPack     = 'ZenPack'
    Mib         = 'MIB'
    Process     = 'Process'
    Report      = 'Report'
    Service     = 'Service'
    Network     = 'Network'
    Trigger     = 'Trigger'
    Notification        = 'Notification'
    NotificationWindow  = 'NotificationWindow'


class ActionName(object):
    """DEPRECATED"""

    # Use whatever terminology the code does.
    Create  = 'Create'
    Add     = 'Add'
    Rename  = 'Rename'
    Edit    = 'Edit'
    Move    = 'Move'
    Remove  = 'Remove'
    Delete  = 'Delete'
