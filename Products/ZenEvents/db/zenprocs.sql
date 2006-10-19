DROP PROCEDURE IF EXISTS close_events;
DELIMITER //
CREATE PROCEDURE close_events()
BEGIN
    DECLARE done boolean DEFAULT false;
    DECLARE evnode, evcomp, evclass, evkey varchar(128) default "";
    DECLARE clears CURSOR FOR 
        SELECT device, component, eventClass, eventKey FROM status 
            WHERE Severity = 0;
    DECLARE CONTINUE HANDLER FOR SQLSTATE '02000' SET done = true;
    OPEN clears;
    REPEAT 
        FETCH clears INTO evnode, evcomp, evclass, evkey;
        DELETE FROM status where 
            device = evnode AND eventClass = evclass
            AND component = evcomp AND eventKey = evkey;
    UNTIL done END REPEAT; 
    CLOSE clears;
END;//
DELIMITER ;
   

DROP PROCEDURE IF EXISTS clean_old_events;
DELIMITER //
CREATE PROCEDURE clean_old_events()
BEGIN
    DELETE FROM status where 
        DATE_ADD(StateChange, INTERVAL 4 HOUR) < NOW() and severity < 4;   
--    DELETE h,j,d FROM history h
--        LEFT JOIN log j ON h.evid = j.evid 
--        LEFT JOIN detail d ON h.evid = d.evid
--        WHERE DATE_ADD(StateChange, INTERVAL 3 MONTH) < NOW();
END;//
DELIMITER ;
