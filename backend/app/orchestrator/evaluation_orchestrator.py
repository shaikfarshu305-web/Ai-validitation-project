"""
AI Validation Evaluation Orchestrator — Optimized Parallel Architecture
==================================================================

Execution model (AFTER optimization):

   Input
     │
     ▼
  RAG Retrieval (single call, result shared with all agents)
     │
     ├─────────────────────────────────────────────────────┐
     │                    asyncio.gather                    │
     ▼             ▼              ▼               ▼         │
 Relevance     Accuracy    Hallucination    Completeness    │
  Agent         Agent          Agent           Agent        │
     │             │              │               │         │
     └─────────────┴──────────────┴───────────────┘         │
                           │                                 │
                           ▼                                 │
                     Verdict Agent                           │
                           │                                 │
                           ▼                                 │
                   Single DB Write (batched)◄────────────────┘

Performance wins:
  • 4 agents run in parallel  → total ≈ slowest agent (not sum)
  • RAG retrieved once        → shared across all agents
  • 1 DB commit at the end    → not 5 sequential commits
  • LLM uses async httpx      → non-blocking event loop
  • Embeddings cached         → no repeated hashing
  • Retrieval cached (5 min)  → near-instant for repeated queries
"""

import uuid
import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from app.rag.retrieval import retrieve_evidence
from app.agents.relevance_agent import RelevanceJudgeAgent
from app.agents.accuracy_agent import AccuracyJudgeAgent
from app.agents.hallucination_agent import HallucinationDetectionAgent
from app.agents.completeness_agent import CompletenessJudgeAgent
from app.agents.verdict_agent import VerdictAgent
from app.models.db_models import (
    EvaluationSubmission,
    EvaluationResult,
    AgentEvaluation,
    EvaluationHistory,
)
from app.schemas.evaluation_schemas import (
    SingleEvaluationRequest,
    RetrievedChunk,
)

logger = logging.getLogger(__name__)

# Thread pool for running sync agent compute in parallel without blocking event loop
_AGENT_THREAD_POOL = ThreadPoolExecutor(max_workers=8, thread_name_prefix="ai-validation-agent")


class EvaluationOrchestrator:
    """
    Coordinates end-to-end AI response verification with maximum parallelism.
    """

    def __init__(self):
        self.relevance_agent = RelevanceJudgeAgent()
        self.accuracy_agent = AccuracyJudgeAgent()
        self.hallucination_agent = HallucinationDetectionAgent()
        self.completeness_agent = CompletenessJudgeAgent()
        self.verdict_agent = VerdictAgent()

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC: Synchronous entry point (called by FastAPI sync endpoints)
    # Uses asyncio.run() internally to get true parallel execution
    # ─────────────────────────────────────────────────────────────────────────

    def run_evaluation(
        self,
        db: Session,
        req: SingleEvaluationRequest,
        custom_weights: Optional[Dict[str, float]] = None,
        custom_thresholds: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper — runs the async pipeline and returns result dict.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an async context — run in thread pool
                import concurrent.futures
                future = _AGENT_THREAD_POOL.submit(
                    asyncio.run,
                    self._async_pipeline(db, req, custom_weights, custom_thresholds),
                )
                return future.result(timeout=120)
            else:
                return loop.run_until_complete(
                    self._async_pipeline(db, req, custom_weights, custom_thresholds)
                )
        except RuntimeError:
            return asyncio.run(
                self._async_pipeline(db, req, custom_weights, custom_thresholds)
            )

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC: Async entry point (called by FastAPI async endpoints & SSE)
    # ─────────────────────────────────────────────────────────────────────────

    async def run_evaluation_async(
        self,
        db: Session,
        req: SingleEvaluationRequest,
        custom_weights: Optional[Dict[str, float]] = None,
        custom_thresholds: Optional[Dict[str, float]] = None,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        Async evaluation pipeline with optional SSE progress callback.
        progress_callback: async callable(stage: str, status: str, detail: str)
        """
        return await self._async_pipeline(
            db, req, custom_weights, custom_thresholds, progress_callback
        )

    # ─────────────────────────────────────────────────────────────────────────
    # CORE ASYNC PIPELINE
    # ─────────────────────────────────────────────────────────────────────────

    async def _async_pipeline(
        self,
        db: Session,
        req: SingleEvaluationRequest,
        custom_weights: Optional[Dict[str, float]],
        custom_thresholds: Optional[Dict[str, float]],
        progress_callback=None,
    ) -> Dict[str, Any]:
        eval_id = str(uuid.uuid4())
        wall_start = time.perf_counter()

        async def _progress(stage: str, status: str, detail: str = ""):
            if progress_callback:
                try:
                    await progress_callback(stage, status, detail)
                except Exception:
                    pass

        # ── Step 1: Create submission record (non-blocking write) ────────────
        submission = EvaluationSubmission(
            id=eval_id,
            question=req.question.strip(),
            ai_response=req.ai_response.strip(),
            reference_answer=req.reference_answer.strip() if req.reference_answer else None,
            source_information=req.source_information.strip() if req.source_information else None,
            status="PROCESSING",
            created_at=datetime.utcnow(),
        )
        db.add(submission)
        db.flush()  # flush only — no commit yet

        await _progress("input", "complete", "Input validated and staged")

        # ── Step 2: RAG Retrieval — SINGLE call, shared with all agents ──────
        t_rag_start = time.perf_counter()
        await _progress("retrieval", "running", "Searching knowledge base")

        loop = asyncio.get_event_loop()
        search_query = req.question
        retrieved_evidence: List[RetrievedChunk] = await loop.run_in_executor(
            _AGENT_THREAD_POOL,
            lambda: retrieve_evidence(search_query, top_k=settings_top_k()),
        )
        t_rag = time.perf_counter() - t_rag_start
        await _progress("retrieval", "complete", f"Retrieved {len(retrieved_evidence)} chunks in {t_rag*1000:.0f}ms")

        # ── Step 3: Parallel Agent Execution ─────────────────────────────────
        await _progress("agents", "running", "Launching 4 parallel judge agents")

        t_agents_start = time.perf_counter()

        rel_task = loop.run_in_executor(
            _AGENT_THREAD_POOL,
            lambda: self._timed_agent_call(
                "RelevanceJudge",
                lambda: self.relevance_agent.evaluate(
                    req.question,
                    req.ai_response,
                    reference_answer=req.reference_answer,
                    source_information=req.source_information,
                    retrieved_evidence=retrieved_evidence,
                ),
            ),
        )
        acc_task = loop.run_in_executor(
            _AGENT_THREAD_POOL,
            lambda: self._timed_agent_call(
                "AccuracyJudge",
                lambda: self.accuracy_agent.evaluate(
                    req.question,
                    req.ai_response,
                    reference_answer=req.reference_answer,
                    source_information=req.source_information,
                    retrieved_evidence=retrieved_evidence,
                ),
            ),
        )
        hal_task = loop.run_in_executor(
            _AGENT_THREAD_POOL,
            lambda: self._timed_agent_call(
                "HallucinationDetector",
                lambda: self.hallucination_agent.evaluate(
                    req.question,
                    req.ai_response,
                    reference_answer=req.reference_answer,
                    source_information=req.source_information,
                    retrieved_evidence=retrieved_evidence,
                ),
            ),
        )
        comp_task = loop.run_in_executor(
            _AGENT_THREAD_POOL,
            lambda: self._timed_agent_call(
                "CompletenessJudge",
                lambda: self.completeness_agent.evaluate(
                    req.question,
                    req.ai_response,
                    reference_answer=req.reference_answer,
                    retrieved_evidence=retrieved_evidence,
                ),
            ),
        )

        # Run all 4 agents concurrently — total time ≈ slowest agent
        rel_result, acc_result, hal_result, comp_result = await asyncio.gather(
            rel_task, acc_task, hal_task, comp_task,
            return_exceptions=True,
        )

        t_agents = time.perf_counter() - t_agents_start

        # Handle any exceptions from gather
        rel_result = self._handle_exception(rel_result, "RelevanceJudge")
        acc_result = self._handle_exception(acc_result, "AccuracyJudge")
        hal_result = self._handle_exception(hal_result, "HallucinationDetector")
        comp_result = self._handle_exception(comp_result, "CompletenessJudge")

        rel_output, rel_time = rel_result
        acc_output, acc_time = acc_result
        hal_output, hal_time = hal_result
        comp_output, comp_time = comp_result

        failed_agents = [
            name for name, output in (
                ("RelevanceJudge", rel_output),
                ("AccuracyJudge", acc_output),
                ("HallucinationDetector", hal_output),
                ("CompletenessJudge", comp_output),
            ) if output.get("status") in {"FAILED", "TIMEOUT"}
        ]
        if failed_agents:
            submission.status = "FAILED"
            db.commit()
            raise RuntimeError(f"Evaluation incomplete; failed agents: {', '.join(failed_agents)}")

        await _progress("agents", "complete", f"All 4 agents completed in {t_agents*1000:.0f}ms")

        # ── Step 4: Verdict ───────────────────────────────────────────────────
        await _progress("verdict", "running", "Synthesizing weighted verdict")

        t_verdict_start = time.perf_counter()
        verdict_output, verdict_time = self._timed_agent_call(
            "VerdictAgent",
            lambda: self.verdict_agent.evaluate(
                relevance_data=rel_output,
                accuracy_data=acc_output,
                hallucination_data=hal_output,
                completeness_data=comp_output,
                custom_weights=custom_weights,
                custom_thresholds=custom_thresholds,
            ),
        )
        t_verdict = time.perf_counter() - t_verdict_start

        if verdict_output.get("status") in {"FAILED", "TIMEOUT"}:
            submission.status = "FAILED"
            db.commit()
            raise RuntimeError("Evaluation incomplete; VerdictAgent failed")

        overall_score = verdict_output["overall_score"]
        verdict_status = verdict_output["verdict"]

        t_total = time.perf_counter() - wall_start

        # ── Performance metrics ───────────────────────────────────────────────
        perf_metrics = {
            "total_ms": round(t_total * 1000, 1),
            "rag_ms": round(t_rag * 1000, 1),
            "agents_parallel_ms": round(t_agents * 1000, 1),
            "relevance_ms": rel_time,
            "accuracy_ms": acc_time,
            "hallucination_ms": hal_time,
            "completeness_ms": comp_time,
            "verdict_ms": round(t_verdict * 1000, 1),
        }

        await _progress("verdict", "complete", f"Verdict: {verdict_status} ({overall_score:.1f})")

        # ── Step 5: Single batched DB write (all records at once) ─────────────
        result_record = EvaluationResult(
            id=str(uuid.uuid4()),
            evaluation_id=eval_id,
            relevance_score=float(rel_output.get("score", 0.0)),
            accuracy_score=float(acc_output.get("score", 0.0)),
            hallucination_score=float(hal_output.get("hallucination_score", 0.0)),
            completeness_score=float(comp_output.get("score", 0.0)),
            overall_score=overall_score,
            verdict=verdict_status,
            summary=verdict_output.get("summary", ""),
            major_issues=verdict_output.get("major_issues", []),
            recommendations=verdict_output.get("recommendations", []),
            raw_metrics={
                "dimension_scores": verdict_output.get("dimension_scores", {}),
                "relevance": rel_output,
                "accuracy": acc_output,
                "hallucination": hal_output,
                "completeness": comp_output,
                "verdict": verdict_output,
                "performance": perf_metrics,
            },
            retrieved_evidence=[c.model_dump() for c in retrieved_evidence],
            created_at=datetime.utcnow(),
        )
        db.add(result_record)

        # Agent audit logs (batched)
        for agent_name, output, exec_ms in [
            ("RelevanceJudge", rel_output, rel_time),
            ("AccuracyJudge", acc_output, acc_time),
            ("HallucinationDetector", hal_output, hal_time),
            ("CompletenessJudge", comp_output, comp_time),
            ("VerdictAgent", verdict_output, round(t_verdict * 1000, 1)),
        ]:
            db.add(AgentEvaluation(
                id=str(uuid.uuid4()),
                evaluation_id=eval_id,
                agent_name=agent_name,
                score=output.get("score") or output.get("overall_score") or output.get("hallucination_score"),
                reasoning=output.get("reasoning") or output.get("summary", ""),
                evidence=output.get("supporting_evidence") or output.get("flagged_claims") or [],
                metadata_info={"execution_time_ms": exec_ms},
                execution_time_ms=exec_ms,
                status=output.get("status", "SUCCESS"),
                created_at=datetime.utcnow(),
            ))

        db.add(EvaluationHistory(
            id=str(uuid.uuid4()),
            evaluation_id=eval_id,
            question_preview=req.question[:120],
            overall_score=overall_score,
            verdict=verdict_status,
            hallucination_status=hal_output.get("hallucination_status", "LOW"),
            created_at=datetime.utcnow(),
        ))

        submission.status = "COMPLETED"
        db.commit()  # Single commit for everything

        await _progress("complete", "complete", f"Done in {t_total*1000:.0f}ms")

        logger.info(
            f"[AI_VALIDATION] eval={eval_id} | total={perf_metrics['total_ms']}ms "
            f"| rag={perf_metrics['rag_ms']}ms "
            f"| agents_parallel={perf_metrics['agents_parallel_ms']}ms "
            f"| verdict={perf_metrics['verdict_ms']}ms"
        )

        return {
            "id": eval_id,
            "question": req.question,
            "ai_response": req.ai_response,
            "reference_answer": req.reference_answer,
            "source_information": req.source_information,
            "created_at": submission.created_at.isoformat(),
            "status": "COMPLETED",
            "relevance_score": float(rel_output.get("score", 0.0)),
            "accuracy_score": float(acc_output.get("score", 0.0)),
            "hallucination_score": float(hal_output.get("hallucination_score", 0.0)),
            "hallucination_percentage": float(
                verdict_output.get("dimension_scores", {}).get("hallucination_percentage", 0.0)
            ),
            "completeness_score": float(comp_output.get("score", 0.0)),
            "overall_score": overall_score,
            "verdict": verdict_status,
            "summary": verdict_output.get("summary", ""),
            "major_issues": verdict_output.get("major_issues", []),
            "recommendations": verdict_output.get("recommendations", []),
            "relevance_details": rel_output,
            "accuracy_details": acc_output,
            "hallucination_details": hal_output,
            "completeness_details": comp_output,
            "verdict_details": verdict_output,
            "retrieved_evidence": retrieved_evidence,
            "performance_metrics": perf_metrics,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _timed_agent_call(self, agent_name: str, fn):
        """Run an agent function, measure time, apply error containment."""
        t0 = time.perf_counter()
        try:
            output = fn()
            exec_ms = round((time.perf_counter() - t0) * 1000, 1)
            output["_exec_ms"] = exec_ms
            return output, exec_ms
        except Exception as e:
            exec_ms = round((time.perf_counter() - t0) * 1000, 1)
            logger.error(f"Agent {agent_name} error: {e}", exc_info=True)
            fallback = self._make_fallback(agent_name, str(e))
            fallback["_exec_ms"] = exec_ms
            fallback["status"] = "FAILED"
            return fallback, exec_ms

    def _handle_exception(self, result, agent_name: str):
        """Handle exceptions returned by asyncio.gather."""
        if isinstance(result, Exception):
            logger.error(f"Agent {agent_name} gather exception: {result}")
            fb = self._make_fallback(agent_name, str(result))
            return fb, 0.0
        return result

    def _make_fallback(self, agent_name: str, error: str) -> Dict[str, Any]:
        logger.error("Evaluation cannot be completed because %s failed: %s", agent_name, error)
        return {"status": "FAILED", "error": error, "reasoning": f"{agent_name} failed: {error}"}


def settings_top_k() -> int:
    """Get configured top_k from settings."""
    from app.config import settings
    return settings.DEFAULT_RETRIEVAL_TOP_K


# Module-level singleton
orchestrator = EvaluationOrchestrator()
