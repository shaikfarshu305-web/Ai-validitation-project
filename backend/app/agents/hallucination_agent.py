import time
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent
from app.agents.factual_consistency import assess_claims, assess_factual_consistency
from app.services.llm_service import llm_service
from app.schemas.evaluation_schemas import RetrievedChunk

class HallucinationDetectionAgent(BaseAgent):
    """
    Dedicated Hallucination Detection Agent.
    Deconstructs response into atomic factual claims and evaluates each as:
    - SUPPORTED (corroborated by verified reference / RAG chunks)
    - UNSUPPORTED (speculative assertion with zero grounding in evidence)
    - CONTRADICTED (directly conflicts with or inverts ground truth facts)
    """
    def __init__(self):
        super().__init__("HallucinationDetector")

    def evaluate(
        self,
        question: str,
        ai_response: str,
        reference_answer: Optional[str] = None,
        source_information: Optional[str] = None,
        retrieved_evidence: Optional[List[RetrievedChunk]] = None
    ) -> Dict[str, Any]:
        start_time = time.time()

        relevant_chunks = self.filter_relevant_chunks(question, reference_answer, retrieved_evidence)

        evidence_texts = []
        if reference_answer:
            evidence_texts.append(f"Ground Truth Reference: {reference_answer}")
        if source_information:
            evidence_texts.append(f"Source Document: {source_information}")
        if relevant_chunks:
            for c in relevant_chunks:
                evidence_texts.append(f"RAG Evidence ({c.dataset}): {c.text}")
        
        combined_evidence = "\n\n".join(evidence_texts) if evidence_texts else "No external evidence provided."

        system_prompt = (
            "You are the Hallucination Detection Agent for the AI Response Validation system.\n"
            "CRITICAL INSTRUCTION: Do NOT simply label the whole text as hallucinated.\n"
            "Compare each important factual claim directly with the reference answer first, then other evidence.\n"
            "Topic similarity, fluency, and confidence are not evidence. Identify changed entities, numbers, dates, definitions, and technical facts.\n"
            "1. Deconstruct the response into individual atomic factual claims.\n"
            "2. For every claim, verify against the provided Ground Truth and RAG Evidence.\n"
            "3. Categorize each claim strictly into:\n"
            "   - 'supported': Ground truth or RAG evidence explicitly corroborates this claim.\n"
            "   - 'unsupported': The claim makes an ungrounded factual assertion not substantiated by the evidence.\n"
            "   - 'contradicted': The claim directly conflicts with or denies facts stated in the evidence.\n\n"
            "Scoring scale for hallucination_score (Safety Score, 0 to 5):\n"
            "5.0 = Zero hallucinations (all claims supported by evidence)\n"
            "4.0 = Minor ungrounded fluff or safe extrapolation, no contradictions\n"
            "3.0 = Noticeable unsupported claims that risk misleading the user\n"
            "2.0 = Significant factual fabrication or at least one contradiction\n"
            "1.0 = Severe widespread hallucinations or multiple contradictions\n"
            "0.0 = Entirely fabricated response\n\n"
            "hallucination_status must be 'LOW', 'MEDIUM', or 'HIGH'.\n"
            "Output JSON format:\n"
            "{\n"
            "  \"hallucination_status\": \"LOW\" | \"MEDIUM\" | \"HIGH\",\n"
            "  \"hallucination_score\": float (0-5),\n"
            "  \"flagged_claims\": [\n"
            "     {\"claim\": \"...\", \"status\": \"supported\"|\"unsupported\"|\"contradicted\", \"reasoning\": \"...\", \"evidence\": \"...\"}\n"
            "  ],\n"
            "  \"reasoning\": \"...\"\n"
            "}"
        )

        user_prompt = (
            f"Question:\n{question}\n\n"
            f"AI Response:\n{ai_response}\n\n"
            f"Verified Evidence:\n{combined_evidence}"
        )

        raw_llm = llm_service.query(user_prompt, system_prompt)
        parsed = self.extract_json(raw_llm)
        consistency = assess_factual_consistency(
            question,
            ai_response,
            [text for text in [reference_answer, source_information] if text]
            + [chunk.text for chunk in relevant_chunks],
        )

        if parsed and "hallucination_status" in parsed and "flagged_claims" in parsed:
            try:
                score = self.normalize_score(parsed.get("hallucination_score"), source_scale=5)
            except ValueError:
                score = None
            status = parsed.get("hallucination_status")
            reasoning = parsed.get("reasoning")
            claims = parsed.get("flagged_claims")
            valid_claims = (
                isinstance(claims, list)
                and all(
                    isinstance(claim, dict)
                    and isinstance(claim.get("claim"), str)
                    and claim.get("status") in {"supported", "unsupported", "contradicted"}
                    and isinstance(claim.get("reasoning"), str)
                    and (claim.get("evidence") is None or isinstance(claim.get("evidence"), str))
                    for claim in claims
                )
            )
            if (
                score is not None
                and status in {"LOW", "MEDIUM", "HIGH"}
                and isinstance(reasoning, str)
                and valid_claims
            ):
                result = {
                    "hallucination_status": status,
                    "hallucination_score": score,
                    "flagged_claims": claims,
                    "reasoning": reasoning,
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
        result["analyzed_claim_count"] = consistency["analyzed_claim_count"]
        if state == "CONTRADICTORY":
            result["hallucination_status"] = "HIGH"
            result["hallucination_score"] = min(float(result["hallucination_score"]), 1.0)
            result["flagged_claims"] = consistency["flagged_claims"]
            result["reasoning"] = f"Hallucination detected: {consistency['reasoning']}"
        elif state == "UNSUPPORTED":
            result["hallucination_status"] = "MEDIUM"
            result["hallucination_score"] = min(float(result["hallucination_score"]), 2.5)
            result["flagged_claims"] = consistency["flagged_claims"]
            result["reasoning"] = consistency["reasoning"]
        elif state == "PARTIALLY_CONSISTENT":
            result["hallucination_score"] = min(float(result["hallucination_score"]), 4.0)
            if result["hallucination_status"] == "LOW":
                result["hallucination_status"] = "MEDIUM"
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
        status_map = {
            "correct": "supported",
            "partially_correct": "unsupported",
            "incorrect": "contradicted",
            "unverifiable": "unsupported",
        }
        score_map = {
            "correct": 5.0,
            "partially_correct": 3.0,
            "incorrect": 0.0,
            "unverifiable": 2.5,
        }
        claims = analysis["claims"]
        flagged_claims = [
            {**claim, "status": status_map[claim["status"]]}
            for claim in claims
        ]
        score = sum(score_map[claim["status"]] for claim in claims) / max(1, len(claims))
        contradicted_count = sum(claim["status"] == "contradicted" for claim in flagged_claims)
        unsupported_count = sum(claim["status"] == "unsupported" for claim in flagged_claims)
        if not analysis["has_evidence"]:
            status = "MEDIUM"
            reasoning = (
                "No reference or relevant retrieved evidence was available. "
                "Claims are unverified; this does not prove that they are false."
            )
        elif contradicted_count:
            status = "HIGH"
            reasoning = f"{contradicted_count} claim(s) directly contradict the available evidence."
        elif unsupported_count:
            status = "MEDIUM" if unsupported_count >= len(flagged_claims) / 2 else "LOW"
            reasoning = f"{unsupported_count} of {len(flagged_claims)} claim(s) are only partially supported or unverifiable."
        else:
            status = "LOW"
            reasoning = "Every evaluated factual claim is supported by the available evidence."
        return {
            "hallucination_status": status,
            "hallucination_score": score,
            "flagged_claims": flagged_claims,
            "reasoning": reasoning,
        }
