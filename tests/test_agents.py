import pytest
from app.config import migrate_legacy_default_weights
from app.agents.relevance_agent import RelevanceJudgeAgent
from app.agents.accuracy_agent import AccuracyJudgeAgent
from app.agents.hallucination_agent import HallucinationDetectionAgent
from app.agents.completeness_agent import CompletenessJudgeAgent
from app.agents.verdict_agent import VerdictAgent
from app.agents.factual_consistency import assess_factual_consistency
from app.services.scoring import calculate_overall_score
from app.orchestrator.evaluation_orchestrator import EvaluationOrchestrator
from app.schemas.evaluation_schemas import RetrievedChunk


def test_legacy_default_weights_migrate_without_changing_custom_weights():
    legacy_defaults = {
        "weight_accuracy": 0.35,
        "weight_hallucination": 0.30,
        "weight_relevance": 0.20,
        "weight_completeness": 0.15,
    }

    migrated = migrate_legacy_default_weights(legacy_defaults)
    assert migrated == {
        "weight_accuracy": 0.35,
        "weight_hallucination": 0.25,
        "weight_relevance": 0.25,
        "weight_completeness": 0.15,
    }
    custom_weights = {**legacy_defaults, "weight_accuracy": 0.40}
    assert migrate_legacy_default_weights(custom_weights) == custom_weights


def test_weighted_score_normalizes_each_dimension_once():
    overall, dimensions, weights = calculate_overall_score({
        "relevance": 5.0,
        "accuracy": 4.0,
        "hallucination_safety": 4.0,
        "completeness": 3.5,
    })

    assert dimensions == {
        "relevance": 100.0,
        "accuracy": 80.0,
        "hallucination_safety": 80.0,
        "completeness": 70.0,
    }
    assert weights == {
        "relevance": 0.25,
        "accuracy": 0.35,
        "hallucination_safety": 0.25,
        "completeness": 0.15,
    }
    assert overall == 83.5


def test_relevance_agent_direct_and_irrelevant():
    agent = RelevanceJudgeAgent()
    
    # Fully relevant
    q = "What causes ocean tides on Earth?"
    r1 = "Ocean tides on Earth are primarily caused by the gravitational pull of the Moon and the Sun."
    res1 = agent.evaluate(q, r1)
    assert res1["score"] >= 4.0
    assert "status" in res1 and res1["status"] == "SUCCESS"
    
    # Irrelevant
    r2 = "The stock market experienced heavy trading volume in tech stocks during yesterday's session."
    res2 = agent.evaluate(q, r2)
    assert res2["score"] <= 2.5
    assert len(res2["issues"]) > 0

def test_accuracy_agent_grounding():
    agent = AccuracyJudgeAgent()
    q = "At what temperature does water boil at standard sea level pressure?"
    ref = "Water boils at 100 degrees Celsius (212 degrees Fahrenheit) at sea level."
    
    # Accurate response
    r_correct = "Water boils at 100 degrees Celsius (212 Fahrenheit) under standard atmospheric pressure."
    res_correct = agent.evaluate(q, r_correct, reference_answer=ref)
    assert res_correct["score"] >= 4.0
    assert len(res_correct["supporting_evidence"]) > 0
    
    # Inaccurate response
    r_wrong = "Water boils at 45 degrees Celsius at sea level, freezing at 10 degrees."
    res_wrong = agent.evaluate(q, r_wrong, reference_answer=ref)
    assert res_wrong["score"] <= 3.0


def test_accuracy_without_evidence_is_unverified_not_supported(monkeypatch):
    monkeypatch.setattr("app.agents.accuracy_agent.llm_service.query", lambda *args: "")
    result = AccuracyJudgeAgent().evaluate(
        "What is a primary key?",
        "A primary key uniquely identifies each record in a database table.",
    )

    assert result["factual_consistency"] == "UNSUPPORTED"
    assert result["supporting_evidence"] == []
    assert "No reference" in result["reasoning"]


def test_evaluation_directive_does_not_inject_fixed_agent_scores(monkeypatch):
    monkeypatch.setattr("app.agents.accuracy_agent.llm_service.query", lambda *args: "")
    monkeypatch.setattr("app.agents.hallucination_agent.llm_service.query", lambda *args: "")
    monkeypatch.setattr("app.agents.relevance_agent.llm_service.query", lambda *args: "")
    monkeypatch.setattr("app.agents.completeness_agent.llm_service.query", lambda *args: "")

    question = "Evaluate the quality of the following answer."
    response = "This answer is clear, concise, and directly addresses the prompt with appropriate detail."
    reference = "evaution"

    accuracy = AccuracyJudgeAgent().evaluate(question, response, reference_answer=reference)
    hallucination = HallucinationDetectionAgent().evaluate(question, response, reference_answer=reference)
    relevance = RelevanceJudgeAgent().evaluate(question, response, reference_answer=reference)
    completeness = CompletenessJudgeAgent().evaluate(question, response, reference_answer=reference)
    verdict = VerdictAgent().evaluate(relevance, accuracy, hallucination, completeness)

    assert 0.0 <= accuracy["score"] <= 5.0
    assert 0.0 <= relevance["score"] <= 5.0
    assert 0.0 <= completeness["score"] <= 5.0
    assert verdict["overall_score"] <= 100.0


def test_correct_grounded_answer_receives_high_score_and_pass(monkeypatch):
    monkeypatch.setattr("app.agents.accuracy_agent.llm_service.query", lambda *args: "")
    monkeypatch.setattr("app.agents.hallucination_agent.llm_service.query", lambda *args: "")
    monkeypatch.setattr("app.agents.relevance_agent.llm_service.query", lambda *args: "")
    monkeypatch.setattr("app.agents.completeness_agent.llm_service.query", lambda *args: "")
    question = "What is photosynthesis?"
    response = "Photosynthesis is the process by which green plants use sunlight, water, and carbon dioxide to produce glucose and oxygen."
    reference = "Photosynthesis is the process by which green plants use light energy, water, and carbon dioxide to produce glucose and oxygen."

    accuracy = AccuracyJudgeAgent().evaluate(question, response, reference_answer=reference)
    hallucination = HallucinationDetectionAgent().evaluate(question, response, reference_answer=reference)
    relevance = RelevanceJudgeAgent().evaluate(question, response, reference_answer=reference)
    completeness = CompletenessJudgeAgent().evaluate(question, response, reference_answer=reference)
    verdict = VerdictAgent().evaluate(relevance, accuracy, hallucination, completeness)

    assert accuracy["factual_consistency"] == "CONSISTENT"
    assert accuracy["score"] >= 4.5
    assert hallucination["hallucination_score"] >= 4.5
    assert verdict["overall_score"] >= 90.0
    assert verdict["verdict"] == "PASS"


def test_ai_definition_example_receives_high_score_and_pass(monkeypatch):
    monkeypatch.setattr("app.agents.accuracy_agent.llm_service.query", lambda *args: "")
    monkeypatch.setattr("app.agents.hallucination_agent.llm_service.query", lambda *args: "")
    monkeypatch.setattr("app.agents.relevance_agent.llm_service.query", lambda *args: "")
    monkeypatch.setattr("app.agents.completeness_agent.llm_service.query", lambda *args: "")

    question = "What is AI?"
    response = (
        "Artificial Intelligence (AI) refers to the capability of a computer system or machine to "
        "perform tasks that typically require human intelligence. These tasks include learning, reasoning, "
        "problem-solving, understanding natural language, recognizing patterns, and making decisions."
    )
    reference = (
        "Artificial Intelligence (AI) is the ability of computers or machines to perform tasks that normally "
        "require human intelligence, such as learning, reasoning, problem solving, language understanding, "
        "and decision making."
    )

    accuracy = AccuracyJudgeAgent().evaluate(question, response, reference_answer=reference)
    hallucination = HallucinationDetectionAgent().evaluate(question, response, reference_answer=reference)
    relevance = RelevanceJudgeAgent().evaluate(question, response, reference_answer=reference)
    completeness = CompletenessJudgeAgent().evaluate(question, response, reference_answer=reference)
    verdict = VerdictAgent().evaluate(relevance, accuracy, hallucination, completeness)

    assert relevance["score"] >= 4.5
    assert accuracy["score"] >= 4.5
    assert hallucination["hallucination_score"] >= 4.5
    assert completeness["score"] >= 4.5
    assert verdict["overall_score"] >= 90.0
    assert verdict["verdict"] == "PASS"


def test_local_evaluator_scores_response_quality_across_examples(monkeypatch):
    monkeypatch.setattr("app.agents.accuracy_agent.llm_service.query", lambda *args: "")

    def evaluate(question, response, reference=None):
        accuracy = AccuracyJudgeAgent().evaluate(question, response, reference_answer=reference)
        hallucination = HallucinationDetectionAgent().evaluate(question, response, reference_answer=reference)
        relevance = RelevanceJudgeAgent().evaluate(question, response, reference_answer=reference)
        completeness = CompletenessJudgeAgent().evaluate(question, response, reference_answer=reference)
        return VerdictAgent().evaluate(relevance, accuracy, hallucination, completeness)

    excellent = evaluate(
        "What is Python?",
        "Python is a high-level, interpreted, general-purpose programming language known for its simple and readable syntax. "
        "It is widely used in web development, data science, automation, artificial intelligence, and machine learning.",
        "Python is a high-level, interpreted, general-purpose programming language known for its readability and simple syntax.",
    )
    partial = evaluate(
        "What is Python?",
        "Python is a programming language used for many types of applications. It is popular because it is easy to learn.",
    )
    incorrect = evaluate(
        "What is Python?",
        "Python is a database management system developed by Microsoft for storing tables.",
    )
    hallucinated = evaluate(
        "Who created Python?",
        "Python was created by James Gosling in 1995.",
        "Python was created by Guido van Rossum.",
    )
    irrelevant = evaluate(
        "What is machine learning?",
        "The weather is pleasant today and many people enjoy going outside.",
    )

    assert excellent["overall_score"] >= 90.0
    assert excellent["dimension_scores"]["hallucination_percentage"] == 0.0
    assert 70.0 <= partial["overall_score"] <= 85.0
    assert incorrect["overall_score"] <= 40.0 and incorrect["verdict"] == "FAIL"
    assert hallucinated["overall_score"] <= 35.0 and hallucinated["verdict"] == "FAIL"
    assert irrelevant["overall_score"] <= 55.0 and irrelevant["verdict"] == "FAIL"
    assert len({item["overall_score"] for item in (excellent, partial, incorrect, hallucinated, irrelevant)}) == 5


def test_agent_failure_has_no_fallback_score():
    fallback = EvaluationOrchestrator()._make_fallback("AccuracyJudge", "service unavailable")

    assert fallback["status"] == "FAILED"
    assert "score" not in fallback
    assert "overall_score" not in fallback


@pytest.mark.parametrize(("question", "reference", "response"), [
    (
        "Who created Python?",
        "Python was created by Guido van Rossum.",
        "Python was created by James Gosling in 1995.",
    ),
    (
        "What is Natural Language Processing?",
        "NLP is a branch of AI that enables computers to process and understand human language.",
        "NLP is a programming language developed by Microsoft for Android application development.",
    ),
    (
        "What is a primary key?",
        "A primary key uniquely identifies each record in a database and cannot contain duplicate values.",
        "A primary key allows duplicate values and is used mainly to store images.",
    ),
    (
        "What is machine learning?",
        "Machine learning allows systems to learn patterns from data and make predictions or decisions.",
        "Machine learning means manually writing every possible rule that a computer must follow.",
    ),
    (
        "What is RAG?",
        "RAG retrieves relevant information from an external knowledge source and provides it to a language model before generating an answer.",
        "RAG is a programming language used to create websites.",
    ),
])
def test_accuracy_rejects_major_reference_contradictions(question, reference, response, monkeypatch):
    monkeypatch.setattr("app.agents.accuracy_agent.llm_service.query", lambda *args: "")
    result = AccuracyJudgeAgent().evaluate(question, response, reference_answer=reference)

    assert result["score"] <= 1.5
    assert result["factual_consistency"] == "CONTRADICTORY"
    assert result["incorrect_claims"]


def test_factual_consistency_identifies_creator_contradiction():
    result = assess_factual_consistency(
        "Who created Python?",
        "Python was created by James Gosling. It is primarily used to store relational tables.",
        ["Python was created by Guido van Rossum."],
    )

    assert result["factual_consistency"] == "CONTRADICTORY"
    assert "James Gosling" in result["reasoning"]
    assert "Guido van Rossum" in result["reasoning"]
    assert result["analyzed_claim_count"] == 2


def test_hallucination_percentage_uses_all_analyzed_claims():
    result = VerdictAgent().evaluate(
        {"score": 4.0},
        {"score": 3.0},
        {
            "hallucination_score": 2.0,
            "hallucination_status": "HIGH",
            "flagged_claims": [{"claim": "Incorrect creator", "status": "contradicted"}],
            "analyzed_claim_count": 4,
        },
        {"score": 4.0},
    )

    assert result["dimension_scores"]["hallucination_percentage"] == 25.0


@pytest.mark.parametrize(("question", "reference", "response"), [
    (
        "Who created Python?",
        "Python was created by Guido van Rossum.",
        "Python was created by James Gosling in 1995.",
    ),
    (
        "What is Natural Language Processing?",
        "NLP is a branch of AI that enables computers to process and understand human language.",
        "NLP is a programming language developed by Microsoft for Android application development.",
    ),
    (
        "What is a primary key?",
        "A primary key uniquely identifies each record in a database and cannot contain duplicate values.",
        "A primary key allows duplicate values and is used mainly to store images.",
    ),
    (
        "What is machine learning?",
        "Machine learning allows systems to learn patterns from data and make predictions or decisions.",
        "Machine learning means manually writing every possible rule that a computer must follow.",
    ),
    (
        "What is RAG?",
        "RAG retrieves relevant information from an external knowledge source and provides it to a language model before generating an answer.",
        "RAG is a programming language used to create websites.",
    ),
])
def test_hallucination_agent_flags_reference_contradictions(question, reference, response, monkeypatch):
    monkeypatch.setattr("app.agents.hallucination_agent.llm_service.query", lambda *args: "")
    result = HallucinationDetectionAgent().evaluate(question, response, reference_answer=reference)

    assert result["hallucination_status"] == "HIGH"
    assert result["hallucination_score"] <= 1.5
    assert result["factual_consistency"] == "CONTRADICTORY"
    assert any(claim["status"] == "contradicted" for claim in result["flagged_claims"])


@pytest.mark.parametrize(("question", "reference", "response"), [
    (
        "Who created Python?",
        "Python was created by Guido van Rossum.",
        "Python was created by James Gosling in 1995.",
    ),
    (
        "What is Natural Language Processing?",
        "NLP is a branch of AI that enables computers to process and understand human language.",
        "NLP is a programming language developed by Microsoft for Android application development.",
    ),
    (
        "What is a primary key?",
        "A primary key uniquely identifies each record in a database and cannot contain duplicate values.",
        "A primary key allows duplicate values and is used mainly to store images.",
    ),
    (
        "What is machine learning?",
        "Machine learning allows systems to learn patterns from data and make predictions or decisions.",
        "Machine learning means manually writing every possible rule that a computer must follow.",
    ),
    (
        "What is RAG?",
        "RAG retrieves relevant information from an external knowledge source and provides it to a language model before generating an answer.",
        "RAG is a programming language used to create websites.",
    ),
])
def test_confident_llm_cannot_override_factual_contradiction(question, reference, response, monkeypatch):
    def confident_but_wrong(prompt, system_prompt):
        if "Hallucination Detection Agent" in system_prompt:
            return '{"hallucination_status":"LOW","hallucination_score":5,"flagged_claims":[],"reasoning":"No issue found."}'
        return '{"score":5,"reasoning":"Fully correct.","supporting_evidence":[],"incorrect_claims":[]}'

    monkeypatch.setattr("app.agents.accuracy_agent.llm_service.query", confident_but_wrong)
    accuracy = AccuracyJudgeAgent().evaluate(question, response, reference_answer=reference)
    hallucination = HallucinationDetectionAgent().evaluate(question, response, reference_answer=reference)
    verdict = VerdictAgent().evaluate(
        {"score": 4.5},
        accuracy,
        hallucination,
        {"score": 4.5},
    )

    assert accuracy["score"] <= 1.0
    assert hallucination["hallucination_status"] == "HIGH"
    assert hallucination["hallucination_score"] <= 1.0
    assert verdict["verdict"] == "FAIL"
    assert verdict["overall_score"] < 50.0


@pytest.mark.parametrize(("question", "reference", "response"), [
    (
        "What is Natural Language Processing?",
        "NLP is a branch of AI that enables computers to process and understand human language.",
        "NLP is a programming language developed by Microsoft for Android application development.",
    ),
    (
        "What is RAG?",
        "RAG retrieves relevant information from an external knowledge source and provides it to a language model before generating an answer.",
        "RAG is a programming language used to create websites.",
    ),
])
def test_relevance_penalizes_contradictory_definitions(question, reference, response, monkeypatch):
    monkeypatch.setattr("app.agents.relevance_agent.llm_service.query", lambda *args: "")
    result = RelevanceJudgeAgent().evaluate(question, response, reference_answer=reference)

    assert result["score"] <= 2.0
    assert result["factual_consistency"] == "CONTRADICTORY"

def test_hallucination_agent_claims_breakdown():
    agent = HallucinationDetectionAgent()
    q = "Can you see the Great Wall of China from the Moon?"
    ref = "The Great Wall of China is NOT visible from space or the Moon with the unaided eye. It is an urban myth."
    
    # Hallucinated response
    r_halluc = "Yes, the Great Wall of China is famously visible from space and the Moon without any equipment."
    res = agent.evaluate(q, r_halluc, reference_answer=ref)
    assert res["hallucination_status"] in ["MEDIUM", "HIGH"]
    assert len(res["flagged_claims"]) > 0
    # Check claim classification
    statuses = [c["status"] for c in res["flagged_claims"]]
    assert "contradicted" in statuses or "unsupported" in statuses

def test_completeness_agent_multi_part():
    agent = CompletenessJudgeAgent()
    q = "Explain the cause of earthquakes and how they are measured."
    
    # Complete response
    r_full = "Earthquakes are caused by sudden tectonic plate movements along faults, releasing seismic energy. They are measured using seismographs on the moment magnitude scale."
    res_full = agent.evaluate(q, r_full)
    assert res_full["score"] >= 4.0
    assert len(res_full["addressed_aspects"]) >= 1
    
    # Incomplete response
    r_partial = "Earthquakes are caused by tectonic plate friction."
    res_partial = agent.evaluate(q, r_partial)
    assert len(res_partial["missing_aspects"]) > 0


def test_completeness_penalizes_partial_reference_coverage(monkeypatch):
    monkeypatch.setattr("app.agents.completeness_agent.llm_service.query", lambda *args: "")
    result = CompletenessJudgeAgent().evaluate(
        "What is supervised learning?",
        "Supervised learning is a machine learning technique that learns from data.",
        reference_answer="Supervised learning uses labeled training data containing input-output pairs.",
    )

    assert result["score"] <= 4.2
    assert result["missing_aspects"] == []

def test_verdict_agent_critical_override():
    agent = VerdictAgent()
    
    # Severe hallucination override test
    rel = {"score": 5.0}
    acc = {"score": 1.0, "incorrect_claims": ["False fact"]}
    hal = {
        "hallucination_score": 1.0,
        "hallucination_status": "HIGH",
        "flagged_claims": [{"claim": "Disproved claim", "status": "contradicted"}]
    }
    comp = {"score": 4.0}
    
    verdict_res = agent.evaluate(rel, acc, hal, comp)
    assert verdict_res["verdict"] == "FAIL"
    assert len(verdict_res["major_issues"]) > 0


def test_verdict_fails_explicit_contradiction_even_with_high_scores():
    result = VerdictAgent().evaluate(
        {"score": 4.8},
        {
            "score": 4.8,
            "factual_consistency": "CONTRADICTORY",
            "incorrect_claims": ["The response names James Gosling, but the reference names Guido van Rossum."],
        },
        {"hallucination_score": 4.8, "hallucination_status": "LOW", "flagged_claims": []},
        {"score": 4.8},
    )

    assert result["verdict"] == "FAIL"
    assert result["overall_score"] == 96.0
    assert any("James Gosling" in issue and "Guido van Rossum" in issue for issue in result["major_issues"])


def test_critical_verdict_does_not_mutate_weighted_score():
    result = VerdictAgent().evaluate(
        {"score": 5.0},
        {
            "score": 4.0,
            "factual_consistency": "CONTRADICTORY",
            "incorrect_claims": ["A verified factual contradiction."],
        },
        {
            "hallucination_score": 4.0,
            "hallucination_status": "HIGH",
            "flagged_claims": [{"status": "contradicted", "reasoning": "Verified contradiction."}],
        },
        {"score": 3.5},
    )

    assert result["overall_score"] == 83.5
    assert result["verdict"] == "FAIL"
    assert result["dimension_scores"]["hallucination_percentage"] == 100.0


def test_verdict_fails_irrelevant_response():
    result = VerdictAgent().evaluate(
        {"score": 0.5, "reasoning": "The response is off-topic."},
        {"score": 1.0, "factual_consistency": "UNSUPPORTED", "incorrect_claims": []},
        {"hallucination_score": 1.0, "hallucination_status": "HIGH", "flagged_claims": []},
        {"score": 0.5},
    )

    assert result["verdict"] == "FAIL"
    assert result["overall_score"] < 50.0


def test_verdict_uses_weighted_threshold_for_partially_grounded_answer():
    result = VerdictAgent().evaluate(
        {"score": 5.0},
        {"score": 3.5, "factual_consistency": "PARTIALLY_CONSISTENT", "incorrect_claims": []},
        {"hallucination_score": 5.0, "hallucination_status": "LOW", "flagged_claims": []},
        {"score": 2.5},
    )

    assert result["verdict"] == "PASS"
    assert result["overall_score"] == 82.0
    assert result["dimension_scores"]["hallucination_percentage"] == 0.0
