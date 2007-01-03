
DROP PROCEDURE IF EXISTS clean_old_events;
DELIMITER //
CREATE PROCEDURE clean_old_events(IN hours INT, IN severity INT)
BEGIN
    DELETE FROM status where 
        DATE_ADD(StateChange, INTERVAL hours HOUR) < NOW() and severity < severity;   
END;//
DELIMITER ;


DROP PROCEDURE IF EXISTS clean_history_events;
DELIMITER //
CREATE PROCEDURE clean_history_events(IN months INT)
BEGIN
    DELETE h,j,d FROM history h
        LEFT JOIN log j ON h.evid = j.evid 
        LEFT JOIN detail d ON h.evid = d.evid
        WHERE DATE_ADD(StateChange, INTERVAL months MONTH) < NOW();
END;//
DELIMITER ;
