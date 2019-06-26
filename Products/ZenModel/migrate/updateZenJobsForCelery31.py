##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import os
import servicemigration as sm

from Products.Jobber.manager import manage_addJobManager
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION  # noqa: E501

import Migrate

log = logging.getLogger("zen.migrate")
sm.require("1.1.11")


class _MigrationData(object):

    startup_command = (
        "su - zenoss -c "
        "\"/opt/zenoss/bin/zenjobs worker "
        "-n zenjobs_$CONTROLPLANE_INSTANCE_ID\""
    )

    loglevels_config_filename = "/opt/zenoss/etc/zenjobs_log_levels.conf"
    loglevels_config = {
        "Filename": loglevels_config_filename,
        "Owner": "zenoss:zenoss",
        "Permissions": "0664",
        "Content": "\n".join([
            "STDOUT          INFO",
            "zen             INFO",
            "zen.zenjobs     INFO",
            "zen.zenjobs.job INFO",
            "celery          WARN",
        ]) + "\n",
    }

    zodb_config_filename = "/opt/zenoss/etc/zodb.conf"
    _zodb_config = {
        "Filename": zodb_config_filename,
        "Owner": "zenoss:zenoss",
        "Permissions": "0660",
        "Content": None,
    }

    @property
    def zodb_config(self):
        content = self._loadfile("zenjobs-celery3126upgrade_zodb.conf")
        self._zodb_config["Content"] = content
        return self._zodb_config

    @property
    def zenjobs_config_content(self):
        return self._loadfile("zenjobs-celery3126upgrade_zenjobs.conf")

    @staticmethod
    def _loadfile(filename):
        cwd = os.path.dirname(__file__)
        config_file = os.path.join(
            cwd, "data", filename,
        )
        with open(config_file) as f:
            return "".join(f.readlines())


migrationData = _MigrationData()


class UpdateZenJobsForCelery31(Migrate.Step):
    """Updates zenjobs related stuff for redis and Celery v3.1.26."""

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        self.replaceJobManager(dmd)
        self.updateServiceDefinition(ctx)

    def replaceJobManager(self, dmd):
        log.info("Removing old JobManager.")
        try:
            del dmd.JobManager
        except Exception:
            dmd._delOb("JobManager")
        log.info("Old JobManager removed.")
        manage_addJobManager(dmd)
        log.info("New JobManager added.")

    def updateServiceDefinition(self, ctx):
        service = next((s for s in ctx.services if s.name == "zenjobs"), None)
        self._updateStartupCommand(service)
        self._deleteActions(service)
        for configName in ("configFiles", "originalConfigs"):
            configFiles = getattr(service, configName)
            self._addConfig(
                configFiles,
                configName,
                migrationData.loglevels_config_filename,
                migrationData.loglevels_config,
            )
            self._addConfig(
                configFiles,
                configName,
                migrationData.zodb_config_filename,
                migrationData.zodb_config,
            )
            self._replaceZenJobsConfig(configFiles, configName)
        self._updateRunningHealthCheck(service)

    def _updateStartupCommand(self, service):
        # Modify the startup command
        if service is None:
            log.warning("zenjobs service not found.")
            return
        service.startup = migrationData.startup_command

    def _deleteActions(self, service):
        service._Service__data["Actions"] = None

    def _addConfig(self, configfiles, configname, filename, config):
        configFile = next((
            cf for cf in configfiles if cf.name == filename
        ), None)
        if configFile is not None:
            log.info(
                "Config file %s already added to %s.", filename, configname,
            )
            return
        configFile = sm.ConfigFile(
            name=filename,
            filename=config.get("Filename"),
            owner=config.get("Owner"),
            permissions=config.get("Permissions"),
            content=config.get("Content"),
        )
        configfiles.append(configFile)
        log.info("Added %s config file to %s.", filename, configname)

    def _replaceZenJobsConfig(self, configfiles, configname):
        filename = "/opt/zenoss/etc/zenjobs.conf"
        configFile = next((
            cf for cf in configfiles
            if cf.name == filename
        ), None)
        if configFile is None:
            log.warning("Adding missing config file %s", filename)
            configFile = sm.ConfigFile(
                name=filename,
                filename=filename,
                owner="zenoss:zenoss",
                permissions="0664",
            )
            configfiles.append(configFile)
        configFile.content = migrationData.zenjobs_config_content
        log.info(
            "Replaced content of %s config file in %s.",
            configFile.filename, configname,
        )

    def _updateRunningHealthCheck(self, service):
        running = next(
            (hc for hc in service.healthChecks if hc.name == "running"),
            None,
        )
        if running is None:
            log.warning("Missing 'running' healthcheck")
        running.script = "pgrep -fu zenoss zenjobs > /dev/null"
        log.info("Updated 'running' healthcheck script.")


UpdateZenJobsForCelery31()
