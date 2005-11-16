DROP DATABASE IF EXISTS events;
CREATE DATABASE events;
USE events;

CREATE TABLE IF NOT EXISTS status
(
    Identifier      varchar(255) not null,
    EventUuid       char(128) not null,
    Node            varchar(128) not null,
    IpAddress       char(15),
    Component       varchar(128) default "",
    Manager         varchar(128),
    Agent           varchar(64),
    AlertGroup      varchar(64) default "",
    AlertKey        varchar(64) default "",
    Severity        smallint not null,
    Summary         varchar(4096) not null,
    StateChange     timestamp,
    FirstOccurrence timestamp,
    LastOccurrence  timestamp,
    EventType       int,    
    Count           int default 1,
    Class           varchar(64) not null,
    OwnerUID        int default 65365,
    OwnerGID        int default 0,        
    Acknowledged    bool default false,
    DeviceClass     varchar(255) default "",
    Location        varchar(255) default "",
    Systems         varchar(255) default "",
    DeviceGroups    varchar(255) default "",
    ProdState       smallint default 0,
    PRIMARY KEY ( Identifier ),
    Index UuidIdx (EventUuid)
) ENGINE=MEMORY MAX_ROWS=20000;

CREATE TABLE IF NOT EXISTS history
(
    Identifier      varchar(255) not null,
    EventUuid       char(128) not null,
    Node            varchar(128),
    IpAddress       char(15),
    Component       varchar(128),
    Manager         varchar(128),
    Agent           varchar(64),
    AlertGroup      varchar(64),
    AlertKey        varchar(64),
    Severity        smallint,
    Summary         varchar(4096),
    StateChange     timestamp,
    FirstOccurrence timestamp,
    LastOccurrence  timestamp,
    EventType       int,    
    Count           int default 1,
    Class           varchar(64),
    OwnerUID        int,
    OwnerGID        int,        
    Acknowledged    bool default false,
    DeviceClass     varchar(255),
    Location        varchar(255),
    Systems         varchar(255),
    DeviceGroups    varchar(255),
    ProdState       smallint default 0,
    DeletedTime     timestamp,
    PRIMARY KEY ( EventUuid ),
    INDEX DateRange (FirstOccurrence, LastOccurrence)
) ENGINE=INNODB;

CREATE TRIGGER status_delete BEFORE DELETE ON status
    FOR EACH ROW INSERT INTO history VALUES (
            OLD.Identifier,
            OLD.EventUuid,
            OLD.Node,
            OLD.IpAddress,
            OLD.Component,
            OLD.Manager,
            OLD.Agent,
            OLD.AlertGroup,
            OLD.AlertKey,
            OLD.Severity,
            OLD.Summary,
            OLD.StateChange,
            OLD.FirstOccurrence,
            OLD.LastOccurrence,
            OLD.EventType,
            OLD.Count,
            OLD.Class,
            OLD.OwnerUID,
            OLD.OwnerGID,
            OLD.Acknowledged,
            OLD.DeviceClass,
            OLD.Location,
            OLD.Systems,
            OLD.DeviceGroups,
            OLD.ProdState,
            NULL
            );

CREATE TABLE IF NOT EXISTS journal
(
    EventUuid    char(128) not null,
    UserName     varchar(64),
    CTime        timestamp,
    Text         text
) ENGINE=INNODB;

CREATE TABLE IF NOT EXISTS details
(
    EventUuid   char(128) not null,
    AttrVal     int,
    Sequence    int,
    Name        varchar(255),
    Detail      varchar(255)
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
