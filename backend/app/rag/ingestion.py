import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.rag.chunking import clean_text, chunk_text
from app.rag.embeddings import embedder
from app.rag.vector_store import get_vector_store
from app.models.db_models import KnowledgeDocument, KnowledgeChunk, DatasetSource
from app.config import settings

def ingest_document(
    db: Session,
    dataset: str,
    title: str,
    content: str,
    source: Optional[str] = "Uploaded Document",
    metadata: Optional[Dict[str, Any]] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
) -> KnowledgeDocument:
    """
    Ingest a document into SQLite and the Vector Database:
    Dataset -> Cleaning -> Chunking -> Embedding -> Vector DB + SQL
    """
    c_size = chunk_size or settings.DEFAULT_CHUNK_SIZE
    c_overlap = chunk_overlap or settings.DEFAULT_CHUNK_OVERLAP
    cleaned = clean_text(content)

    doc_id = str(uuid.uuid4())
    doc = KnowledgeDocument(
        id=doc_id,
        dataset=dataset,
        title=title,
        source=source,
        content=cleaned,
        num_chunks=0
    )
    db.add(doc)
    db.flush()

    raw_chunks = chunk_text(cleaned, chunk_size=c_size, chunk_overlap=c_overlap)
    if not raw_chunks:
        raw_chunks = [cleaned] if cleaned else []

    if raw_chunks:
        embeddings = embedder.embed_batch(raw_chunks)
        vector_chunks_meta = []

        for idx, (chunk_str, emb) in enumerate(zip(raw_chunks, embeddings)):
            chunk_id = str(uuid.uuid4())
            chunk_meta = {
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "dataset": dataset,
                "title": title,
                "source": source,
                "chunk_index": idx,
                "chunk_text": chunk_str,
                "metadata": metadata or {}
            }
            vector_chunks_meta.append(chunk_meta)

            db_chunk = KnowledgeChunk(
                id=chunk_id,
                document_id=doc_id,
                dataset=dataset,
                chunk_index=idx,
                chunk_text=chunk_str,
                metadata_json=metadata or {}
            )
            db.add(db_chunk)

        # Index in Vector Store
        vector_store = get_vector_store()
        vector_ids = vector_store.add_chunks(vector_chunks_meta, embeddings)

        doc.num_chunks = len(raw_chunks)

    # Update DatasetSource stats
    ds = db.query(DatasetSource).filter(DatasetSource.name == dataset).first()
    if ds:
        total_docs = db.query(KnowledgeDocument).filter(KnowledgeDocument.dataset == dataset).count()
        ds.num_records = total_docs
        ds.last_indexed = datetime.utcnow()
        ds.status = "INDEXED"
        ds.vector_index_status = "READY"
    else:
        new_ds = DatasetSource(
            id=str(uuid.uuid4()),
            name=dataset,
            description=f"Evidence collection for {dataset}",
            num_records=1,
            status="INDEXED",
            last_indexed=datetime.utcnow(),
            vector_index_status="READY"
        )
        db.add(new_ds)

    db.commit()
    db.refresh(doc)
    return doc


def rebuild_vector_index(db: Session) -> int:
    """Restore the process-local vector index from persisted knowledge chunks."""
    rows = (
        db.query(KnowledgeChunk, KnowledgeDocument)
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .order_by(KnowledgeChunk.document_id, KnowledgeChunk.chunk_index)
        .all()
    )
    vector_store = get_vector_store()
    vector_store.clear()
    if not rows:
        return 0

    chunks = []
    texts = []
    for chunk, document in rows:
        texts.append(chunk.chunk_text)
        chunks.append({
            "chunk_id": chunk.id,
            "document_id": document.id,
            "dataset": chunk.dataset,
            "title": document.title,
            "source": document.source,
            "chunk_index": chunk.chunk_index,
            "chunk_text": chunk.chunk_text,
            "metadata": chunk.metadata_json or {},
        })

    vector_store.add_chunks(chunks, embedder.embed_batch(texts))
    return len(chunks)
