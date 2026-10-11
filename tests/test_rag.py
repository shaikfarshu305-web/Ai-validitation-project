import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.session import Base
from app.rag.chunking import clean_text, chunk_text
from app.rag.embeddings import embedder
from app.rag.ingestion import rebuild_vector_index
from app.rag.vector_store import MemoryVectorStore, get_vector_store
from app.rag.retrieval import retrieve_evidence
from app.rag.vector_store import MemoryVectorStore
from app.services.seed_service import seed_benchmark_knowledge
from app.models.db_models import KnowledgeChunk, KnowledgeDocument

def test_chunking_and_cleaning():
    raw_text = "   This is a   test text with \r\n line breaks and tabs.   "
    cleaned = clean_text(raw_text)
    assert "\r" not in cleaned
    assert "  " not in cleaned

    long_text = "Sentence one. " * 30
    chunks = chunk_text(long_text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) > 0

def test_semantic_embeddings():
    vec1 = embedder.embed_text("Astronomy and planetary orbits")
    vec2 = embedder.embed_text("Planetary orbits and astronomy")
    vec3 = embedder.embed_text("Culinary baking recipes and pastry cakes")
    
    assert len(vec1) == 128
    sim_12 = float(vec1 @ vec2)
    sim_13 = float(vec1 @ vec3)
    # Cosine similarity between related texts should be substantially higher than unrelated
    assert sim_12 > sim_13

def test_vector_store_and_retrieval():
    vstore = get_vector_store()
    texts = [
        {"chunk_id": "test-1", "dataset": "TestSet", "title": "Quantum Physics", "chunk_text": "Quantum computers utilize qubits in superposition.", "source": "Unit Test", "metadata": {}},
        {"chunk_id": "test-2", "dataset": "TestSet", "title": "Baking Cakes", "chunk_text": "Flour and sugar are mixed to bake sponge cakes.", "source": "Unit Test", "metadata": {}}
    ]
    embs = embedder.embed_batch([t["chunk_text"] for t in texts])
    vstore.add_chunks(texts, embs)
    
    # Retrieve
    results = retrieve_evidence("quantum superposition qubits", top_k=1)
    assert len(results) >= 1
    assert "qubit" in results[0].text.lower()


def test_rebuild_vector_index_restores_persisted_chunks(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    memory_store = MemoryVectorStore(dimension=128)
    monkeypatch.setattr("app.rag.ingestion.get_vector_store", lambda: memory_store)
    document = KnowledgeDocument(
        id="persisted-document",
        dataset="TestSet",
        title="Database Keys",
        source="Regression Test",
        content="A primary key uniquely identifies each record in a database table.",
        num_chunks=1,
    )
    db.add(document)
    db.add(KnowledgeChunk(
        id="persisted-chunk",
        document_id=document.id,
        dataset=document.dataset,
        chunk_index=0,
        chunk_text=document.content,
        metadata_json={},
    ))
    db.commit()

    try:
        indexed_count = rebuild_vector_index(db)
        results = memory_store.search(embedder.embed_text("primary key database record"), top_k=1)

        assert indexed_count == 1
        assert memory_store.count() == 1
        assert results[0][0]["chunk_text"] == document.content
    finally:
        db.close()
        engine.dispose()


def test_retrieval_does_not_return_unrelated_chunks(monkeypatch):
    memory_store = MemoryVectorStore(dimension=128)
    chunks = [{
        "chunk_id": "seasons-chunk",
        "dataset": "TestSet",
        "title": "Earth's Orbital Mechanics and Causes of Seasons",
        "chunk_text": "Earth experiences seasons because its axial tilt changes sunlight and daylight.",
        "source": "Regression Test",
        "metadata": {},
    }]
    memory_store.add_chunks(chunks, embedder.embed_batch([chunks[0]["chunk_text"]]))
    monkeypatch.setattr("app.rag.retrieval.get_vector_store", lambda: memory_store)

    unrelated = retrieve_evidence("What is a primary key?", top_k=1, min_score=0.0)
    related = retrieve_evidence("Why does Earth have seasons?", top_k=1, min_score=0.0)

    assert unrelated == []
    assert len(related) == 1


def test_benchmark_knowledge_is_added_incrementally_and_retrievable(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    memory_store = MemoryVectorStore(dimension=128)
    monkeypatch.setattr("app.rag.ingestion.get_vector_store", lambda: memory_store)
    monkeypatch.setattr("app.rag.retrieval.get_vector_store", lambda: memory_store)

    try:
        first_added = seed_benchmark_knowledge(db)
        second_added = seed_benchmark_knowledge(db)
        results = retrieve_evidence("primary key uniquely identifies database table records", top_k=4)

        assert first_added > 0
        assert second_added == 0
        assert results
        assert any("primary key" in chunk.text.lower() for chunk in results)
    finally:
        db.close()
        engine.dispose()
