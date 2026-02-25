from app.core.neo4j import Neo4jClient

class KnowledgeExtractor:

    @staticmethod
    def create_knowledge(name, description):
        query = """
        MERGE (k:KnowledgePoint {name: $name})
        SET k.description = $description
        RETURN k
        """
        return Neo4jClient.execute(query, {
            "name": name,
            "description": description
        })

    @staticmethod
    def add_dependency(a, b):
        query = """
        MATCH (x:KnowledgePoint {name: $a})
        MATCH (y:KnowledgePoint {name: $b})
        MERGE (x)-[:DEPENDS_ON]->(y)
        """
        return Neo4jClient.execute(query, {"a": a, "b": b})
