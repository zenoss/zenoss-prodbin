#!/usr/bin/env python

import json
import sys
import servicemigration as sm
sm.require("1.0.0")

TMP_FILENAME = "/tmp/zenoss-service-migration.json"
SERVICE_NAME_TO_REMOVE = "zenhubiworker"


def remove_service_from_file(file_path, service_name):
    with open(file_path, 'r') as file:
        data = json.load(file)

    if data.get("Deploy"):
        data['Deploy'] = [service for service in data['Deploy'] if service['Service']['Name'] != service_name]

        with open(file_path, 'w') as file:
            json.dump(data, file)


if sys.argv[-1] == "begin":
    ctx = sm.ServiceContext()
    ctx.commit(TMP_FILENAME)
    remove_service_from_file(TMP_FILENAME, SERVICE_NAME_TO_REMOVE)
    print TMP_FILENAME
elif sys.argv[-1] == "end":
    ctx = sm.ServiceContext(TMP_FILENAME)
    ctx.commit()
else:
    raise ValueError("No operation specified.")
