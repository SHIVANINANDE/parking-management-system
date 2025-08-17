from elasticsearch import AsyncElasticsearch
from app.core.config import settings

class ElasticsearchClient:
    def __init__(self):
        self.client = None
    
    async def connect(self):
        self.client = AsyncElasticsearch(
            [settings.ELASTICSEARCH_URL],
            verify_certs=False
        )
        return self.client
    
    async def disconnect(self):
        if self.client:
            await self.client.close()
    
    async def index_document(self, index: str, document: dict, doc_id: str = None):
        return await self.client.index(
            index=index,
            id=doc_id,
            document=document
        )
    
    async def search(self, index: str, query: dict):
        return await self.client.search(
            index=index,
            body=query
        )
    
    async def delete_document(self, index: str, doc_id: str):
        return await self.client.delete(
            index=index,
            id=doc_id
        )
    
    async def create_index(self, index: str, mapping: dict):
        return await self.client.indices.create(
            index=index,
            body=mapping
        )

elasticsearch_client = ElasticsearchClient()