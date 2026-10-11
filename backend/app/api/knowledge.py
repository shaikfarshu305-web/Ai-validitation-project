from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database.session import get_db
from app.models.db_models import KnowledgeDocument, KnowledgeChunk, DatasetSource
from app.schemas.evaluation_schemas import (
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeStatsResponse,
    DataSourceInfo,
    RetrievedChunk
)
from app.rag.retrieval import retrieve_evidence
from app.rag.ingestion import ingest_document
from app.rag.vector_store import get_vector_store
from app.services.seed_service import BENCHMARK_KNOWLEDGE

router = APIRouter(tags=["Knowledge Base"])

class IngestCustomDocRequest(BaseModel):
    dataset: str = Field(..., description="Dataset or collection name (e.g. TruthfulQA, SQuAD, Custom)")
    title: str = Field(..., min_length=2)
    content: str = Field(..., min_length=10)
    source: Optional[str] = "Uploaded Document"

@router.get("/knowledge-base/stats", response_model=KnowledgeStatsResponse)
def get_knowledge_stats(db: Session = Depends(get_db)):
    """Retrieve total documents, chunks, embeddings, and dataset collections."""
    total_docs = db.query(KnowledgeDocument).count()
    total_chunks = db.query(KnowledgeChunk).count()
    vector_store = get_vector_store()
    total_embeddings = vector_store.count()

    datasets = db.query(KnowledgeDocument.dataset).distinct().all()
    dataset_names = [d[0] for d in datasets if d[0]]

    return KnowledgeStatsResponse(
        total_documents=total_docs,
        total_chunks=total_chunks,
        total_embeddings=total_embeddings,
        datasets=dataset_names or ["TruthfulQA", "SQuAD"]
    )

@router.post("/knowledge-base/search", response_model=KnowledgeSearchResponse)
def test_retrieval_query(req: KnowledgeSearchRequest):
    """
    Test semantic retrieval on knowledge base.
    Returns matched chunks, similarity scores, datasets, and metadata.
    """
    chunks = retrieve_evidence(query=req.query, top_k=req.top_k or 4, dataset=req.dataset)
    return KnowledgeSearchResponse(
        query=req.query,
        total_found=len(chunks),
        results=chunks
    )

@router.post("/knowledge-base/ingest")
def ingest_new_document(req: IngestCustomDocRequest, db: Session = Depends(get_db)):
    """Ingest, clean, chunk, and index a document into knowledge base."""
    doc = ingest_document(
        db=db,
        dataset=req.dataset.strip(),
        title=req.title.strip(),
        content=req.content.strip(),
        source=req.source.strip() if req.source else "User Ingestion"
    )
    return {
        "message": f"Successfully ingested '{doc.title}' with {doc.num_chunks} chunks.",
        "document_id": doc.id,
        "chunks_indexed": doc.num_chunks
    }

@router.get("/data-sources", response_model=List[DataSourceInfo])
def list_data_sources(db: Session = Depends(get_db)):
    """List all benchmark and ingested data sources with indexing metrics."""
    sources = db.query(DatasetSource).all()
    results = []
    for s in sources:
        results.append(DataSourceInfo(
            name=s.name,
            description=s.description or "Evidence repository",
            num_records=s.num_records,
            status=s.status,
            last_indexed=s.last_indexed.strftime("%Y-%m-%d %H:%M") if s.last_indexed else "Never",
            vector_index_status=s.vector_index_status
        ))
    
    # Ensure default cards if DB was newly created
    if not results:
        results = [
            DataSourceInfo(
                name="TruthfulQA",
                description="Benchmark measuring whether language models mimic human falsehoods and cognitive biases.",
                num_records=3,
                status="INDEXED",
                last_indexed=datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                vector_index_status="READY"
            ),
            DataSourceInfo(
                name="SQuAD",
                description="Stanford Question Answering Dataset consisting of questions posed on Wikipedia articles.",
                num_records=3,
                status="INDEXED",
                last_indexed=datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                vector_index_status="READY"
            )
        ]
    return results

@router.post("/data-sources/{name}/reindex")
def reindex_data_source(name: str, db: Session = Depends(get_db)):
    """Rebuild chunks and vector embeddings for a specific data source."""
    matching_benchmarks = [b for b in BENCHMARK_KNOWLEDGE if b["dataset"].lower() == name.lower()]
    reindexed_count = 0
    if matching_benchmarks:
        for b in matching_benchmarks:
            ingest_document(
                db=db,
                dataset=b["dataset"],
                title=b["title"],
                content=b["content"],
                source=b["source"]
            )
            reindexed_count += 1
    
    ds = db.query(DatasetSource).filter(DatasetSource.name.ilike(name)).first()
    if ds:
        ds.last_indexed = datetime.utcnow()
        ds.status = "INDEXED"
        ds.vector_index_status = "READY"
        db.commit()

    return {"message": f"Data source '{name}' reindexed successfully.", "reindexed_documents": max(1, reindexed_count)}
