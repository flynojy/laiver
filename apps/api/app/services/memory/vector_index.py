import hashlib
import math

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from app.core.config import get_settings
from app.utils.text import tokenize


class LocalHashEmbeddingProvider:
    def __init__(self, size: int) -> None:
        self.size = size

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.size
        for token in tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = digest[0] % self.size
            sign = 1.0 if digest[1] % 2 == 0 else -1.0
            weight = 1.0 + (digest[2] / 255.0)
            vector[index] += sign * weight
        norm = math.sqrt(sum(item * item for item in vector)) or 1.0
        return [item / norm for item in vector]


class QdrantMemoryIndex:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = QdrantClient(url=settings.qdrant_url, check_compatibility=False)
        self.collection_name = settings.qdrant_collection
        self.vector_size = settings.memory_vector_size

    def ensure_collection(self) -> bool:
        try:
            collections = self.client.get_collections().collections
            if not any(item.name == self.collection_name for item in collections):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qdrant_models.VectorParams(
                        size=self.vector_size,
                        distance=qdrant_models.Distance.COSINE,
                    ),
                )
            return True
        except Exception:
            return False

    def upsert(self, memory_id: str, vector: list[float], payload: dict) -> bool:
        if not self.ensure_collection():
            return False
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[qdrant_models.PointStruct(id=memory_id, vector=vector, payload=payload)],
            )
            return True
        except Exception:
            return False

    def search(self, vector: list[float], user_id: str, persona_id: str | None, limit: int) -> list[str]:
        if not self.ensure_collection():
            return []

        filters = [
            qdrant_models.FieldCondition(
                key="user_id",
                match=qdrant_models.MatchValue(value=user_id),
            )
        ]
        if persona_id:
            filters.append(
                qdrant_models.FieldCondition(
                    key="persona_id",
                    match=qdrant_models.MatchValue(value=persona_id),
                )
            )
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                query_filter=qdrant_models.Filter(must=filters),
                limit=limit,
            )
            return [str(item.id) for item in results]
        except Exception:
            return []
