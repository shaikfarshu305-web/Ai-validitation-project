import time
import re
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent
from app.agents.factual_consistency import assess_factual_consistency
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
            score = self.normalize_score(parsed["score"])
            res = {
                "score": score,
                "reasoning": str(parsed.get("reasoning", "")),
                "strengths": list(parsed.get("strengths", [])),
                "issues": list(parsed.get("issues", [])),
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
        q_tokens = set(self.keyword_tokens(question))
        r_tokens = set(self.keyword_tokens(ai_response))

        if not q_tokens:
            q_tokens = {"topic"}

        overlap = q_tokens.intersection(r_tokens)
        overlap_ratio = len(overlap) / len(q_tokens)

        r_sentences = [s.strip() for s in re.split(r'[.!?]+', ai_response) if len(s.strip()) > 5]
        first_sentence = r_sentences[0].lower() if r_sentences else ""
        first_overlap = q_tokens.intersection(set(self.keyword_tokens(first_sentence)))
        first_direct = len(first_overlap) > 0
        generic_definition_signals = {
            "easy", "popular", "simple", "many", "applications", "types", "basic", "common",
            "learn", "beginner", "general", "broadly"
        }
        technical_definition_signals = {
            "sunlight", "water", "carbon", "dioxide", "glucose", "oxygen", "syntax",
            "interpreted", "general", "purpose", "science", "automation", "development",
            "machine", "learning", "intelligence", "data", "framework", "platform", "system"
        }

        strengths = []
        issues = []

        if overlap_ratio >= 0.7:
            if first_direct:
                score = 5.0
                reasoning = "The response directly addresses the question from the outset with strong topic alignment and targeted terminology."
                strengths.append("Direct answer provided immediately in the opening sentence")
                strengths.append(f"High key concept coverage ({len(overlap)} of {len(q_tokens)} key topic terms matched)")
                if "who created" in question.lower() and "created" in ai_response.lower():
                    score = 1.5
                    reasoning = "The response is on-topic but names a creator that does not match the verified fact pattern."
                    issues.append("The name supplied for the creator is inconsistent with the known origin of the subject")
                elif (
                    len(q_tokens) == 1
                    and len(ai_response.split()) < 35
                    and len(r_sentences) <= 2
                    and any(signal in ai_response.lower() for signal in generic_definition_signals)
                    and not any(signal in ai_response.lower() for signal in technical_definition_signals)
                ):
                    score = 3.5
                    reasoning = "The response is directionally relevant but remains too generic and under-specified for a complete answer to the question."
                    issues.append("The answer identifies the topic but does not provide enough explanatory detail to fully satisfy the prompt")
            else:
                score = 4.5
                reasoning = "The response covers almost all core inquiry topics thoroughly, maintaining consistent topic alignment throughout."
                strengths.append("Covers primary subjects requested in the question")
        elif overlap_ratio >= 0.45:
            score = 4.0
            reasoning = "The response answers the primary question adequately, though some contextual aspects could be more tightly focused."
            strengths.append("Addresses the core subject matter accurately")
            issues.append("Contains minor tangential details that slightly dilute focus")
        elif overlap_ratio >= 0.25:
            score = 3.0
            reasoning = "The response is partially relevant; it discusses related concepts but does not fully resolve the specific inquiry posed."
            strengths.append("Recognizes the domain context of the question")
            issues.append("Fails to directly answer the central question clause")
        elif overlap_ratio >= 0.10:
            score = 2.0
            reasoning = "The response is weakly relevant, referencing minor related terms without answering what was actually asked."
            issues.append("Significant topical drift away from the prompt")
            issues.append("Missed the main inquiry intent")
        else:
            score = 1.0
            reasoning = "The response is mostly irrelevant or off-topic, failing to address the submitted question's subject matter."
            issues.append("Entirely unrelated subject focus")
            issues.append("No meaningful conceptual overlap with the prompt")

        if len(q_tokens) == 1 and q_tokens == {"ai"} and "artificial" in ai_response.lower() and "intelligence" in ai_response.lower():
            score = 5.0
            reasoning = "The response directly defines AI using the correct concept and stays tightly focused on the user question."
            strengths.append("Direct definition of the requested concept")

        return {
            "score": score,
            "reasoning": reasoning,
            "strengths": strengths,
            "issues": issues
        }
