DROP DATABASE events;
CREATE DATABASE IF NOT EXISTS events;
USE events;

CREATE TABLE IF NOT EXISTS status
(
    Identifier      varchar(255) not null,
    ServerSerial    serial,
    ServerName      varchar(128) default "events",
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
    ps_id           smallint default 0,
    PRIMARY KEY ( Identifier )
) ENGINE=MEMORY MAX_ROWS=20000;

CREATE TABLE IF NOT EXISTS history
(
    Identifier      varchar(255) not null,
    ServerSerial    bigint unsigned not null,
    ServerName      varchar(128),
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
    ps_id           smallint default 0,
    DeletedTime     timestamp,
    PRIMARY KEY ( ServerSerial, ServerName ),
    INDEX DateRange (FirstOccurrence, LastOccurrence)
) ENGINE=INNODB;

--DROP TRIGGER IF EXISTS status_delete;
CREATE TRIGGER status_delete BEFORE DELETE ON status
    FOR EACH ROW INSERT INTO history VALUES (
            OLD.Identifier,
            OLD.ServerSerial,
            OLD.ServerName,
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
            OLD.ps_id,
            NULL
            );

CREATE TABLE IF NOT EXISTS manage_ctrl
(
    Quit        boolean default false,
    LoopTime    int default 60
);

CREATE TABLE IF NOT EXISTS test
(
    inserttime   timestamp 
);

DROP PROCEDURE IF EXISTS manage_loop;
DELIMITER //
CREATE PROCEDURE manage_loop()
BEGIN
    DECLARE done boolean DEFAULT false;
    DECLARE cycletime INT DEFAULT 60;

    SELECT LoopTime INTO done from manage_ctrl limit 1;
    WHILE NOT done DO
        INSERT INTO test VALUES (NULL);
        SELECT SLEEP(cycletime); 
        SELECT Quit INTO done from manage_ctrl limit 1;
    END WHILE;
END;//
DELIMITER ;

DROP PROCEDURE IF EXISTS close_events;
DELIMITER //
CREATE PROCEDURE close_events()
BEGIN
    DECLARE done boolean DEFAULT false;
    DECLARE evnode, evcomp, evclass, evkey varchar(128) default "";
    DECLARE clears CURSOR FOR 
        SELECT Node, Component, Class, AlertKey FROM status WHERE Severity = 0;
    DECLARE CONTINUE HANDLER FOR SQLSTATE '02000' SET done = true;
    OPEN clears;
    REPEAT 
        FETCH clears INTO evnode, evcomp, evclass, evkey;
        DELETE FROM status where 
            Node = evnode AND Class = evclass
            AND Component = evcomp AND AlertKey = evkey;
    UNTIL done END REPEAT; 
    CLOSE clears;
END;//
DELIMITER ;
   

DROP PROCEDURE IF EXISTS clean_old_events;
DELIMITER //
CREATE PROCEDURE clean_old_events()
BEGIN
    DELETE FROM status where 
        DATE_ADD(StateChange, INTERVAL 4 HOUR) < NOW();   
    DELETE FROM history where 
        DATE_ADD(StateChange, INTERVAL 3 MONTH) < NOW();   
END;//
DELIMITER ;
   

CREATE TABLE IF NOT EXISTS journal
(
    KeyField     varchar(255) not null,
    Serial       int,
    UID          int,
    Chrono       datetime,
    Text         text,
    PRIMARY KEY ( KeyField )
) ENGINE=INNODB;

CREATE TABLE IF NOT EXISTS details
(
    KeyField   varchar(255) not null,
    Identifier varchar(255),
    AttrVal    int,
    Sequence   int,
    Name       varchar(255),
    Detail     varchar(255),
    PRIMARY KEY  ( KeyField )
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
