
drop table event_history;
create table event_history (
    oid         integer unsigned,
    device      varchar(128),
    startdate   datetime,
    lastupdate  datetime,
    enddate     datetime,
    summary     text,
    severity    tinyint,
    classid     integer unsigned,
    monitor     varchar(128),
    monitorhost varchar(128),
    
); 
