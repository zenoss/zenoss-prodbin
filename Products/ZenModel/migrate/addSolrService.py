##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json
import logging
import os
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class AddSolrService(Migrate.Step):
    """
    Add Solr service and associated healthchecks.
    """
    version = Migrate.Version(116, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # If the service lacks memcached, add it now.
        solr = filter(lambda s: s.name == "Solr", ctx.services)
        log.info("Found %i services named 'Solr'." % len(solr))
        if not solr:
            log.info("No Solr found; creating new service.")
            new_solr = default_solr_service()
            infrastructure = ctx.findServices('^[^/]+/Infrastructure$')[0]
            ctx.deployService(json.dumps(new_solr), infrastructure)
            ctx.commit()


def default_solr_service():
return {
    "CPUCommitment": 2,
    "Command": "setuser zenoss /opt/solr/zenoss/bin/start-solr -cloud -Dbootstrap_confdir=/opt/solr/server/solr/configsets/zenoss_model/conf -Dcollection.configName=zenoss_model",
    "ConfigFiles": {
        "/opt/solr/server/solr/configsets/zenoss_model/conf/solrconfig.xml": {
            "Filename": "/opt/solr/server/solr/configsets/zenoss_model/conf/solrconfig.xml",
            "Owner": "root:root",
            "Permissions": "0664"
        },
        "/opt/solr/server/solr/solr.xml": {
            "FileName": "/opt/solr/server/solr/solr.xml",
            "Owner": "root:root",
            "Permissions": "0664"
        },
        "/opt/solr/zenoss/etc/solr.in.sh": {
            "Filename": "/opt/solr/zenoss/etc/solr.in.sh",
            "Owner": "root:root",
            "Permissions": "0664"
        }
    },
    "Description": "Solr Cloud",
    "EmergencyShutdownLevel": 1,
    "Endpoints": [
        {
            "Application": "solr",
            "Name": "solr",
            "PortNumber": 8983,
            "Protocol": "tcp",
            "Purpose": "export",
            "Vhosts": [
                "solr"
            ]
        }
    ],
    "HealthChecks": {
        "answering": {
            "Interval": 10.0,
            "Script": "curl -A 'Solr answering healthcheck' -s http://localhost:8983/solr/zenoss_model/admin/ping?wt=json | grep -q '\"status\":\"OK\"'"
        },
        "embedded_zk_answering": {
            "Interval": 10.0,
            "Script": "{ echo stats; sleep 1; } | nc 127.0.0.1 9983 | grep -q Zookeeper"
        },
        "zk_connected": {
            "Interval": 10.0,
            "Script": "curl -A 'Solr zk_connected healthcheck' -s http://localhost:8983/solr/zenoss_model/admin/ping?wt=json | grep -q '\"zkConnected\":true'"
        }
    },
    "ImageID": "zenoss/zenoss5x",
    "Instances": {
        "Default": 1,
        "Max": 1,
        "Min": 1
    },
    "Launch": "auto",
    "LogConfigs": [
        {
            "path": "/var/solr/logs/solr.log",
            "type": "solr"
        }
    ],
    "Name": "Solr",
    "Prereqs": [],
    "RAMCommitment": "1G",
    "StartLevel": 1,
    "Tags": [
        "daemon"
    ],
    "Volumes": [
        {
            "ContainerPath": "/opt/solr/server/logs",
            "Owner": "zenoss:zenoss",
            "Permission": "0750",
            "ResourcePath": "solr-logs-{{.InstanceID}}"
        },
        {
            "ContainerPath": "/var/solr/data",
            "Owner": "zenoss:zenoss",
            "Permission": "0750",
            "ResourcePath": "solr-{{.InstanceID}}"
        }
    ]
}
    return {
        "CPUCommitment": 1,
        "Command": "/bin/memcached -u nobody -v -m {{percentScale .RAMCommitment 0.9 | bytesToMB}}",
        "ConfigFiles": {
            "/etc/sysconfig/memcached": {
                "Filename": "/etc/sysconfig/memcached",
                "Owner": "root:root",
                "Permissions": "0644",
                "Content": 'PORT="11211"\nUSER="memcached"\nMAXCONN="1024"\nCACHESIZE="{{.RAMCommitment}}"\nOPTIONS=""\n'
            }
        },
        "Description": "Free & open source, high-performance, distributed memory object caching system",
        "Endpoints": [
            {
                "Application": "memcached",
                "ApplicationTemplate": "memcached",
                "Name": "memcached",
                "PortNumber": 11211,
                "Protocol": "tcp",
                "Purpose": "export"
            }
        ],
        "HealthChecks": {
            "answering": {
                "Interval": 5.0,
                "Script": "{ echo stats; sleep 1; } | nc 127.0.0.1 11211 | grep -q uptime"
            }
        },
        "ImageID": os.environ['SERVICED_SERVICE_IMAGE'],
        "Instances": {
            "Min": 1
        },
        "Launch": "auto",
        "Name": "memcached",
        "RAMCommitment": "1G",
        "Tags": [
            "daemon"
        ]
    }

AddMemcachedService()
