##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")

class addOpenTSDBLogbackConfig(Migrate.Step):
    """ Set Editable Logback configuration file for OpenTSDB. See ZEN-26681 """
    version = Migrate.Version(114, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        services = filter(lambda s: "opentsdb" in ctx.getServicePath(s), ctx.services)
        log.info("Found %i services with 'opentsdb' in their service path." % len(services))
        services = filter(lambda s: "/opt/zenoss/etc/opentsdb/opentsdb.conf" in [i.name for i in s.originalConfigs], services)
        log.info("Of those, %i services use /opt/zenoss/etc/opentsdb/opentsdb.conf." % len(services))
        hm_content = '<?xml version="1.0" encoding="UTF-8"?>\n<configuration>\n  <!--<jmxConfigurator/>-->\n  <appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender">\n    <encoder>\n      <pattern>\n        %d{ISO8601} %-5level [%thread] %logger{0}: %msg%n\n      </pattern>\n    </encoder>\n  </appender>\n\n  <!-- This appender is responsible for the /logs endpoint. It maintains MaxSize\n       lines of the log file in memory. If you don\'t need the endpoint, disable\n       this appender (by removing the line "<appender-ref ref="CYCLIC"/>" in\n       the "root" section below) to save some cycles and memory. -->\n  <appender name="CYCLIC" class="ch.qos.logback.core.read.CyclicBufferAppender">\n    <MaxSize>1024</MaxSize>\n  </appender>\n\n  <!-- Appender to write OpenTSDB data to a set of rotating log files -->\n  <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">\n    <file>/var/log/opentsdb/opentsdb.log</file>\n    <append>true</append>\n\n    <rollingPolicy class="ch.qos.logback.core.rolling.FixedWindowRollingPolicy">\n      <fileNamePattern>/var/log/opentsdb/opentsdb.log.%i</fileNamePattern>\n      <minIndex>1</minIndex>\n      <maxIndex>3</maxIndex>\n    </rollingPolicy>\n\n    <triggeringPolicy class="ch.qos.logback.core.rolling.SizeBasedTriggeringPolicy">\n      <maxFileSize>128MB</maxFileSize>\n    </triggeringPolicy>\n\n    <encoder>\n      <pattern>%d{HH:mm:ss.SSS} %-5level [%logger{0}.%M] - %msg%n</pattern>\n    </encoder>\n  </appender>\n\n  <!-- Appender for writing full and completed queries to a log file. To use it, make\n       sure to set the "level" to "INFO" in QueryLog below. -->\n  <appender name="QUERY_LOG" class="ch.qos.logback.core.rolling.RollingFileAppender">\n    <file>/var/log/opentsdb/queries.log</file>\n    <append>true</append>\n\n    <rollingPolicy class="ch.qos.logback.core.rolling.FixedWindowRollingPolicy">\n        <fileNamePattern>/var/log/opentsdb/queries.log.%i</fileNamePattern>\n        <minIndex>1</minIndex>\n        <maxIndex>4</maxIndex>\n    </rollingPolicy>\n\n    <triggeringPolicy class="ch.qos.logback.core.rolling.SizeBasedTriggeringPolicy">\n        <maxFileSize>128MB</maxFileSize>\n    </triggeringPolicy>\n    <encoder>\n        <pattern>%date{ISO8601} [%logger.%M] %msg%n</pattern>\n    </encoder>\n  </appender>\n\n  <!-- Per class logger levels -->\n  <logger name="QueryLog" level="OFF" additivity="false">\n    <appender-ref ref="QUERY_LOG"/>\n  </logger>\n  <logger name="org.apache.zookeeper" level="INFO"/>\n  <logger name="org.hbase.async" level="INFO"/>\n  <logger name="com.stumbleupon.async" level="INFO"/>\n\n  <!-- Fallthrough root logger and router -->\n  <root level="INFO">\n    <appender-ref ref="STDOUT"/>\n    <appender-ref ref="CYCLIC"/>\n    <appender-ref ref="FILE"/>\n  </root>\n</configuration>\n\n'
        content = hm_content

        def equal(this, that):
            return this.name == that.name and this.filename == that.filename and this.owner == that.owner and this.permissions == that.permissions and this.content == that.content

        for service in services:
            newConfig = sm.ConfigFile(
                name="/opt/opentsdb/src/logback.xml",
                filename="/opt/opentsdb/src/logback.xml",
                owner="root:root",
                permissions="0664",
                 content=content
            )

            # If there's a config with the same name but is different from
            # the new config, overwrite it.
            if all([not equal(config, newConfig) for config in service.originalConfigs]):
                service.originalConfigs.append(newConfig)
                changed = True
                log.info("Adding a configuration to OriginalConfigs of %s", service.name)

            # Add this config only if there's no config with the same name.
            # If there is such config, honor it.
            if all([not config.name == newConfig.name for config in service.configFiles]):
                service.configFiles.append(newConfig)
                changed = True
                log.info("Adding a configuration to ConfigFiles of %s", service.name)

        log.info("Configuration added for OpenTSDB services")
        ctx.commit()

addOpenTSDBLogbackConfig()
