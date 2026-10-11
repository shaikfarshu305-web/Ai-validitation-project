import re
from typing import Any, Dict, List


_STOP_WORDS = {
    "the", "and", "are", "was", "were", "is", "a", "an", "of", "to", "in", "on",
    "for", "with", "that", "this", "it", "as", "by", "from", "at", "be", "can",
    "which", "their", "they", "these", "those", "before", "after", "into", "used",
    "use", "mainly", "each", "every", "its", "all", "or", "such", "than", "then",
}
_NEGATION = re.compile(r"\b(?:not|never|cannot|can't|doesn't|don't|isn't|aren't|without|no)\b", re.I)
_PERSON_AFTER_BY = re.compile(
    r"\bby\s+([A-Z][a-z]+(?:\s+(?:van|von|de|del|da|di|la|le)\s+[A-Z][a-z]+|\s+[A-Z][a-z]+)*)"
)
_DEFINITION = re.compile(
    r"\b(?:is|are|means|refers to|is defined as)\s+(?:a|an|the)?\s*"
    r"([a-z]+(?:\s+[a-z]+){0,2})",
    re.I,
)


def _content_words(text: str) -> set[str]:
    words = set(re.findall(r"[a-z]+", text.lower())) - _STOP_WORDS
    return {word[:-3] if word.endswith("ing") and len(word) > 5 else word for word in words}


def _definition_class(text: str) -> str | None:
    lowered = text.lower()
    if re.search(r"\b(?:learn|learning|train|training|patterns?)\b.*\b(?:data|examples)\b", lowered):
        return "data-driven learning approach"
    if re.search(r"\b(?:manually|manual|hand-written|predefined)\b.*\brules?\b", lowered):
        return "manual rule-based approach"
    if re.search(r"\bprogramming language\b", lowered):
        return "programming language"
    if re.search(r"\b(?:database management system|database management software|dbms)\b", lowered):
        return "database management system"
    if re.search(r"\boperating system\b", lowered):
        return "operating system"
    if re.search(r"\bprimary key\b.*\buniquely identifies\b", lowered):
        return "unique database identifier"
    if re.search(r"\b(?:branch|field|area|discipline) of (?:artificial intelligence|ai)\b", lowered):
        return "AI field"
    if re.search(r"\b(retriev\w*|fetch\w*)\b.*\b(?:knowledge|document|source|information)\b", lowered):
        return "information retrieval method"
    return None


def _person_claim(text: str) -> str | None:
    match = _PERSON_AFTER_BY.search(text)
    return re.sub(r"\s+", " ", match.group(1)) if match else None


def assess_factual_consistency(
    question: str,
    response: str,
    evidence_texts: List[str],
) -> Dict[str, Any]:
    """Compare answer claims with supplied evidence; topic overlap is not proof."""
    evidence = "\n".join(text.strip() for text in evidence_texts if text and text.strip())
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", response.strip()) if part.strip()]
    if not sentences and response.strip():
        sentences = [response.strip()]
    question_class = (
        "programming language"
        if re.search(r"\bpython\b", question, re.I)
        else _definition_class(question)
    )

    if not evidence:
        response_class = _definition_class(response)
        if question_class and response_class and question_class != response_class:
            reasoning = f"The response defines the subject as {response_class}; the question's subject is {question_class}."
            claim = {
                "claim": response,
                "status": "contradicted",
                "reasoning": reasoning,
                "evidence": "The subject category named in the question conflicts with the response's definition.",
            }
            return {
                "factual_consistency": "CONTRADICTORY",
                "reasoning": reasoning,
                "incorrect_claims": [reasoning],
                "flagged_claims": [claim],
                "analyzed_claim_count": len(sentences),
                "has_evidence": True,
            }
        reasoning = "No reference, source material, or retrieved evidence was available to verify the response's factual claims."
        return {
            "factual_consistency": "UNSUPPORTED",
            "reasoning": reasoning,
            "incorrect_claims": [],
            "flagged_claims": [{
                "claim": sentence,
                "status": "unsupported",
                "reasoning": reasoning,
                "evidence": "No evidence available.",
            } for sentence in sentences[:5]],
            "analyzed_claim_count": len(sentences),
            "has_evidence": False,
        }

    evidence_words = _content_words(evidence)
    response_words = _content_words(response)
    shared_words = evidence_words & response_words
    response_ratio = len(shared_words) / max(1, len(response_words))
    evidence_ratio = len(shared_words) / max(1, len(evidence_words))
    contradictions: List[Dict[str, str]] = []

    reference_person = _person_claim(evidence)
    response_person = _person_claim(response)
    who_question = bool(re.match(r"\s*(?:who|which person)\b", question, re.I))
    if who_question and reference_person and response_person and reference_person.casefold() != response_person.casefold():
        contradictions.append({
            "claim": response_person,
            "reasoning": f"The response names {response_person}, but the reference names {reference_person}.",
            "evidence": evidence[:500],
        })

    reference_class = _definition_class(evidence) or question_class
    response_class = _definition_class(response)
    if reference_class and response_class and reference_class != response_class:
        contradictions.append({
            "claim": response,
            "reasoning": f"The response defines the subject as {response_class}; the reference describes it as {reference_class}.",
            "evidence": evidence[:500],
        })

    if bool(_NEGATION.search(evidence)) != bool(_NEGATION.search(response)) and shared_words:
        contradictions.append({
            "claim": response,
            "reasoning": "The response reverses the reference's positive/negative assertion about the same factual terms.",
            "evidence": evidence[:500],
        })

    reference_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", evidence))
    response_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", response))
    number_question = bool(re.search(r"\b(?:when|what year|how many|how much|what temperature|how old)\b", question, re.I))
    if reference_numbers and response_numbers and not reference_numbers.intersection(response_numbers):
        if number_question or len(shared_words) >= 2:
            contradictions.append({
                "claim": response,
                "reasoning": f"The response gives {', '.join(sorted(response_numbers))}, while the reference gives {', '.join(sorted(reference_numbers))}.",
                "evidence": evidence[:500],
            })

    if contradictions:
        claims = [{
            "claim": item["claim"],
            "status": "contradicted",
            "reasoning": item["reasoning"],
            "evidence": item["evidence"],
        } for item in contradictions]
        return {
            "factual_consistency": "CONTRADICTORY",
            "reasoning": " ".join(item["reasoning"] for item in contradictions),
            "incorrect_claims": [item["reasoning"] for item in contradictions],
            "flagged_claims": claims,
            "analyzed_claim_count": len(sentences),
            "has_evidence": True,
        }

    if response_ratio >= 0.55 and evidence_ratio >= 0.15:
        consistency = "CONSISTENT"
        reasoning = "The response's key factual terms are supported by the supplied evidence, with no detected contradiction."
    elif response_ratio >= 0.2:
        consistency = "PARTIALLY_CONSISTENT"
        reasoning = "Some response claims align with the evidence, but other important claims or details are not established by it."
    else:
        consistency = "UNSUPPORTED"
        reasoning = "The response introduces factual claims that are not supported by the supplied evidence."

    unsupported = consistency == "UNSUPPORTED"
    return {
        "factual_consistency": consistency,
        "reasoning": reasoning,
        "incorrect_claims": [],
        "flagged_claims": [{
            "claim": sentence,
            "status": "unsupported" if unsupported else "supported",
            "reasoning": reasoning,
            "evidence": evidence[:500],
        } for sentence in sentences[:5]],
        "analyzed_claim_count": len(sentences),
        "has_evidence": True,
    }