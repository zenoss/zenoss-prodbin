DROP DATABASE IF EXISTS events;
CREATE DATABASE events;
USE events;

CREATE TABLE IF NOT EXISTS status
(
    dedupid         varchar(255) not null,
    evid            char(36) not null,
    device          varchar(128) not null,
    ipAddress       char(15) default "",
    component       varchar(128) default "",
    eventClass      varchar(64) default "Unknown",
    eventGroup      varchar(64) default "",
    eventKey        varchar(64) default "",
    facility        varchar(8) default "unknown",
    severity        smallint default -1,
    priority        smallint default -1,
    summary         varchar(4096) not null,
    stateChange     timestamp,
    firstTime       timestamp,
    lastTime        timestamp,
    count           int default 1,
    acknowledged    bool default false,
    prodState       smallint default 0,
    manager         varchar(128) not null,
    agent           varchar(64) not null,
    DeviceClass     varchar(255) default "",
    Location        varchar(255) default "",
    Systems         varchar(255) default "",
    DeviceGroups    varchar(255) default "",
    PRIMARY KEY ( dedupid ),
    Index evididx (evid)
) ENGINE=MEMORY MAX_ROWS=20000;

CREATE TABLE IF NOT EXISTS history
(
    dedupid         varchar(255) not null,
    evid            char(36) not null,
    device          varchar(128) not null,
    ipAddress       char(15) default "",
    component       varchar(128) default "",
    eventClass      varchar(64) not null,
    eventGroup      varchar(64) default "",
    eventKey        varchar(64) default "",
    facility        varchar(8) default "",
    severity        smallint not null,
    priority        smallint not null,
    summary         varchar(4096) not null,
    stateChange     timestamp,
    firstTime       timestamp,
    lastTime        timestamp,
    count           int default 1,
    acknowledged    bool default false,
    prodState       smallint default 0,
    manager         varchar(128) not null,
    agent           varchar(64) not null,
    DeviceClass     varchar(255) default "",
    Location        varchar(255) default "",
    Systems         varchar(255) default "",
    DeviceGroups    varchar(255) default "",
    deletedTime     timestamp,
    PRIMARY KEY ( evid ),
    INDEX DateRange (firstTime, lastTime)
) ENGINE=INNODB;

CREATE TRIGGER status_delete BEFORE DELETE ON status
    FOR EACH ROW INSERT INTO history VALUES (
            OLD.dedupid,
            OLD.evid,
            OLD.device,
            OLD.ipAddress,
            OLD.component,
            OLD.eventClass,
            OLD.eventGroup,
            OLD.eventKey,
            OLD.facility,
            OLD.severity,
            OLD.priority,
            OLD.summary,
            OLD.stateChange,
            OLD.firstTime,
            OLD.lastTime,
            OLD.count,
            OLD.acknowledged,
            OLD.prodState,
            OLD.manager,
            OLD.agent,
            OLD.DeviceClass,
            OLD.Location,
            OLD.Systems,
            OLD.DeviceGroups,
            NULL
            );

CREATE TABLE IF NOT EXISTS log
(
    evid    char(128) not null,
    userName     varchar(64),
    ctime        timestamp,
    text         text
) ENGINE=INNODB;

CREATE TABLE IF NOT EXISTS detail
(
    evid   char(128) not null,
    sequence    int,
    name        varchar(255),
    value       varchar(255),
    PRIMARY KEY ( evid, name )
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
