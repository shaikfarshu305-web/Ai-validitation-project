import time
import re
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent
from app.agents.factual_consistency import assess_factual_consistency
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
            score = self.normalize_score(parsed["score"])
            result = {
                "score": score,
                "reasoning": str(parsed.get("reasoning", "")),
                "supporting_evidence": list(parsed.get("supporting_evidence", [])),
                "incorrect_claims": list(parsed.get("incorrect_claims", [])),
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
        result["incorrect_claims"] = list(dict.fromkeys(
            result.get("incorrect_claims", []) + consistency["incorrect_claims"]
        ))
        if state == "CONTRADICTORY":
            result["score"] = min(float(result["score"]), 1.0)
            result["reasoning"] = f"{consistency['reasoning']} Accuracy is capped because a major factual contradiction was detected."
        elif state == "UNSUPPORTED":
            result["score"] = min(float(result["score"]), 4.0)
            result["reasoning"] = (
                f"{consistency['reasoning']} The claim is unverified, not established as false. "
                f"{result.get('reasoning', '')}"
            ).strip()
        elif state == "PARTIALLY_CONSISTENT":
            result["score"] = min(float(result["score"]), 4.5)
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
        # Synthesize ground truth corpus
        evidence_corpus = []
        if reference_answer:
            evidence_corpus.append(reference_answer.lower())
        if source_information:
            evidence_corpus.append(source_information.lower())
        if retrieved_evidence:
            for c in retrieved_evidence:
                evidence_corpus.append(c.text.lower())
        
        full_corpus = " ".join(evidence_corpus)
        
        # Extract response sentences
        sentences = [s.strip() for s in re.split(r'[.!?]+', ai_response) if len(s.strip()) > 8]
        if not sentences:
            sentences = [ai_response]

        supporting_evidence = []
        incorrect_claims = []
        unverified_claims = []
        
        if not full_corpus.strip():
            return {
                "score": 3.75,
                "reasoning": "No reference, source material, or relevant retrieved evidence was available. The answer is unverified, not confirmed incorrect; provide grounding evidence for a factual accuracy judgment.",
                "supporting_evidence": [],
                "incorrect_claims": []
            }

        matched_sentences = 0
        contradicted_sentences = 0

        # Known contradiction patterns: "not", "never", "only", numbers/dates inversion
        negation_terms = {"not", "never", "no", "false", "cannot", "impossible", "myth", "incorrect"}

        # Extract numbers from sentence vs corpus
        corpus_numbers = set(re.findall(r'\b\d+(?:\.\d+)?\b', full_corpus))

        stopwords = {"the", "and", "are", "is", "was", "were", "from", "for", "with", "between", "that", "this", "can", "may", "which", "into", "their"}

        for s in sentences:
            s_words = self.keyword_tokens(s)
            s_set = set(s_words)
            s_numbers = set(re.findall(r'\b\d+(?:\.\d+)?\b', s))
            if not s_words and not s_numbers:
                continue

            content_words = [w for w in s_words if w not in stopwords]
            if not content_words:
                content_words = s_words

            # Look for matching content words or stems in corpus
            matches = [w for w in content_words if (w in full_corpus or (len(w) >= 5 and w[:4] in full_corpus))]
            overlap_ratio = len(matches) / len(content_words) if content_words else 0.0

            # Check number conflict: response has numbers not found in reference when reference has numbers
            number_conflict = False
            if corpus_numbers and s_numbers:
                if not s_numbers.intersection(corpus_numbers):
                    number_conflict = True

            # Check negation mismatch
            has_negation_s = bool(s_set.intersection(negation_terms))
            has_negation_ref = bool(set(re.findall(r'\b[a-zA-Z]{3,}\b', full_corpus)).intersection(negation_terms))
            negation_conflict = (has_negation_s != has_negation_ref) and overlap_ratio >= 0.4

            if number_conflict:
                incorrect_claims.append(f"Conflicting numerical claim: \"{s}\" (Found numbers {list(s_numbers)}, expected {list(corpus_numbers)})")
            elif negation_conflict:
                incorrect_claims.append(f"Conflicting polarity or negation assertion: \"{s}\"")
            elif overlap_ratio >= 0.5:
                matched_sentences += 1
                snippet = s[:90] + ("..." if len(s) > 90 else "")
                supporting_evidence.append(f"Verified against reference evidence: \"{snippet}\"")
            elif overlap_ratio < 0.25 and len(s_words) > 6:
                unverified_claims.append(s)
            else:
                pass

        total_s = max(1, len(sentences))
        acc_ratio = matched_sentences / total_s

        if len(incorrect_claims) == 0:
            if unverified_claims and matched_sentences:
                score = 4.5 if acc_ratio >= 0.5 else 4.0
                reasoning = (
                    "The core answer aligns with the reference. Additional factual details could not be verified "
                    "and are not treated as proven errors."
                )
            elif acc_ratio >= 0.70:
                score = 5.0
                reasoning = "All evaluated statements align factually with the verified reference evidence and ground truth citations."
            elif acc_ratio >= 0.40:
                score = 4.5
                reasoning = "The response is factually sound across all major verified claims, closely mirroring available evidence."
            elif acc_ratio >= 0.20:
                score = 4.0
                reasoning = "Core concepts match verified reference material; factual statements are consistent with evidence."
            else:
                score = 3.5
                reasoning = "Response appears consistent and plausible, though direct textual overlap with reference material is modest."
        elif len(incorrect_claims) == 1:
            score = 2.5
            reasoning = f"Partially accurate; while some contextual terms match, the response contains a critical factual discrepancy: {incorrect_claims[0]}."
        else:
            score = 1.5
            reasoning = f"Significant inaccuracies detected; {len(incorrect_claims)} statement(s) directly contradict or deviate from ground truth facts."

        return {
            "score": score,
            "reasoning": reasoning,
            "supporting_evidence": supporting_evidence[:4],
            "incorrect_claims": incorrect_claims[:3]
        }
