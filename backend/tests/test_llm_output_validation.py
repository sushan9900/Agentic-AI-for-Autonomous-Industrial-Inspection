"""Unit tests for LLM structured output validation and fabrication guards (Phase 5C)."""

import pytest
from backend.app.agents.validators import AgentValidator, LLMInvalidOutputError


def test_parse_json_with_markdown_fences():
    raw_text = '```json\n{"recommended_action": "Inspect weld", "engineering_justification": "Surface crack"}\n```'
    parsed = AgentValidator.parse_and_validate_llm_json(raw_text)
    assert parsed["recommended_action"] == "Inspect weld"
    assert parsed["engineering_justification"] == "Surface crack"


def test_parse_json_with_raw_fences():
    raw_text = '```\n{"recommended_action": "Inspect weld"}\n```'
    parsed = AgentValidator.parse_and_validate_llm_json(raw_text)
    assert parsed["recommended_action"] == "Inspect weld"


def test_fabricated_cost_and_downtime_nullified():
    raw_payload = {
        "recommended_action": "Inspect pipeline",
        "engineering_justification": "Crack indication",
        "estimated_cost": 15000.0,
        "estimated_downtime_hours": 36.0,
        "cost_notes": "Fabricated guess"
    }

    sanitized, warnings = AgentValidator.sanitize_and_ground_work_order(
        llm_raw_data=raw_payload,
        expected_inspection_id="insp-01",
        expected_image_filename="11112.jpg",
        expected_image_sha256="sha256abc",
        cost_data_available=False
    )

    assert sanitized["estimated_cost"] is None
    assert sanitized["estimated_downtime_hours"] is None
    assert "unavailable" in sanitized["cost_notes"].lower()
    assert any("fabricated cost" in w.lower() for w in warnings)
    assert any("fabricated downtime" in w.lower() for w in warnings)


def test_verified_cost_retained_when_available():
    raw_payload = {
        "recommended_action": "Inspect pipeline",
        "engineering_justification": "Crack indication",
        "estimated_cost": 2500.0,
        "estimated_downtime_hours": 4.0
    }

    sanitized, warnings = AgentValidator.sanitize_and_ground_work_order(
        llm_raw_data=raw_payload,
        expected_inspection_id="insp-01",
        expected_image_filename="11112.jpg",
        expected_image_sha256="sha256abc",
        cost_data_available=True,
        verified_cost=2500.0,
        verified_downtime_hours=4.0
    )

    assert sanitized["estimated_cost"] == 2500.0
    assert sanitized["estimated_downtime_hours"] == 4.0


def test_evidence_reference_enforcement():
    raw_payload = {
        "recommended_action": "Inspect pipeline",
        "evidence_references": {
            "inspection_id": "HALLUCINATED_INSP_ID",
            "source_image_filename": "wrong_image.png",
            "source_image_sha256": "fakehash"
        }
    }

    sanitized, warnings = AgentValidator.sanitize_and_ground_work_order(
        llm_raw_data=raw_payload,
        expected_inspection_id="insp-correct-99",
        expected_image_filename="correct_image.jpg",
        expected_image_sha256="correcthash",
        cost_data_available=False
    )

    assert sanitized["evidence_references"]["inspection_id"] == "insp-correct-99"
    assert sanitized["evidence_references"]["source_image_filename"] == "correct_image.jpg"
    assert sanitized["evidence_references"]["source_image_sha256"] == "correcthash"
    assert any("mismatched" in w.lower() for w in warnings)
