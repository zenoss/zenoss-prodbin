create database if not exists events;
use events;

create table if not exists status
(
    Identifier      varchar(255) not null,
    ServerSerial    int unsigned not null auto_increment unique,
    ServerName      varchar(128) default "events",
    Node            varchar(128),
    IpAddress       char(15),
    Component       varchar(255),
    System          varchar(255),
    DeviceClass     varchar(255),
    DeviceGroups    varchar(255),
    Manager         varchar(128),
    Agent           varchar(64),
    AlertGroup      varchar(64),
    AlertKey        varchar(64),
    Severity        smallint,
    Summary         varchar(255),
    StateChange     timestamp,
    FirstOccurrence timestamp,
    LastOccurrence  timestamp,
    EventType       int,    
    Count           int default 1,
    Class           int,
    Location        varchar(255),
    OwnerUID        int,
    OwnerGID        int,        
    Acknowledged    bool,
    ps_id           smallint default 0,
    primary key ( Identifier )
);

create table if not exists objclass
(
    Tag     int not null,
    Name    varchar(64),
    Icon    varchar(255),
    Menu    varchar(64),
    primary key    ( Tag )
);

create table if not exists resolutions
(
    KeyField        varchar(255) not null,
    Tag             int,
    Sequence        int,
    Title           varchar(64),
    Resolution1     varchar(255),
    Resolution2     varchar(255),
    Resolution3     varchar(255),
    Resolution4     varchar(255),
    primary key  ( KeyField )
);

create table if not exists journal
(
    KeyField     varchar(255) not null,
    Serial       int,
    UID          int,
    Chrono       datetime,
    Text1        varchar(255),
    Text2        varchar(255),
    Text3        varchar(255),
    Text4        varchar(255),
    Text5        varchar(255),
    Text6        varchar(255),
    Text7        varchar(255),
    Text8        varchar(255),
    Text9        varchar(255),
    Text10       varchar(255),
    Text11       varchar(255),
    Text12       varchar(255),
    Text13       varchar(255),
    Text14       varchar(255),
    Text15       varchar(255),
    Text16       varchar(255),
    primary key ( KeyField )
);

create table if not exists conversions
(
    KeyField    varchar(255) not null,
    Colname     varchar(255),
    Value       int,
    Conversion  varchar(255),
    primary key  ( KeyField )
);

create table if not exists col_visuals
(
    Colname         varchar(255) not null,
    Title           varchar(255),
    DefWidth        int,
    MaxWidth        int,
    TitleJustify    int,
    DataJustify     int,
    primary key ( Colname )
);


create table if not exists details
(
    KeyField   varchar(255) not null,
    Identifier varchar(255),
    AttrVal    int,
    Sequence   int,
    Name       varchar(255),
    Detail     varchar(255),
    primary key  ( KeyField )
);

create table if not exists colors 
(
    Severity        int not null,
    AckedRed        int,
    AckedGreen      int,
    AckedBlue       int,
    UnackedRed      int,
    UnackedGreen    int,
    UnackedBlue     int,
    primary key( Severity )
);
