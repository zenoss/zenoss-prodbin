##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from behave import given, when, then

@given('I can connect to "{connectable}"')
def step_impl(context, connectable):
    connectable = connectable.lower()
    if connectable == "zodb":
        assert context.zen_context.dmd.Devices is not None
    elif connectable == "model_catalog" or connectable == "model catalog":
        assert context.zen_context.solr_client.ping() is True