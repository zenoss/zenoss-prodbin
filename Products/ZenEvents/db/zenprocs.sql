USE events;
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
    DELETE h,j,d FROM history h
        LEFT JOIN journal j ON h.EventUuid = j.EventUuid 
        LEFT JOIN details d ON h.EventUuid = d.EventUuid
        WHERE DATE_ADD(StateChange, INTERVAL 3 MONTH) < NOW();
END;//
DELIMITER ;
