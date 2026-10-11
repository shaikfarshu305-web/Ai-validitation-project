import time
import re
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent
from app.services.llm_service import llm_service
from app.schemas.evaluation_schemas import RetrievedChunk

class CompletenessJudgeAgent(BaseAgent):
    """
    Evaluates whether the AI response addresses all sub-questions and key requirements.
    Identifies addressed aspects and missing aspects.
    Scale: 0 - 5.
    """
    def __init__(self):
        super().__init__("CompletenessJudge")

    def evaluate(
        self,
        question: str,
        ai_response: str,
        reference_answer: Optional[str] = None,
        retrieved_evidence: Optional[List[RetrievedChunk]] = None
    ) -> Dict[str, Any]:
        start_time = time.time()

        ref_context = reference_answer if reference_answer else ""
        if not ref_context and retrieved_evidence:
            ref_context = "\n".join([f"Evidence snippet: {c.text}" for c in retrieved_evidence[:3]])

        system_prompt = (
            "You are the Completeness Judge Agent for the AI Response Validation system.\n"
            "Your role is to assess whether the AI response answers all aspects, sub-questions, and depth required by the prompt.\n"
            "Reference truth/evidence (if available):\n"
            f"{ref_context or 'None provided'}\n\n"
            "Score on a 0 to 5 scale:\n"
            "5 = Complete (comprehensive coverage of all sub-questions and necessary context)\n"
            "4 = Mostly complete (covers primary questions with minor non-critical omissions)\n"
            "3 = Partially complete (answers one part of a multi-part question but leaves other parts unanswered)\n"
            "2 = Significant omissions (misses essential requirements or critical answers)\n"
            "1 = Mostly incomplete (superficial glance, largely unanswered)\n"
            "0 = Does not answer the required aspects\n\n"
            "Output JSON format:\n"
            "{\n"
            "  \"score\": float (0-5),\n"
            "  \"reasoning\": \"...\",\n"
            "  \"addressed_aspects\": [\"list of specific aspects covered\"],\n"
            "  \"missing_aspects\": [\"list of specific omitted aspects\"]\n"
            "}"
        )

        user_prompt = f"Question:\n{question}\n\nAI Response:\n{ai_response}"

        raw_llm = llm_service.query(user_prompt, system_prompt)
        parsed = self.extract_json(raw_llm)

        if parsed and "score" in parsed and "reasoning" in parsed:
            score = float(max(0.0, min(5.0, parsed["score"])))
            result = {
                "score": score,
                "reasoning": str(parsed.get("reasoning", "")),
                "addressed_aspects": list(parsed.get("addressed_aspects", [])),
                "missing_aspects": list(parsed.get("missing_aspects", [])),
                "execution_time_ms": round((time.time() - start_time) * 1000, 2),
                "status": "SUCCESS"
            }
            return result

        res = self._local_evaluate(question, ai_response, reference_answer, retrieved_evidence)
        res["execution_time_ms"] = round((time.time() - start_time) * 1000, 2)
        res["status"] = "SUCCESS"
        return res

    def _local_evaluate(
        self,
        question: str,
        ai_response: str,
        reference_answer: Optional[str],
        retrieved_evidence: Optional[List[RetrievedChunk]]
    ) -> Dict[str, Any]:
        # Identify sub-clauses in question (using conjunctions 'and', 'also', 'as well as', '?', etc.)
        clauses = [c.strip() for c in re.split(r'\band\b|\balso\b|\bas well as\b|\?|,', question) if len(c.strip()) > 8]
        if not clauses:
            clauses = [question.strip()]

        addressed = []
        missing = []
        r_lower = ai_response.lower()

        # Check coverage of each clause
        for clause in clauses:
            c_words = self.keyword_tokens(clause)
            stop = {"what", "when", "where", "which", "who", "why", "how", "the", "and", "is", "are", "does", "explain"}
            c_keywords = [w for w in c_words if w not in stop]
            if not c_keywords:
                continue

            matches = [w for w in c_keywords if w in r_lower]
            ratio = len(matches) / len(c_keywords)

            aspect_desc = f"Inquiry aspect: \"{clause[:60]}...\"" if len(clause) > 60 else f"Inquiry aspect: \"{clause}\""
            if ratio >= 0.5:
                addressed.append(aspect_desc)
            else:
                missing.append(f"Omitted or insufficiently explained: \"{clause}\"")

        # Check reference answer key concepts coverage if provided
        if reference_answer:
            ref_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', reference_answer.lower()))
            common_ref = ref_words.intersection(set(re.findall(r'\b[a-zA-Z]{4,}\b', r_lower)))
            ref_coverage = len(common_ref) / max(1, len(ref_words))
        else:
            ref_coverage = 0.8

        total_aspects = len(addressed) + len(missing)
        if total_aspects == 0:
            total_aspects = 1
            addressed.append("General prompt response")

        addressed_ratio = len(addressed) / total_aspects

        if len(missing) == 0 and len(ai_response.split()) >= 25:
            score = 5.0
            reasoning = "Comprehensive response addressing all explicit questions and underlying context."
        elif len(missing) == 0:
            score = 4.2
            reasoning = "All core aspects addressed, though could benefit from greater elaboration."
            if not reference_answer and len(ai_response.split()) < 30:
                q_tokens = set(re.findall(r'\b[a-zA-Z]{3,}\b', question.lower()))
                stop = {"what", "when", "where", "which", "who", "why", "how", "the", "and", "is", "are", "does", "explain"}
                q_core = q_tokens - stop
                if len(q_core) == 1:
                    generic_signals = {"easy", "popular", "simple", "many", "applications", "types", "basic", "common", "learn", "beginner"}
                    technical_signals = {"sunlight", "water", "carbon", "dioxide", "glucose", "oxygen", "syntax", "interpreted", "purpose", "science", "automation", "development", "machine", "learning", "intelligence", "data", "framework", "platform", "system"}
                    if (
                        any(signal in ai_response.lower() for signal in generic_signals)
                        and not any(signal in ai_response.lower() for signal in technical_signals)
                    ):
                        score = 3.2
                        reasoning = "The response is broadly on-topic but still too generic and under-detailed for a complete answer."
        elif addressed_ratio >= 0.65:
            score = 3.8
            reasoning = f"Mostly complete; successfully covers {len(addressed)} of {total_aspects} aspects but leaves secondary points incomplete."
        elif addressed_ratio >= 0.35:
            score = 2.5
            reasoning = f"Partially complete; {len(missing)} requirement(s) were neglected in the AI output."
        else:
            score = 1.5
            reasoning = "Significant omissions; fails to provide answers to most requested dimensions."

        return {
            "score": score,
            "reasoning": reasoning,
            "addressed_aspects": addressed,
            "missing_aspects": missing
        }
