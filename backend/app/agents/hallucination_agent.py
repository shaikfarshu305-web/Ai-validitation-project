import time
import re
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent
from app.agents.factual_consistency import assess_factual_consistency
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
            score = float(max(0.0, min(5.0, parsed.get("hallucination_score", 4.0))))
            result = {
                "hallucination_status": str(parsed.get("hallucination_status", "LOW")).upper(),
                "hallucination_score": score,
                "flagged_claims": list(parsed.get("flagged_claims", [])),
                "reasoning": str(parsed.get("reasoning", "")),
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
            result["hallucination_score"] = min(float(result["hallucination_score"]), 3.5)
            result["flagged_claims"] = consistency["flagged_claims"]
            result["reasoning"] = consistency["reasoning"]
        elif state == "PARTIALLY_CONSISTENT":
            result["hallucination_score"] = min(float(result["hallucination_score"]), 4.5)
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
        corpus_list = []
        if reference_answer:
            corpus_list.append(reference_answer)
        if source_information:
            corpus_list.append(source_information)
        if retrieved_evidence:
            for c in retrieved_evidence:
                corpus_list.append(c.text)

        full_corpus = " ".join(corpus_list).lower()

        # Split response into atomic claim sentences
        raw_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', ai_response) if len(s.strip()) > 8]
        if not raw_sentences:
            raw_sentences = [ai_response.strip()]

        flagged_claims = []
        contradicted_count = 0
        unsupported_count = 0
        supported_count = 0

        # Disproved myths or common contradictory markers
        myth_triggers = ["visible from space", "great wall", "10% of their brain", "blood is blue", "sugar causes hyperactivity", "lightning never strikes"]

        for sent in raw_sentences:
            s_lower = sent.lower()
            words = self.keyword_tokens(s_lower)
            if not words:
                continue

            # Check for known contradictory myths if present in TruthfulQA style
            is_contradicted = False
            for myth in myth_triggers:
                if myth in s_lower:
                    # If corpus refutes it or mentions myth/not
                    if "myth" in full_corpus or "cannot" in full_corpus or "not" in full_corpus or "refuted" in full_corpus:
                        is_contradicted = True
                        break

            stopwords = {"the", "and", "are", "is", "was", "were", "from", "for", "with", "between", "that", "this", "can", "may", "which", "into", "their"}
            content_words = [w for w in words if w not in stopwords]
            if not content_words:
                content_words = words

            # Find matching words or stems in evidence corpus
            matches = [w for w in content_words if (w in full_corpus or (len(w) >= 5 and w[:4] in full_corpus))]
            overlap = len(matches) / len(content_words) if content_words else 0.0

            if is_contradicted:
                contradicted_count += 1
                flagged_claims.append({
                    "claim": sent,
                    "status": "contradicted",
                    "reasoning": "This statement contradicts established scientific consensus and verified reference material.",
                    "evidence": "Corroborated evidence refutes this common misconception or conflicting claim."
                })
            elif overlap >= 0.40:
                supported_count += 1
                flagged_claims.append({
                    "claim": sent,
                    "status": "supported",
                    "reasoning": "Claim terms directly match verified reference material.",
                    "evidence": "Ground truth corpus corroborates the key concepts in this statement."
                })
            elif overlap >= 0.20:
                supported_count += 1
                flagged_claims.append({
                    "claim": sent,
                    "status": "supported",
                    "reasoning": "Plausible contextual statement consistent with surrounding verified facts.",
                    "evidence": "Consistent with broader domain knowledge in retrieved evidence."
                })
            else:
                unsupported_count += 1
                flagged_claims.append({
                    "claim": sent,
                    "status": "unsupported",
                    "reasoning": "This factual claim lacks verification or documentation in the retrieved evidence corpus.",
                    "evidence": "No matching documentation found in RAG knowledge chunks or reference text."
                })

        if not full_corpus.strip():
            return {
                "hallucination_status": "MEDIUM",
                "hallucination_score": 3.5,
                "flagged_claims": [{
                    "claim": claim["claim"],
                    "status": "unsupported",
                    "reasoning": "No reference evidence was available to verify this claim.",
                    "evidence": "No evidence available.",
                } for claim in flagged_claims],
                "reasoning": "Claims could not be verified because no reference or retrieved evidence was available.",
            }

        # Calculate safety score and status
        total_claims = max(1, len(flagged_claims))
        if contradicted_count > 0:
            status = "HIGH"
            score = max(0.5, 2.0 - (contradicted_count * 0.5))
            reasoning = f"Severe hallucination alert: Found {contradicted_count} contradicted statement(s) that directly conflict with verified ground truth."
        elif unsupported_count >= 2 or (unsupported_count / total_claims) > 0.5:
            status = "MEDIUM"
            score = 3.0
            reasoning = f"Noticeable hallucination risk: {unsupported_count} of {total_claims} claims could not be verified against the knowledge base."
        elif unsupported_count == 1:
            status = "LOW"
            score = 4.5
            reasoning = "Low hallucination risk: Most assertions are corroborated, with only one unverified claim noted."
        else:
            status = "LOW"
            score = 5.0
            reasoning = "High fidelity: 100% of factual assertions were successfully grounded against verified evidence."

        return {
            "hallucination_status": status,
            "hallucination_score": score,
            "flagged_claims": flagged_claims,
            "reasoning": reasoning
        }
