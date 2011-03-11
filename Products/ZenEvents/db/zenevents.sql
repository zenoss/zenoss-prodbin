CREATE TABLE IF NOT EXISTS heartbeat
(
    device          varchar(128) not null,
    component       varchar(128) default "",
    timeout         int default 0,
    lastTime        timestamp,
    PRIMARY KEY ( device,component )
) ENGINE=INNODB;
