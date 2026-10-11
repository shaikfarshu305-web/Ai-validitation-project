import time
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent
from app.config import settings
from app.services.scoring import calculate_hallucination_percentage, calculate_overall_score

class VerdictAgent(BaseAgent):
    """
    Synthesizes dimension scores into an overall score (0-100) and authoritative verdict:
    - PASS (High accuracy, grounded, relevant, complete)
    - NEEDS IMPROVEMENT (Moderate omissions, partial relevance, or minor unverified points)
    - FAIL (Severe factual inaccuracy, contradictions, or low overall score)
    Applies configurable weights and critical hallucination overrides.
    """
    def __init__(self):
        super().__init__("VerdictAgent")

    def evaluate(
        self,
        relevance_data: Dict[str, Any],
        accuracy_data: Dict[str, Any],
        hallucination_data: Dict[str, Any],
        completeness_data: Dict[str, Any],
        custom_weights: Optional[Dict[str, float]] = None,
        custom_thresholds: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        start_time = time.time()

        weights = {
            "accuracy": custom_weights.get("accuracy", settings.DEFAULT_WEIGHT_ACCURACY) if custom_weights else settings.DEFAULT_WEIGHT_ACCURACY,
            "hallucination_safety": custom_weights.get("hallucination", settings.DEFAULT_WEIGHT_HALLUCINATION) if custom_weights else settings.DEFAULT_WEIGHT_HALLUCINATION,
            "relevance": custom_weights.get("relevance", settings.DEFAULT_WEIGHT_RELEVANCE) if custom_weights else settings.DEFAULT_WEIGHT_RELEVANCE,
            "completeness": custom_weights.get("completeness", settings.DEFAULT_WEIGHT_COMPLETENESS) if custom_weights else settings.DEFAULT_WEIGHT_COMPLETENESS,
        }

        # Thresholds
        t_pass = custom_thresholds.get("pass", settings.DEFAULT_THRESHOLD_PASS) if custom_thresholds else settings.DEFAULT_THRESHOLD_PASS
        t_needs = custom_thresholds.get("needs_improvement", settings.DEFAULT_THRESHOLD_NEEDS_IMPROVEMENT) if custom_thresholds else settings.DEFAULT_THRESHOLD_NEEDS_IMPROVEMENT

        rel_score = float(relevance_data.get("score", 0.0))
        acc_score = float(accuracy_data.get("score", 0.0))
        hal_score = float(hallucination_data.get("hallucination_score", 0.0))
        com_score = float(completeness_data.get("score", 0.0))

        overall_score, normalized_scores, normalized_weights = calculate_overall_score({
            "relevance": rel_score,
            "accuracy": acc_score,
            "hallucination_safety": hal_score,
            "completeness": com_score,
        }, weights)
        rel_norm = normalized_scores["relevance"]
        acc_norm = normalized_scores["accuracy"]
        hal_norm = normalized_scores["hallucination_safety"]
        com_norm = normalized_scores["completeness"]
        hallucination_percentage = calculate_hallucination_percentage(
            hallucination_data.get("flagged_claims", []),
            hallucination_data.get("analyzed_claim_count"),
        )

        # Hallucination Safety & Contradiction Check
        flagged_claims = hallucination_data.get("flagged_claims", [])
        contradicted_claims = [c for c in flagged_claims if c.get("status") == "contradicted"]
        unsupported_claims = [c for c in flagged_claims if c.get("status") == "unsupported"]
        incorrect_claims = accuracy_data.get("incorrect_claims", [])
        factual_consistency = accuracy_data.get("factual_consistency") or hallucination_data.get("factual_consistency")
        major_issues = []
        recommendations = []

        # Check for Critical Overrides
        critical_override_fail = False

        if contradicted_claims or factual_consistency == "CONTRADICTORY":
            critical_override_fail = True
            contradiction_details = [claim.get("reasoning", claim.get("claim", "")) for claim in contradicted_claims]
            contradiction_details.extend(incorrect_claims)
            detail = "; ".join(dict.fromkeys(item for item in contradiction_details if item))
            major_issues.append(f"Major factual contradiction: {detail or 'A response claim conflicts with verified ground truth.'}")
            recommendations.append("Immediately retract or correct claims flagged with 'contradicted' status.")

        if hal_score <= 1.5 and hallucination_data.get("hallucination_status") == "HIGH":
            critical_override_fail = True
            major_issues.append("Severe hallucination rate detected; response contains excessive unsupported or fabricated claims.")
            recommendations.append("Ground the generative model using stricter RAG temperature and retrieval parameters.")

        if acc_score <= 1.5:
            critical_override_fail = True
            major_issues.append("Factual accuracy is critically low; multiple claims fail verification.")
            recommendations.append("Cross-reference factual outputs against verified knowledge corpora.")

        if rel_score <= 1.0:
            critical_override_fail = True
            major_issues.append("The response does not answer the submitted question and is substantially off-topic.")
            recommendations.append("Replace the response with a direct answer to the submitted question.")
        elif rel_score <= 2.0:
            major_issues.append("Response fails to adequately address the submitted question prompt.")
            recommendations.append("Align response structure directly with user prompt interrogatives.")

        if com_score <= 2.0:
            missing = completeness_data.get("missing_aspects", [])
            major_issues.append(f"Response omits critical sub-questions: {', '.join(missing[:2])}")
            recommendations.append("Ensure every clause in multi-part inquiries is comprehensively answered.")

        # Determine Verdict
        if critical_override_fail:
            verdict = "FAIL"
            summary = (
                f"VERDICT: FAIL (Critical quality override). The response produced "
                f"severe factual contradictions or high hallucination frequency. "
                f"{major_issues[0]} Weighted score: {overall_score}/100 from accuracy {acc_norm:.1f}, "
                f"relevance {rel_norm:.1f}, completeness {com_norm:.1f}, and hallucination quality "
                f"{hal_norm:.1f} (verified contradicted claims {hallucination_percentage:.1f}%)."
            )
        elif overall_score >= t_pass:
            verdict = "PASS"
            if overall_score >= 90.0:
                grade = "EXCELLENT"
            elif overall_score >= 80.0:
                grade = "VERY GOOD"
            else:
                grade = "GOOD"
            summary = (
                f"{grade} / PASS. Weighted score {overall_score}/100 from accuracy {acc_norm:.1f}, "
                f"relevance {rel_norm:.1f}, completeness {com_norm:.1f}, and hallucination quality "
                f"{hal_norm:.1f} (verified contradicted claims {hallucination_percentage:.1f}%)."
            )
            recommendations.append("The response meets the configured quality threshold.")
        elif overall_score >= t_needs:
            verdict = "NEEDS_IMPROVEMENT"
            summary = (
                f"NEEDS IMPROVEMENT. Weighted score {overall_score}/100 from accuracy {acc_norm:.1f}, "
                f"relevance {rel_norm:.1f}, completeness {com_norm:.1f}, and hallucination quality "
                f"{hal_norm:.1f} (verified contradicted claims {hallucination_percentage:.1f}%)."
            )
            recommendations.append("Revise flagged sections to enhance factual coverage and remove ambiguous extrapolations.")
        else:
            verdict = "FAIL"
            summary = (
                f"FAIL. Weighted score {overall_score}/100 is below the minimum quality threshold of {t_needs}. "
                f"Accuracy {acc_norm:.1f}, relevance {rel_norm:.1f}, completeness {com_norm:.1f}, and "
                f"hallucination quality {hal_norm:.1f} (verified contradicted claims {hallucination_percentage:.1f}%)."
            )
            recommendations.append("Regenerate response with grounded evidence context.")

        if not recommendations:
            recommendations.append("Continuous monitoring recommended.")

        return {
            "overall_score": overall_score,
            "verdict": verdict,
            "dimension_scores": {
                "accuracy": round(acc_norm, 1),
                "hallucination_safety": round(hal_norm, 1),
                "hallucination_percentage": hallucination_percentage,
                "relevance": round(rel_norm, 1),
                "completeness": round(com_norm, 1)
            },
            "weights": normalized_weights,
            "major_issues": major_issues,
            "recommendations": recommendations,
            "summary": summary,
            "execution_time_ms": round((time.time() - start_time) * 1000, 2),
            "status": "SUCCESS"
        }
