import time
import re
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent
from app.agents.factual_consistency import _content_words, assess_factual_consistency
from app.services.llm_service import llm_service
from app.schemas.evaluation_schemas import RelevanceOutput
from app.schemas.evaluation_schemas import RetrievedChunk

class RelevanceJudgeAgent(BaseAgent):
    """
    Evaluates whether the AI response directly answers the submitted question.
    Criteria: Directness, Topic alignment, Question understanding, Off-topic drift.
    Scale: 0 - 5.
    """
    def __init__(self):
        super().__init__("RelevanceJudge")

    def evaluate(
        self,
        question: str,
        ai_response: str,
        reference_answer: Optional[str] = None,
        source_information: Optional[str] = None,
        retrieved_evidence: Optional[List[RetrievedChunk]] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()

        # Check LLM query
        system_prompt = (
            "You are the Relevance Judge Agent for the AI Response Validation system. "
            "Your objective is to evaluate whether the AI response directly answers the submitted question.\n"
            "Score on a 0 to 100 scale:\n"
            "90-100 = Fully relevant (directly addresses all aspects of the prompt without drifting)\n"
            "80-89 = Mostly relevant (addresses the core question with minimal tangential points)\n"
            "60-79 = Partially relevant (touches on the topic but evades the direct question or only answers partially)\n"
            "30-59 = Weakly relevant (tangentially related to keywords but fails to answer the inquiry)\n"
            "15-29 = Mostly irrelevant (off-topic with negligible relevance)\n"
            "0-14 = Completely irrelevant (unrelated topic or refusal to answer)\n\n"
            "Output strictly valid JSON with keys: score (float 0-100), reasoning (str), strengths (list of strings), issues (list of strings)."
        )

        user_prompt = f"Question: {question}\n\nAI Response: {ai_response}"
        evidence_texts = [text for text in [reference_answer, source_information] if text]
        evidence_texts.extend(chunk.text for chunk in (retrieved_evidence or []))
        if evidence_texts:
            user_prompt += "\n\nReference evidence for detecting a wrong definition or answer:\n" + "\n".join(evidence_texts)

        raw_llm = llm_service.query(user_prompt, system_prompt)
        parsed = self.extract_json(raw_llm)

        if parsed and "score" in parsed and "reasoning" in parsed:
            strengths = self.string_list(parsed.get("strengths", []))
            issues = self.string_list(parsed.get("issues", []))
            try:
                score = self.normalize_score(parsed["score"], source_scale=100)
            except ValueError:
                score = None
            if (
                score is not None
                and isinstance(parsed["reasoning"], str)
                and strengths is not None
                and issues is not None
            ):
                res = {
                    "score": score,
                    "reasoning": parsed["reasoning"],
                    "strengths": strengths,
                    "issues": issues,
                    "execution_time_ms": round((time.time() - start_time) * 1000, 2),
                    "status": "SUCCESS"
                }
                return self._apply_factual_consistency(res, question, ai_response, evidence_texts)

        # High-Fidelity Local Semantic Fallback
        res = self._local_evaluate(question, ai_response)
        res = self._apply_factual_consistency(res, question, ai_response, evidence_texts)
        res["execution_time_ms"] = round((time.time() - start_time) * 1000, 2)
        res["status"] = "SUCCESS"
        return res

    def _apply_factual_consistency(
        self,
        result: Dict[str, Any],
        question: str,
        ai_response: str,
        evidence_texts: List[str],
    ) -> Dict[str, Any]:
        consistency = assess_factual_consistency(question, ai_response, evidence_texts)
        result["factual_consistency"] = consistency["factual_consistency"]
        if consistency["factual_consistency"] == "CONTRADICTORY":
            result["score"] = min(float(result["score"]), 2.0)
            issue = f"The response contradicts the supplied reference: {consistency['reasoning']}"
            result["issues"] = list(dict.fromkeys(result.get("issues", []) + [issue]))
            result["reasoning"] = issue
        elif consistency["factual_consistency"] == "PARTIALLY_CONSISTENT":
            result["score"] = min(float(result["score"]), 4.5)
        return result

    def _local_evaluate(self, question: str, ai_response: str) -> Dict[str, Any]:
        question_concepts = _content_words(question)
        response_concepts = _content_words(ai_response)
        matched_concepts = question_concepts & response_concepts
        coverage = len(matched_concepts) / max(1, len(question_concepts))

        causal_question = bool(re.search(r"\b(?:why|what causes|what is the cause)\b", question, re.I))
        answers_cause = bool(response_concepts & {"cause", "result", "reason", "explain"})
        if causal_question and not answers_cause:
            coverage *= 0.5

        if coverage >= 0.7:
            score = 5.0
            reasoning = "The response directly addresses the question's central concepts and requested intent."
        elif coverage >= 0.5:
            score = 4.5
            reasoning = "The response addresses the main question, with some requested concepts not clearly covered."
        elif coverage >= 0.3:
            score = 3.5
            reasoning = "The response is partly relevant but does not fully resolve the question."
        elif coverage >= 0.15:
            score = 2.0
            reasoning = "The response has limited topical connection and mostly misses the question's intent."
        else:
            score = 1.0
            reasoning = "The response does not meaningfully address the submitted question."

        strengths = []
        issues = []
        if matched_concepts:
            strengths.append(
                f"Addresses {len(matched_concepts)} of {len(question_concepts)} normalized question concepts."
            )
        if coverage >= 0.5:
            strengths.append("Responds to the central inquiry rather than relying only on surface wording.")
        if coverage < 0.5:
            issues.append("Several central question concepts are missing or not answered directly.")
        if causal_question and not answers_cause:
            issues.append("The question asks for a cause, but the response does not explain one.")
        return {"score": score, "reasoning": reasoning, "strengths": strengths, "issues": issues}
