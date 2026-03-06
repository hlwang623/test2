from neo4j import GraphDatabase

class Neo4jClient:
    driver = None

    @classmethod
    def connect(cls):
        cls.driver = GraphDatabase.driver(
            "bolt://localhost:7688",
            auth=("neo4j", "123456")
        )

    @classmethod
    def close(cls):
        if cls.driver:
            cls.driver.close()

    @classmethod
    def execute(cls, query, params=None):
        with cls.driver.session() as session:
            return session.run(query, params or {}).data()
