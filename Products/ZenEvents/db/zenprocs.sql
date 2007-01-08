
DROP PROCEDURE IF EXISTS age_events;
DELIMITER //
CREATE PROCEDURE age_events(IN hours INT, IN sev INT)
BEGIN
    DELETE FROM status where
     StateChange < DATE_SUB(NOW(), INTERVAL hours HOUR) and severity < sev;
END;//
DELIMITER ;


DROP PROCEDURE IF EXISTS clean_history;
DELIMITER //
CREATE PROCEDURE clean_history(IN months INT)
BEGIN
    DELETE h,j,d FROM history h
        LEFT JOIN log j ON h.evid = j.evid 
        LEFT JOIN detail d ON h.evid = d.evid
        WHERE StateChange < DATE_SUB(NOW(), INTERVAL months MONTH);
END;//
DELIMITER ;
