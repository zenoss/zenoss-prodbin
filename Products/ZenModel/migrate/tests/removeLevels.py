with open('zenoss-resmgr-5.1.5-addEmergencyShutdownLevel.json', 'rb') as initial_file, \
     open('removeLevels.out', 'wb') as modified_file:

    lines = initial_file.readlines()
    for line in lines:
        if not '"EmergencyShutdown": 0' in line and not '"StartLevel": 0' in line:
            modified_file.write(line)


