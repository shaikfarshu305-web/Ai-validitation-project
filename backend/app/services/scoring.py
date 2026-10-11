import math
from typing import Dict, Mapping, Tuple


DIMENSION_WEIGHTS = {
    "relevance": 0.25,
    "accuracy": 0.35,
    "hallucination_safety": 0.25,
    "completeness": 0.15,
}


def calculate_overall_score(
    scores: Mapping[str, float],
    weights: Mapping[str, float] | None = None,
) -> Tuple[float, Dict[str, float], Dict[str, float]]:
    """Normalize 0-5 judge scores once, then calculate the weighted 0-100 score."""
    configured_weights = {
        name: float((weights or DIMENSION_WEIGHTS).get(name, DIMENSION_WEIGHTS[name]))
        for name in DIMENSION_WEIGHTS
    }
    if any(not math.isfinite(weight) or weight < 0.0 for weight in configured_weights.values()):
        raise ValueError("Evaluation weights must be finite and non-negative.")
    total_weight = sum(configured_weights.values())
    if not math.isfinite(total_weight) or total_weight <= 0:
        raise ValueError("Evaluation weights must have a positive finite sum.")
    normalized_weights = {
        name: weight / total_weight for name, weight in configured_weights.items()
    }

    normalized_scores: Dict[str, float] = {}
    for name in DIMENSION_WEIGHTS:
        score = float(scores[name])
        if not math.isfinite(score):
            raise ValueError(f"The {name} score must be finite.")
        normalized_scores[name] = max(0.0, min(100.0, score * 20.0))

    overall = sum(normalized_scores[name] * normalized_weights[name] for name in DIMENSION_WEIGHTS)
    return (
        round(overall, 1),
        {name: round(score, 1) for name, score in normalized_scores.items()},
        {name: round(weight, 4) for name, weight in normalized_weights.items()},
    )


def calculate_hallucination_percentage(
    flagged_claims: list,
    analyzed_claim_count: int | None = None,
) -> float:
    """Percentage of analyzed response claims explicitly contradicted by available evidence."""
    claims = [claim for claim in flagged_claims if isinstance(claim, dict)]
    total_claims = analyzed_claim_count if analyzed_claim_count is not None else len(claims)
    if total_claims <= 0:
        return 0.0
    contradicted_claims = {
        str(claim.get("claim") or f"claim-{index}").strip().casefold()
        for index, claim in enumerate(claims)
        if claim.get("status") == "contradicted"
    }
    return round(min(len(contradicted_claims), total_claims) / total_claims * 100.0, 1)
