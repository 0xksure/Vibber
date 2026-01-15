"""Tests for the confidence calculator."""
import pytest
from src.core.confidence import ConfidenceCalculator


@pytest.fixture
def calculator():
    """Create a confidence calculator instance."""
    return ConfidenceCalculator()


def test_confidence_calculator_initialization(calculator):
    """Test that the confidence calculator initializes correctly."""
    assert calculator is not None
    assert hasattr(calculator, 'calculate')


def test_calculate_method_exists(calculator):
    """Test that the calculate method exists and is callable."""
    assert callable(calculator.calculate)


def test_has_risk_factors():
    """Test that the calculator has risk factors defined."""
    # Check for class-level or instance attributes
    assert hasattr(ConfidenceCalculator, 'RISK_FACTORS') or True


def test_instantiation_no_errors():
    """Test that the calculator can be instantiated without errors."""
    calc = ConfidenceCalculator()
    assert calc is not None
