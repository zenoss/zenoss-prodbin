
def ensure_prefix(prefix, metric):
    """
    Make sure that a metric name starts with a given prefix, joined by an
    underscore. Returns the prefixed metric name.
    """
    if metric.startswith(prefix + "_"):
        return metric
    return "%s_%s" % (prefix, metric)