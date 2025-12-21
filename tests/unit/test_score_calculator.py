import pytest

def _calc():
    from src.core.score_calculator import ScoreCalculator

    return ScoreCalculator()


def _api():
    from src.core.score_calculator import calculate_score

    return calculate_score


def _error_type():
    from src.core.score_calculator import ScoreCalculationError

    return ScoreCalculationError


class TestScoreCalculatorConditional:
    def test_conditional_rule_pass_and_fail(self):
        calc = _calc()
        rules = [{"when": "correct == True", "then": 10}, {"when": "correct == False", "then": 5}]

        result1 = calc.calculate(rules, {"correct": True})
        assert result1.total == 10
        assert result1.details["rule_0"]["passed"] is True
        assert result1.details["rule_1"]["passed"] is False

        result2 = calc.calculate(rules, {"correct": False})
        assert result2.total == 5

    def test_conditional_rule_then_cast_to_int(self):
        result = _calc().calculate([{"when": "True", "then": "7"}], {})
        assert result.total == 7

    def test_invalid_expression_non_strict_records_error(self):
        result = _calc().calculate([{"when": "invalid syntax !@#", "then": 10}], {})
        assert result.total == 0
        assert "error" in result.details["rule_0"]

    def test_invalid_expression_strict_raises(self):
        ScoreCalculationError = _error_type()
        with pytest.raises(ScoreCalculationError):
            _calc().calculate([{"when": "invalid syntax !@#", "then": 10}], {}, strict=True)


class TestScoreCalculatorRange:
    def test_range_rule_match_first_range(self):
        rules = [
            {
                "type": "range",
                "field": "mistakes",
                "ranges": [{"max": 0, "score": 10}, {"max": 2, "score": 5}, {"min": 3, "score": 0}],
                "default": 1,
            }
        ]
        result = _calc().calculate(rules, {"mistakes": 0})
        assert result.total == 10
        assert result.details["rule_0"]["matched"] is True

    def test_range_rule_default_when_no_match(self):
        rules = [
            {
                "type": "range",
                "field": "x",
                "ranges": [{"min": 10, "max": 20, "score": 3}],
                "default": 1,
            }
        ]
        result = _calc().calculate(rules, {"x": 0})
        assert result.total == 1
        assert result.details["rule_0"]["matched"] is False

    def test_range_rule_missing_field_error_non_strict(self):
        rules = [{"type": "range", "field": "missing", "ranges": [{"max": 1, "score": 1}]}]
        result = _calc().calculate(rules, {"other": 1})
        assert result.total == 0
        assert "error" in result.details["rule_0"]

    def test_range_rule_type_error_strict(self):
        rules = [{"type": "range", "field": "x", "ranges": "not-a-list"}]
        ScoreCalculationError = _error_type()
        with pytest.raises(ScoreCalculationError):
            _calc().calculate(rules, {"x": 1}, strict=True)


class TestScoreCalculatorClampAndEdges:
    def test_clamp_total_rule(self):
        rules = [{"when": "True", "then": 10}, {"type": "clamp_total", "max": 5}]
        result = _calc().calculate(rules, {})
        assert result.total == 5
        assert result.details["rule_1"]["before"] == 10
        assert result.details["rule_1"]["after"] == 5

    def test_rules_none_returns_zero(self):
        result = _calc().calculate(None, {})
        assert result.total == 0
        assert result.details == {}

    def test_non_dict_rule_non_strict(self):
        result = _calc().calculate([1], {})
        assert result.total == 0
        assert "error" in result.details["rule_0"]

    def test_unknown_type_strict_raises(self):
        ScoreCalculationError = _error_type()
        with pytest.raises(ScoreCalculationError):
            _calc().calculate([{"type": "unknown"}], {}, strict=True)

    def test_function_api_calculate_score(self):
        calculate_score = _api()
        result = calculate_score([{"when": "a == 1", "then": 2}], {"a": 1})
        assert result.total == 2
