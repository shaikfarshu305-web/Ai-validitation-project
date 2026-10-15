import time
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent
from app.agents.factual_consistency import assess_claims, assess_factual_consistency
from app.services.llm_service import llm_service
from app.schemas.evaluation_schemas import RetrievedChunk

class AccuracyJudgeAgent(BaseAgent):
    """
    Evaluates factual correctness against evidence hierarchy:
    1. Reference Answer (highest priority)
    2. User-provided Source Material
    3. RAG Retrieved Knowledge-Base Chunks
    Scale: 0 - 5.
    """
    def __init__(self):
        super().__init__("AccuracyJudge")

    def evaluate(
        self,
        question: str,
        ai_response: str,
        reference_answer: Optional[str] = None,
        source_information: Optional[str] = None,
        retrieved_evidence: Optional[List[RetrievedChunk]] = None
    ) -> Dict[str, Any]:
        start_time = time.time()

        # Build consolidated evidence text according to priority
        relevant_chunks = self.filter_relevant_chunks(question, reference_answer, retrieved_evidence)

        evidence_sections = []
        if reference_answer and reference_answer.strip():
            evidence_sections.append(f"[PRIORITY 1: GROUND TRUTH REFERENCE ANSWER]\n{reference_answer.strip()}")
        if source_information and source_information.strip():
            evidence_sections.append(f"[PRIORITY 2: USER SOURCE MATERIAL]\n{source_information.strip()}")
        if relevant_chunks:
            rag_texts = [f"Chunk ({c.dataset} - {c.title}, score: {c.similarity_score}): {c.text}" for c in relevant_chunks]
            evidence_sections.append("[PRIORITY 3: RAG KNOWLEDGE BASE EVIDENCE]\n" + "\n".join(rag_texts))

        evidence_str = "\n\n".join(evidence_sections) if evidence_sections else "No external reference provided."

        system_prompt = (
            "You are the Accuracy Judge Agent for the AI Response Validation system.\n"
            "Evaluate the factual accuracy of the AI response strictly against the provided evidence.\n"
            "Explicitly compare important claims to the reference answer. Topic similarity, fluency, and confidence do not prove correctness.\n"
            "Check changed names, dates, numbers, definitions, technical facts, contradictions, unsupported additions, and omissions.\n"
            "Include factual_consistency as CONSISTENT, PARTIALLY_CONSISTENT, CONTRADICTORY, or UNSUPPORTED.\n"
            "Hierarchy of truth: 1) Reference Answer > 2) User Source Material > 3) RAG Knowledge Base Chunks.\n"
            "Scale 0-100:\n"
            "90-100 = Fully accurate (all factual claims match verified evidence)\n"
            "80-89 = Mostly accurate (core facts are correct, minor immaterial nuance discrepancy)\n"
            "60-79 = Partially accurate (some correct assertions, but contains at least one noticeable factual error)\n"
            "30-59 = Significant inaccuracies (multiple claims contradicted or factually inverted)\n"
            "15-29 = Mostly incorrect (predominantly false assertions with minimal correct elements)\n"
            "0-14 = Completely incorrect (completely false or contradicts verified ground truth)\n\n"
            "Output strictly valid JSON with:\n"
            "score (float 0-100), reasoning (str), supporting_evidence (list of strings quoting or summarizing verified facts), incorrect_claims (list of strings identifying false claims)."
        )

        user_prompt = (
            f"Question:\n{question}\n\n"
            f"AI Response To Verify:\n{ai_response}\n\n"
            f"Available Evidence Hierarchy:\n{evidence_str}"
        )

        raw_llm = llm_service.query(user_prompt, system_prompt)
        parsed = self.extract_json(raw_llm)
        consistency = assess_factual_consistency(
            question,
            ai_response,
            [text for text in [reference_answer, source_information] if text]
            + [chunk.text for chunk in relevant_chunks],
        )

        if parsed and "score" in parsed and "reasoning" in parsed:
            supporting = self.string_list(parsed.get("supporting_evidence", []))
            incorrect = self.string_list(parsed.get("incorrect_claims", []))
            try:
                score = self.normalize_score(parsed["score"], source_scale=100)
            except ValueError:
                score = None
            if (
                score is not None
                and isinstance(parsed["reasoning"], str)
                and supporting is not None
                and incorrect is not None
            ):
                result = {
                    "score": score,
                    "reasoning": parsed["reasoning"],
                    "supporting_evidence": supporting,
                    "incorrect_claims": incorrect,
                    "execution_time_ms": round((time.time() - start_time) * 1000, 2),
                    "status": "SUCCESS"
                }
                return self._apply_consistency(result, consistency)

        res = self._local_evaluate(question, ai_response, reference_answer, source_information, relevant_chunks)
        res = self._apply_consistency(res, consistency)
        res["execution_time_ms"] = round((time.time() - start_time) * 1000, 2)
        res["status"] = "SUCCESS"
        return res

    def _apply_consistency(self, result: Dict[str, Any], consistency: Dict[str, Any]) -> Dict[str, Any]:
        state = consistency["factual_consistency"]
        result["factual_consistency"] = state
        result["claim_assessments"] = consistency.get("claim_assessments", [])
        result["incorrect_claims"] = list(dict.fromkeys(
            result.get("incorrect_claims", []) + consistency["incorrect_claims"]
        ))
        verified_evidence = [
            claim.get("evidence", "")
            for claim in consistency.get("claim_assessments", [])
            if claim.get("status") == "correct" and claim.get("evidence")
        ]
        result["supporting_evidence"] = list(dict.fromkeys(
            result.get("supporting_evidence", []) + verified_evidence
        ))
        if state == "CONTRADICTORY":
            result["score"] = min(float(result["score"]), 1.0)
            result["reasoning"] = f"{consistency['reasoning']} Accuracy is capped because a major factual contradiction was detected."
        elif state == "UNSUPPORTED":
            result["score"] = min(float(result["score"]), 2.5)
            result["reasoning"] = (
                f"{consistency['reasoning']} Unverified claims are not treated as proven false. "
                f"{result.get('reasoning', '')}"
            ).strip()
        elif state == "PARTIALLY_CONSISTENT":
            result["score"] = min(float(result["score"]), 4.0)
            result["reasoning"] = f"{consistency['reasoning']} {result.get('reasoning', '')}".strip()
        return result

    def _local_evaluate(
        self,
        question: str,
        ai_response: str,
        reference_answer: Optional[str],
        source_information: Optional[str],
        retrieved_evidence: Optional[List[RetrievedChunk]]
    ) -> Dict[str, Any]:
        evidence_texts = [text for text in (reference_answer, source_information) if text]
        evidence_texts.extend(chunk.text for chunk in (retrieved_evidence or []))
        analysis = assess_claims(question, ai_response, evidence_texts)
        claims = analysis["claims"]
        scores = {
            "correct": 5.0,
            "partially_correct": 3.0,
            "incorrect": 0.5,
            "unverifiable": 2.5,
        }
        score = sum(scores[claim["status"]] for claim in claims) / max(1, len(claims))
        supporting_evidence = [
            claim["evidence"] for claim in claims
            if claim["status"] == "correct" and claim.get("evidence")
        ]
        incorrect_claims = [
            f'{claim["claim"]}: {claim["reasoning"]}'
            for claim in claims if claim["status"] == "incorrect"
        ]
        unverifiable_count = sum(claim["status"] == "unverifiable" for claim in claims)
        if not analysis["has_evidence"]:
            reasoning = (
                "No reference, source material, or relevant retrieved evidence was available. "
                "Factual claims are unverified, not proven incorrect."
            )
        elif incorrect_claims:
            reasoning = f"{len(incorrect_claims)} claim(s) contradict the available evidence."
        elif unverifiable_count:
            reasoning = f"{unverifiable_count} claim(s) could not be verified; other claims were compared with evidence."
        else:
            reasoning = "All evaluated claims are supported by the available evidence."
        return {
            "score": score,
            "reasoning": reasoning,
            "supporting_evidence": supporting_evidence,
            "incorrect_claims": incorrect_claims,
            "claim_assessments": claims,
        }
