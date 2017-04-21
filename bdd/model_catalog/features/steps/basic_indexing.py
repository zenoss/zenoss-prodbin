from behave import given, when, then


@given('all "{object_type}" have been indexed')
def step_impl(context, object_type):
    # nothing to do
    pass


@when('I search for all "{object_type}" in model catalog')
def step_impl(context, object_type):
    object_type = object_type.lower()
    catalog_helper = context.zen_context.model_catalog_helper
    if object_type == "device classes":
        context.indexed_data = catalog_helper.get_device_classes()
    elif object_type == "event classes":
        context.indexed_data = catalog_helper.get_event_classes()
    elif object_type == "groups":
        context.indexed_data = catalog_helper.get_groups()
    elif object_type == "locations":
        context.indexed_data = catalog_helper.get_locations()
    elif object_type == "systems":
        context.indexed_data = catalog_helper.get_systems()
    elif object_type == "manufacturers":
        context.indexed_data = catalog_helper.get_manufacturers()
    elif object_type == "mib organizers":
        context.indexed_data = catalog_helper.get_mib_organizers()
    elif object_type == "mibs":
        context.indexed_data = catalog_helper.get_mibs()
    elif object_type == "rrd templates":
        context.indexed_data = catalog_helper.get_rrd_templates()
    elif object_type == "process organizers":
        context.indexed_data = catalog_helper.get_process_organizers()
    elif object_type == "processes":
        context.indexed_data = catalog_helper.get_processes()
    elif object_type == "report organizers":
        context.indexed_data = catalog_helper.get_report_organizers()
    elif object_type == "reports":
        context.indexed_data = catalog_helper.get_reports()
    elif object_type == "services":
        context.indexed_data = catalog_helper.get_services()
    elif object_type == "devices":
        context.indexed_data = catalog_helper.get_devices()
    else:
        raise NotImplementedError


@then('I get all the "{object_type}" available in Zenoss')
def step_impl(context, object_type):
    object_type = object_type.lower()
    zodb_helper = context.zen_context.zodb_helper
    if object_type == "device classes":
        device_classes = zodb_helper.get_all_device_classes_path()
        assert set(device_classes) == set(context.indexed_data)
    elif object_type == "event classes":
        assert set(zodb_helper.get_event_classes()) == set(context.indexed_data)
    elif object_type == "groups":
        assert set(zodb_helper.get_groups()) == set(context.indexed_data)
    elif object_type == "locations":
        assert set(zodb_helper.get_locations()) == set(context.indexed_data)
    elif object_type == "systems":
        assert set(zodb_helper.get_systems()) == set(context.indexed_data)
    elif object_type == "manufacturers":
        assert set(zodb_helper.get_manufacturers()) == set(context.indexed_data)
    elif object_type == "mib organizers":
        assert set(zodb_helper.get_mib_organizers()) == set(context.indexed_data)
    elif object_type == "mibs":
        assert set(zodb_helper.get_mibs()) == set(context.indexed_data)
    elif object_type == "rrd templates":
        assert set(zodb_helper.get_rrd_templates()) == set(context.indexed_data)
    elif object_type == "process organizers":
        assert set(zodb_helper.get_process_organizers()) == set(context.indexed_data)
    elif object_type == "processes":
        assert set(zodb_helper.get_processes()) == set(context.indexed_data)
    elif object_type == "report organizers":
        assert set(zodb_helper.get_report_organizers()) == set(context.indexed_data)
    elif object_type == "reports":
        assert set(zodb_helper.get_reports()) == set(context.indexed_data)
    elif object_type == "services":
        assert set(zodb_helper.get_services()) == set(context.indexed_data)
    elif object_type == "devices":
        assert set(zodb_helper.get_devices()) == set(context.indexed_data)
    else:
        raise NotImplementedError




