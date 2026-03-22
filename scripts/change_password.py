from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'neo4j'))
session = driver.session(database='system')
session.run("ALTER CURRENT USER SET PASSWORD FROM 'neo4j' TO 'xiangqi123'")
print('Password changed to xiangqi123!')
session.close()
driver.close()
