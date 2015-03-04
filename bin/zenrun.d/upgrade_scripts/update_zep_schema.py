
import Globals

from Products.ZenUtils.GlobalConfig import globalConfToDict

import os

def main():

	globalSettings = globalConfToDict()
	db_host = globalSettings.get('zep-host', '127.0.0.1')
	db_port = globalSettings.get('zep-port', '3306')
	zep_db_type = globalSettings.get('zodb-db-type', 'mysql')
	zep_db = globalSettings.get('zep-db', 'zenoss_zep')
	zep_user = globalSettings.get('zep-user', 'zenoss')
	zep_password = globalSettings.get('zep-password', 'zenoss')

	cmd = 'zeneventserver-create-db --dbhost={0} --dbport={1} --dbtype={2} --dbname={3} --dbuser={4} --dbpass={5} --update_schema_only'
	cmd = cmd.format (db_host, db_port, zep_db_type, zep_db, zep_user, zep_password)

	os.system(cmd)

if __name__ == '__main__':
	main()
