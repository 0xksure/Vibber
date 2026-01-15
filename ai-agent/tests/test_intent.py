"""Tests for the intent classifier."""
import pytest
from src.core.intent import IntentClassifier


@pytest.fixture
def classifier():
    """Create an intent classifier instance."""
    return IntentClassifier()


def test_intent_classifier_initialization(classifier):
    """Test that the intent classifier initializes correctly."""
    assert classifier is not None


def test_has_intent_mappings():
    """Test that intent mappings are defined."""
    assert hasattr(IntentClassifier, 'INTENT_MAPPINGS')
    assert isinstance(IntentClassifier.INTENT_MAPPINGS, dict)


def test_slack_in_mappings():
    """Test that Slack mappings exist."""
    assert 'slack' in IntentClassifier.INTENT_MAPPINGS


def test_github_in_mappings():
    """Test that GitHub mappings exist."""
    assert 'github' in IntentClassifier.INTENT_MAPPINGS


def test_jira_in_mappings():
    """Test that Jira mappings exist."""
    assert 'jira' in IntentClassifier.INTENT_MAPPINGS


def test_classify_method_exists(classifier):
    """Test that the classify method exists."""
    assert hasattr(classifier, 'classify')
    assert callable(classifier.classify)


def test_has_action_recommendations():
    """Test that action recommendations are defined."""
    assert hasattr(IntentClassifier, 'ACTION_RECOMMENDATIONS')
    assert isinstance(IntentClassifier.ACTION_RECOMMENDATIONS, dict)
