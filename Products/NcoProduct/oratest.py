import DCOracle2

db=DCOracle2.connect('reporter/rep321@nclh')
c = db.cursor()
c.execute('select count(*) from reporter_status')
print c.fetchall()
