import re
from typing import Any, Dict, List, Optional


_STOP_WORDS = {
    "the", "and", "are", "was", "were", "is", "a", "an", "of", "to", "in", "on",
    "for", "with", "that", "this", "it", "as", "by", "from", "at", "be", "can",
    "which", "their", "they", "these", "those", "before", "after", "into", "used",
    "use", "mainly", "each", "every", "its", "all", "or", "such", "than", "then",
    "what", "when", "where", "who", "whom", "whose", "why", "how", "does", "did",
    "not", "no", "yes", "also", "about", "explain", "describe", "tell", "answer",
}
_NEGATION = re.compile(r"\b(?:not|never|cannot|can't|doesn't|don't|isn't|aren't|no)\b", re.I)
_PERSON_AFTER_BY = re.compile(
    r"\bby\s+([A-Z][a-z]+(?:\s+(?:van|von|de|del|da|di|la|le)\s+[A-Z][a-z]+|\s+[A-Z][a-z]+)*)"
)
_DEFINITION = re.compile(
    r"\b(?:is|are|means|refers to|is defined as)\s+(?:a|an|the)?\s*"
    r"([a-z]+(?:\s+[a-z]+){0,2})",
    re.I,
)
_SYNONYMS = {
    "axial": "axis", "tilted": "tilt", "inclined": "tilt",
    "solar": "sun", "sunlight": "light", "lunar": "moon",
    "gravitational": "gravity", "attraction": "gravity", "pull": "gravity",
    "collide": "collide", "collides": "collide", "collided": "collide",
    "collision": "collide", "collisions": "collide",
    "sea": "ocean", "oceans": "ocean", "tides": "tide", "tidal": "tide",
    "raises": "rise", "raised": "rise", "rises": "rise", "increases": "rise",
    "lowers": "fall", "lowered": "fall", "falls": "fall", "decreases": "fall",
    "generates": "produce", "generated": "produce", "produces": "produce",
    "produced": "produce", "creates": "produce", "created": "produce",
    "converts": "convert", "converted": "convert", "turns": "convert",
    "utilize": "use", "utilizes": "use", "employs": "use",
    "glucose": "sugar", "sugars": "sugar", "co2": "carbon_dioxide",
    "learns": "learn", "learned": "learn", "learning": "learn",
    "patterns": "pattern", "predictions": "prediction", "decisions": "decision",
    "identifies": "identify", "identified": "identify", "records": "record",
    "causes": "cause", "caused": "cause", "because": "cause", "reason": "cause",
    "forces": "cause", "force": "cause",
    "ai": "artificial_intelligence", "ml": "machine_learning", "nlp": "language_processing",
    "capability": "ability", "normally": "typical", "typically": "typical",
}
_CONTRADICTION_TERMS = (
    ({"unique", "uniquely"}, {"duplicate", "duplicates"}),
    ({"increase", "rise"}, {"decrease", "fall"}),
    ({"visible"}, {"invisible"}),
    ({"alive"}, {"dead"}),
)
_DEFINITION_CLASSES = (
    (re.compile(r"\b(?:learn|learning|train|training|patterns?)\b.*\b(?:data|examples)\b", re.I), "data-driven learning approach"),
    (re.compile(r"\b(?:manually|manual|hand-written|predefined)\b.*\brules?\b", re.I), "manual rule-based approach"),
    (re.compile(r"\bprogramming language\b", re.I), "programming language"),
    (re.compile(r"\b(?:database management system|database management software|dbms)\b", re.I), "database management system"),
    (re.compile(r"\boperating system\b", re.I), "operating system"),
    (re.compile(r"\bprimary key\b.*\buniquely identifies\b", re.I), "unique database identifier"),
    (re.compile(r"\b(?:branch|field|area|discipline) of (?:artificial intelligence|ai)\b", re.I), "AI field"),
    (re.compile(r"\b(retriev\w*|fetch\w*)\b.*\b(?:knowledge|document|source|information)\b", re.I), "information retrieval method"),
)


def _content_words(text: str) -> set[str]:
    text = re.sub(r"\bsea levels?\b", "tide", text, flags=re.I)
    text = re.sub(r"\bmachine learning\b", "machine_learning", text, flags=re.I)
    text = re.sub(r"\bartificial intelligence\b", "artificial_intelligence", text, flags=re.I)
    text = re.sub(r"\bnatural language processing\b", "language_processing", text, flags=re.I)
    text = re.sub(r"\bcarbon dioxide\b", "carbon_dioxide", text, flags=re.I)
    words = re.findall(r"[a-z0-9_]+", text.lower())
    normalized = set()
    for word in words:
        word = _SYNONYMS.get(word, word)
        if "_" not in word and len(word) > 5 and word.endswith("ing"):
            word = word[:-3]
            if word.endswith(("v", "z")):
                word += "e"
        elif "_" not in word and len(word) > 4 and word.endswith("ed"):
            word = word[:-2]
            if word.endswith(("at", "iz")):
                word += "e"
        elif "_" not in word and len(word) > 4 and word.endswith("ies"):
            word = word[:-3] + "y"
        elif "_" not in word and len(word) > 4 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
            word = word[:-1]
        normalized.add(word)
    return {
        word for word in normalized
        if word not in _STOP_WORDS and len(word) > 1
    }


def _definition_class(text: str) -> Optional[str]:
    for pattern, name in _DEFINITION_CLASSES:
        if pattern.search(text):
            return name
    return None


def _person_claim(text: str) -> Optional[str]:
    match = _PERSON_AFTER_BY.search(text)
    return re.sub(r"\s+", " ", match.group(1)) if match else None


def _sentence_parts(text: str) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    parts = [
        part.strip()
        for sentence in sentences
        for part in re.split(
            r"\s*;\s*|\s+(?:and|but)\s+(?=(?:the|it|they|this|that)\b)",
            sentence,
            flags=re.I,
        )
        if part.strip()
    ]
    return parts


def _best_evidence(claim: str, evidence_sentences: List[str]) -> tuple[str, float, int]:
    claim_words = _content_words(claim)
    best_sentence = ""
    best_ratio = 0.0
    best_overlap = 0
    for sentence in evidence_sentences:
        evidence_words = _content_words(sentence)
        overlap = len(claim_words & evidence_words)
        ratio = overlap / max(1, len(claim_words))
        if (ratio, overlap) > (best_ratio, best_overlap):
            best_sentence, best_ratio, best_overlap = sentence, ratio, overlap
    return best_sentence, best_ratio, best_overlap


def _contradiction_reason(question: str, claim: str, evidence: str, overlap: int) -> Optional[str]:
    if not evidence or overlap == 0:
        return None

    reference_person = _person_claim(evidence)
    response_person = _person_claim(claim)
    who_question = bool(re.match(r"\s*(?:who|which person)\b", question, re.I))
    if who_question and reference_person and response_person and reference_person.casefold() != response_person.casefold():
        return f"The response names {response_person}, but the reference names {reference_person}."

    reference_class = _definition_class(evidence)
    response_class = _definition_class(claim)
    if reference_class and response_class and reference_class != response_class:
        return f"The response defines the subject as {response_class}; the reference describes it as {reference_class}."

    reference_words = _content_words(evidence)
    claim_words = _content_words(claim)
    if overlap >= 2 and bool(_NEGATION.search(evidence)) != bool(_NEGATION.search(claim)):
        return "The claim reverses the reference's positive/negative assertion about the same facts."

    for left, right in _CONTRADICTION_TERMS:
        if (claim_words & left and reference_words & right) or (claim_words & right and reference_words & left):
            return "The claim asserts the opposite of a fact stated in the reference."

    reference_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", evidence))
    claim_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", claim))
    number_question = bool(re.search(r"\b(?:when|what year|how many|how much|what temperature|how old)\b", question, re.I))
    if reference_numbers and claim_numbers and not reference_numbers.intersection(claim_numbers):
        if number_question or overlap >= 2:
            return (
                f"The response gives {', '.join(sorted(claim_numbers))}, "
                f"while the reference gives {', '.join(sorted(reference_numbers))}."
            )
    return None


def assess_claims(question: str, response: str, evidence_texts: List[str]) -> Dict[str, Any]:
    """Classify each answer sentence against the closest supplied evidence sentence."""
    evidence = [part for text in evidence_texts if text and text.strip() for part in _sentence_parts(text)]
    claims = _sentence_parts(response)
    if not claims and response.strip():
        claims = [response.strip()]

    assessments: List[Dict[str, str]] = []
    for claim in claims:
        evidence_sentence, similarity, overlap = _best_evidence(claim, evidence)
        contradiction = _contradiction_reason(question, claim, evidence_sentence, overlap)
        if not evidence:
            status = "unverifiable"
            reasoning = "No reference, source material, or relevant retrieved evidence was available to verify this claim."
            supporting = ""
        elif contradiction:
            status = "incorrect"
            reasoning = contradiction
            supporting = evidence_sentence
        elif similarity >= 0.6:
            status = "correct"
            reasoning = "The claim is supported by the closest matching reference evidence."
            supporting = evidence_sentence
        elif similarity >= 0.3:
            status = "partially_correct"
            reasoning = "Some key concepts match the evidence, but the full claim is not established by it."
            supporting = evidence_sentence
        else:
            status = "unverifiable"
            reasoning = "The available evidence does not establish or contradict this claim."
            supporting = evidence_sentence
        assessment = {
            "claim": claim,
            "status": status,
            "reasoning": reasoning,
        }
        if supporting:
            assessment["evidence"] = supporting
        assessments.append(assessment)

    statuses = [claim["status"] for claim in assessments]
    if "incorrect" in statuses:
        consistency = "CONTRADICTORY"
        reasoning = " ".join(claim["reasoning"] for claim in assessments if claim["status"] == "incorrect")
    elif statuses and all(status == "correct" for status in statuses):
        consistency = "CONSISTENT"
        reasoning = "All evaluated factual claims are supported by the supplied evidence."
    elif "correct" in statuses or "partially_correct" in statuses:
        consistency = "PARTIALLY_CONSISTENT"
        reasoning = "Some claims align with the evidence, while other details are incomplete or unverified."
    else:
        consistency = "UNSUPPORTED"
        reasoning = "No response claims could be verified against the supplied evidence."

    return {
        "factual_consistency": consistency,
        "reasoning": reasoning,
        "claims": assessments,
        "incorrect_claims": [
            claim["reasoning"] for claim in assessments if claim["status"] == "incorrect"
        ],
        "analyzed_claim_count": len(assessments),
        "has_evidence": bool(evidence),
    }


def assess_factual_consistency(
    question: str,
    response: str,
    evidence_texts: List[str],
) -> Dict[str, Any]:
    """Compatibility wrapper exposing the established consistency result shape."""
    analysis = assess_claims(question, response, evidence_texts)
    hallucination_status = {
        "correct": "supported",
        "partially_correct": "unsupported",
        "incorrect": "contradicted",
        "unverifiable": "unsupported",
    }
    return {
        "factual_consistency": analysis["factual_consistency"],
        "reasoning": analysis["reasoning"],
        "incorrect_claims": analysis["incorrect_claims"],
        "flagged_claims": [
            {**claim, "status": hallucination_status[claim["status"]]}
            for claim in analysis["claims"]
        ],
        "analyzed_claim_count": analysis["analyzed_claim_count"],
        "has_evidence": analysis["has_evidence"],
        "claim_assessments": analysis["claims"],
    }
