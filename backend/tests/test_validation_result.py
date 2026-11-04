
import pytest

from app.models.validation_result import ValidationResult
from pydantic import ValidationError


def valid_result():
    return {
        "id": "V001",
        "trip_id": "T001",
        "version": 1,
        "rule": "budget",
        "passed": False,
        "severity": "hard",
        "message": "Trip exceeds the budget",
        "activity_ids": ["A001"],
    }


def test_valid_result():
    result = ValidationResult(**valid_result())

    assert result.rule == "budget"
    assert result.passed is False
    assert result.severity == "hard"


def test_all_severity_values():
    for severity in ["hard", "soft", "data-gap"]:
        data = valid_result()
        data["severity"] = severity

        result = ValidationResult(**data)

        assert result.severity == severity


def test_invalid_severity():
    data = valid_result()
    data["severity"] = "error"

    with pytest.raises(ValidationError):
        ValidationResult(**data)


def test_missing_message():
    data = valid_result()
    data.pop("message")

    with pytest.raises(ValidationError):
        ValidationResult(**data)


def test_empty_activity_ids():
    data = valid_result()
    data["activity_ids"] = []

    result = ValidationResult(**data)

    assert result.activity_ids == []
