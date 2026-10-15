import time
import re
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent
from app.agents.factual_consistency import _content_words
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
            "Do not reward length or penalize a concise answer when it covers every important requested aspect. "
            "Only report material omissions.\n"
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
            addressed = self.string_list(parsed.get("addressed_aspects", []))
            missing = self.string_list(parsed.get("missing_aspects", []))
            try:
                score = self.normalize_score(parsed["score"], source_scale=5)
            except ValueError:
                score = None
            if (
                score is not None
                and isinstance(parsed["reasoning"], str)
                and addressed is not None
                and missing is not None
            ):
                return {
                    "score": score,
                    "reasoning": parsed["reasoning"],
                    "addressed_aspects": addressed,
                    "missing_aspects": missing,
                    "execution_time_ms": round((time.time() - start_time) * 1000, 2),
                    "status": "SUCCESS"
                }

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
        clauses = [
            clause.strip(" ,?")
            for clause in re.split(
                r"\band\s+(?=(?:what|when|where|which|who|why|how|does|do|is|are)\b)|"
                r",\s*(?=(?:what|when|where|which|who|why|how)\b)",
                question,
                flags=re.I,
            )
            if clause.strip(" ,?")
        ] or [question.strip()]

        addressed = []
        missing = []
        response_concepts = _content_words(ai_response)
        reference_concepts = _content_words(reference_answer or "")
        for clause in clauses:
            aspect_concepts = _content_words(clause)
            if not aspect_concepts:
                continue
            matched = aspect_concepts & response_concepts
            coverage = len(matched) / len(aspect_concepts)
            reference_coverage = (
                len(reference_concepts & response_concepts) / len(reference_concepts)
                if len(clauses) == 1 and reference_concepts
                else 1.0
            )
            description = f'Inquiry aspect: "{clause[:60]}{"..." if len(clause) > 60 else ""}"'
            question_covered = coverage >= 0.4 or (len(aspect_concepts) <= 2 and matched)
            if question_covered:
                addressed.append(description)
            else:
                missing.append(f'Omitted or insufficiently explained: "{clause}"')
            if question_covered and reference_coverage < 0.5:
                missing.append("Some important concepts from the reference answer were not covered.")

        aspect_count = len(clauses)
        coverage = len(addressed) / max(1, aspect_count)
        if not missing:
            score = 5.0
            reasoning = "The answer covers each requested aspect; concision alone is not treated as an omission."
        elif coverage >= 0.65:
            score = 4.0
            reasoning = f"The answer covers {len(addressed)} of {aspect_count} requested aspects."
        elif coverage >= 0.35:
            score = 2.5
            reasoning = f"The answer covers only {len(addressed)} of {aspect_count} requested aspects."
        elif addressed:
            score = 1.5
            reasoning = "The answer touches on the question but omits most requested aspects."
        else:
            score = 0.0
            reasoning = "The answer does not cover the question's requested aspects."

        return {
            "score": score,
            "reasoning": reasoning,
            "addressed_aspects": addressed,
            "missing_aspects": missing
        }
