from app.pipeline.route import CONFIDENCE_REVIEW_THRESHOLD, route_lead
from app.pipeline.schemas import ClassificationResult


def test_high_confidence_decision_maker_routes_to_decision_maker_queue():
    result = route_lead(ClassificationResult(category="decision_maker", confidence=0.9, reasoning="x"))
    assert result.queue == "decision_maker_queue"


def test_high_confidence_technical_routes_to_technical_queue():
    result = route_lead(ClassificationResult(category="technical", confidence=0.85, reasoning="x"))
    assert result.queue == "technical_queue"


def test_not_relevant_routes_to_discard():
    result = route_lead(ClassificationResult(category="not_relevant", confidence=0.9, reasoning="x"))
    assert result.queue == "discard"


def test_low_confidence_always_routes_to_needs_review_regardless_of_category():
    result = route_lead(
        ClassificationResult(category="decision_maker", confidence=CONFIDENCE_REVIEW_THRESHOLD - 0.01, reasoning="x")
    )
    assert result.queue == "needs_review"


def test_confidence_exactly_at_threshold_is_not_needs_review():
    result = route_lead(ClassificationResult(category="technical", confidence=CONFIDENCE_REVIEW_THRESHOLD, reasoning="x"))
    assert result.queue == "technical_queue"
