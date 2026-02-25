from app.core.neo4j import Neo4jClient

class TreeKGBuilder:

    @staticmethod
    def create_chapter(name):
        query = """
        MERGE (c:Chapter {name: $name})
        RETURN c
        """
        return Neo4jClient.execute(query, {"name": name})

    @staticmethod
    def create_section(name, chapter):
        query = """
        MATCH (c:Chapter {name: $chapter})
        MERGE (s:Section {name: $name})
        MERGE (s)-[:PART_OF]->(c)
        RETURN s
        """
        return Neo4jClient.execute(query, {"name": name, "chapter": chapter})
