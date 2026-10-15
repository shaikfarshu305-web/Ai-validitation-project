import re
import json
import time
import logging
import math
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.agents.factual_consistency import _content_words

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Base class for all AI validation specialized evaluation agents.
    Provides timing, error recovery, JSON extraction, and lifecycle tracking.
    """
    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    def extract_json(self, raw_text: str) -> Dict[str, Any]:
        """Safely extract valid JSON object from LLM response text."""
        if not raw_text:
            return {}

        # Strip code markdown fences if present
        cleaned = raw_text.strip()
        if "```" in cleaned:
            match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', cleaned)
            if match:
                cleaned = match.group(1).strip()

        # Direct JSON parse attempt
        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            pass

        # Search for first '{' and matching '}'
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if start != -1 and end != -1 and end > start:
            substring = cleaned[start:end+1]
            try:
                return json.loads(substring)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse substring JSON for {self.agent_name}: {e}")

        return {}

    def normalize_score(self, raw_score: Any, source_scale: int | None = None) -> float:
        """
        Convert common LLM score formats into the project's 0-5 quality scale.
        An explicit source scale removes ambiguity for values such as 1 or 5.
        """
        try:
            if raw_score is None:
                raise ValueError("Score is missing.")

            if isinstance(raw_score, str):
                raw_score = raw_score.strip()
                if "/" in raw_score:
                    parts = raw_score.split("/")
                    num = float(re.sub(r'[^\d.]', '', parts[0]))
                    den = float(re.sub(r'[^\d.]', '', parts[1]))
                    if den > 0:
                        return float(max(0.0, min(5.0, (num / den) * 5.0)))
                    else:
                        raise ValueError("Score denominator must be positive.")
                elif raw_score.endswith("%"):
                    raw_score = raw_score[:-1]
                    source_scale = 100
                else:
                    raw_score = re.sub(r'[^\d.]', '', raw_score)

            if raw_score == "":
                raise ValueError("Score is empty.")

            val = float(raw_score)
            if not math.isfinite(val):
                raise ValueError("Score must be finite.")

            if source_scale == 100:
                if not 0.0 <= val <= 100.0:
                    raise ValueError("Score is outside the 0-100 range.")
                val /= 20.0
            elif source_scale == 10:
                if not 0.0 <= val <= 10.0:
                    raise ValueError("Score is outside the 0-10 range.")
                val /= 2.0
            elif source_scale == 5:
                if not 0.0 <= val <= 5.0:
                    raise ValueError("Score is outside the 0-5 range.")
            elif not 0.0 <= val <= 100.0:
                raise ValueError("Score is outside the supported range.")
            elif 0.0 <= val <= 1.0:
                val = val * 5.0
            elif 1.0 < val <= 5.0:
                pass
            elif 5.0 < val <= 10.0:
                val = val / 2.0
            elif 10.0 < val <= 100.0:
                val = val / 20.0

            return float(max(0.0, min(5.0, val)))
        except (TypeError, ValueError, IndexError) as exc:
            raise ValueError(f"Invalid judge score: {raw_score!r}") from exc

    @staticmethod
    def string_list(raw_value: Any) -> List[str] | None:
        if raw_value is None:
            return []
        if isinstance(raw_value, list) and all(isinstance(item, str) for item in raw_value):
            return raw_value
        return None

    @staticmethod
    def keyword_tokens(text: str) -> List[str]:
        """Extract meaningful answer/question terms, including common short acronyms like AI and NLP."""
        if not text:
            return []
        stop_words = {
            "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
            "the", "a", "an", "and", "or", "is", "are", "was", "were", "be", "been",
            "being", "to", "of", "in", "on", "for", "with", "by", "as", "at", "it",
            "its", "this", "that", "these", "those", "from", "into", "about", "under",
            "over", "after", "before", "between", "through", "using", "used", "can",
            "could", "should", "would", "do", "does", "did", "not", "no", "yes", "very",
            "also", "than", "then", "them", "they", "their", "there", "here", "have",
            "has", "had", "make", "makes", "made", "just", "like", "such", "more", "most",
            "other", "some", "many", "all", "each", "both", "same", "into", "your", "our",
            "explain", "describe", "tell", "show", "define", "define", "determine", "answer"
        }
        tokens = re.findall(r"[A-Za-z]{2,}", text.lower())
        return [token for token in tokens if token not in stop_words and len(token) >= 2]

    @staticmethod
    def is_evaluation_mode(question: str = "", reference_answer: str = None, source_information: str = None) -> bool:
        """Treat explicit evaluation directives as a scoring mode instead of factual ground truth."""
        text_parts = [question or "", reference_answer or "", source_information or ""]
        combined = " ".join(text_parts).lower().replace("evaution", "evaluation")
        if not combined.strip():
            return False

        if re.search(r"\bcorrect answer is\s+evaluation\b", combined):
            return True

        for value in (reference_answer, source_information):
            if value is None:
                continue
            normalized = value.strip().lower().replace("evaution", "evaluation")
            if normalized in {"evaluation", "evaluate"}:
                return True

        return False

    @staticmethod
    def filter_relevant_chunks(question: str, reference_answer: str = None, retrieved_evidence=None):
        """Ignore weak / irrelevant RAG chunks so unrelated snippets cannot trigger false contradictions."""
        if not retrieved_evidence:
            return []

        target_terms = set()
        for text in [question or "", reference_answer or ""]:
            target_terms |= _content_words(text)

        kept = []
        for chunk in retrieved_evidence:
            text = getattr(chunk, "text", str(chunk)) or ""
            terms = _content_words(text)
            overlap = len(target_terms & terms)
            similarity = getattr(chunk, "similarity_score", 0.0) or 0.0
            if overlap >= 1 or similarity >= 0.65:
                kept.append(chunk)

        return kept

    @abstractmethod
    def evaluate(self, **kwargs) -> Dict[str, Any]:
        """Execute agent evaluation."""
        pass
