DROP DATABASE IF EXISTS events;
CREATE DATABASE events;
USE events;

CREATE TABLE IF NOT EXISTS status
(
    dedupid         varchar(255) not null,
    evid            char(25) not null,
    device          varchar(128) not null,
    component       varchar(128) default "",
    eventClass      varchar(128) default "/Unknown",
    eventKey        varchar(64) default "",
    summary         varchar(128) not null,
    message         varchar(4096) default "",
    severity        smallint default -1,
    eventState      smallint default 0,
    eventClassKey   varchar(128) default "",
    eventGroup      varchar(64) default "",
    stateChange     timestamp,
    firstTime       double,
    lastTime        double,
    count           int default 1,
    prodState       smallint default 0,
    suppid          char(36) not null,
    manager         varchar(128) not null,
    agent           varchar(64) not null,
    DeviceClass     varchar(128) default "",
    Location        varchar(128) default "",
    Systems         varchar(255) default "",
    DeviceGroups    varchar(255) default "",
    ipAddress       char(15) default "",
    priority        smallint default -1,
    facility        varchar(8) default "unknown",
    PRIMARY KEY ( dedupid ),
    Index evididx (evid)
) ENGINE=MEMORY MAX_ROWS=20000;

CREATE TABLE IF NOT EXISTS history
(
    dedupid         varchar(255) not null,
    evid            char(25) not null,
    device          varchar(128) not null,
    component       varchar(128) default "",
    eventClass      varchar(128) default "/Unknown",
    eventKey        varchar(64) default "",
    summary         varchar(128) not null,
    message         varchar(4096) default "",
    severity        smallint default -1,
    eventState      smallint default 0,
    eventClassKey    varchar(128) default "",
    eventGroup      varchar(64) default "",
    stateChange     timestamp,
    firstTime       double,
    lastTime        double,
    count           int default 1,
    prodState       smallint default 0,
    suppid          char(36) not null,
    manager         varchar(128) not null,
    agent           varchar(64) not null,
    DeviceClass     varchar(128) default "",
    Location        varchar(128) default "",
    Systems         varchar(255) default "",
    DeviceGroups    varchar(255) default "",
    ipAddress       char(15) default "",
    facility        varchar(8) default "unknown",
    priority        smallint default -1,
    deletedTime     timestamp,
    PRIMARY KEY ( evid ),
    INDEX DateRange (firstTime, lastTime)
) ENGINE=INNODB;

CREATE TRIGGER status_delete BEFORE DELETE ON status
    FOR EACH ROW INSERT INTO history VALUES (
            OLD.dedupid,
            OLD.evid,
            OLD.device,
            OLD.component,
            OLD.eventClass,
            OLD.eventKey,
            OLD.summary,
            OLD.message,
            OLD.severity,
            OLD.eventState,
            OLD.eventClassKey,
            OLD.eventGroup,
            OLD.stateChange,
            OLD.firstTime,
            OLD.lastTime,
            OLD.count,
            OLD.prodState,
            OLD.suppid,
            OLD.manager,
            OLD.agent,
            OLD.DeviceClass,
            OLD.Location,
            OLD.Systems,
            OLD.DeviceGroups,
            OLD.ipAddress,
            OLD.facility,
            OLD.priority,
            NULL
            );


CREATE TABLE IF NOT EXISTS heartbeat
(
    device          varchar(128) not null,
    component       varchar(128) default "",
    timeout         int default 0,
    lastTime        timestamp,
    PRIMARY KEY ( device,component )
) ENGINE=MEMORY MAX_ROWS=10000;


CREATE TABLE IF NOT EXISTS alert_state
(
    evid        char(25) not null,
    userid      varchar(64),
    rule        varchar(255),
    PRIMARY KEY ( evid, userid, rule )
) ENGINE=INNODB;


CREATE TABLE IF NOT EXISTS log
(
    evid        char(25) not null,
    userName    varchar(64),
    ctime       timestamp,
    text        text,
    Index evididx (evid)
) ENGINE=INNODB;


CREATE TABLE IF NOT EXISTS detail
(
    evid        char(25) not null,
    sequence    int,
    name        varchar(255),
    value       varchar(255),
    PRIMARY KEY ( evid, name ),
    Index evididx (evid)
) ENGINE=INNODB;


CREATE TABLE IF NOT EXISTS conversions
(
    KeyField    varchar(255) not null,
    Colname     varchar(255),
    Value       int,
    Conversion  varchar(255),
    primary key  ( KeyField )
) ENGINE=INNODB;

CREATE TABLE IF NOT EXISTS col_visuals
(
    Colname         varchar(255) not null,
    Title           varchar(255),
    DefWidth        int,
    MaxWidth        int,
    TitleJustify    int,
    DataJustify     int,
    PRIMARY KEY ( Colname )
) ENGINE=INNODB;
