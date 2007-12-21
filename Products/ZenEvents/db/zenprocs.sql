
DROP PROCEDURE IF EXISTS age_events;
DELIMITER //
CREATE PROCEDURE age_events(IN hours INT, IN sev INT)
BEGIN
    DELETE FROM status where
     StateChange < DATE_SUB(NOW(), INTERVAL hours HOUR) and severity < sev;
END;//
DELIMITER ;
