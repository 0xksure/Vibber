"""
Intent Classifier - Determines what action the agent should take
"""

from typing import Any, Dict, Optional
import structlog

logger = structlog.get_logger()


class IntentClassifier:
    """
    Classifies the intent of incoming interactions to determine
    what action the agent should take.
    """

    # Intent mappings by provider and interaction type
    INTENT_MAPPINGS = {
        "slack": {
            "message": {
                "question": ["?", "how", "what", "when", "where", "why", "who", "can you", "could you"],
                "request": ["please", "can you", "could you", "would you", "need", "want"],
                "greeting": ["hi", "hello", "hey", "good morning", "good afternoon"],
                "acknowledgment": ["thanks", "thank you", "got it", "ok", "okay", "sure"],
                "escalation": ["urgent", "asap", "critical", "help", "issue", "problem"],
            },
            "mention": {
                "question": ["?"],
                "request": ["please", "can you", "need"],
                "review": ["review", "check", "look at"],
            }
        },
        "github": {
            "pull_request": {
                "review_request": ["review", "please review", "ready for review"],
                "feedback_request": ["feedback", "thoughts", "opinion"],
                "approval_request": ["approve", "lgtm", "merge"],
            },
            "issue": {
                "bug_report": ["bug", "error", "broken", "doesn't work", "failed"],
                "feature_request": ["feature", "enhancement", "would be nice", "suggestion"],
                "question": ["?", "how to", "help"],
            },
            "comment": {
                "question": ["?"],
                "suggestion": ["suggest", "maybe", "could", "should"],
                "response_needed": ["@", "thoughts", "opinion"],
            }
        },
        "jira": {
            "issue_created": {
                "bug": ["bug", "defect", "error"],
                "task": ["task", "todo", "implement"],
                "story": ["story", "feature", "user story"],
            },
            "issue_updated": {
                "status_change": ["status", "moved", "transitioned"],
                "assignment": ["assigned", "assignee"],
                "comment": ["commented", "comment"],
            },
            "comment": {
                "question": ["?"],
                "update_request": ["update", "status", "eta"],
                "blocker": ["blocked", "blocking", "blocker"],
            }
        }
    }

    # Action recommendations by intent
    ACTION_RECOMMENDATIONS = {
        # Slack intents
        ("slack", "question"): "respond",
        ("slack", "request"): "respond",
        ("slack", "greeting"): "respond",
        ("slack", "acknowledgment"): "react",  # Just react with emoji
        ("slack", "escalation"): "escalate",
        ("slack", "review"): "respond",

        # GitHub intents
        ("github", "review_request"): "review_code",
        ("github", "feedback_request"): "comment",
        ("github", "approval_request"): "approve_or_comment",
        ("github", "bug_report"): "triage",
        ("github", "feature_request"): "triage",
        ("github", "suggestion"): "respond",

        # Jira intents
        ("jira", "bug"): "triage_and_update",
        ("jira", "task"): "acknowledge",
        ("jira", "story"): "acknowledge",
        ("jira", "status_change"): "none",  # Just log
        ("jira", "question"): "respond",
        ("jira", "update_request"): "update_status",
        ("jira", "blocker"): "escalate",
    }

    async def classify(
        self,
        provider: str,
        interaction_type: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Classify the intent of an interaction.

        Returns:
            dict with:
                - type: The classified intent type
                - action: Recommended action
                - confidence: How confident we are in classification
                - keywords: Keywords that triggered the classification
        """
        # Get text content from data
        text = self._extract_text(data)
        if not text:
            return self._unknown_intent(provider, interaction_type)

        text_lower = text.lower()

        # Get intent mappings for this provider and type
        provider_mappings = self.INTENT_MAPPINGS.get(provider, {})
        type_mappings = provider_mappings.get(interaction_type, {})

        if not type_mappings:
            return self._unknown_intent(provider, interaction_type)

        # Score each potential intent
        best_intent = None
        best_score = 0
        matched_keywords = []

        for intent_type, keywords in type_mappings.items():
            score = 0
            matches = []

            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
                    matches.append(keyword)

            if score > best_score:
                best_score = score
                best_intent = intent_type
                matched_keywords = matches

        if best_intent is None:
            return self._unknown_intent(provider, interaction_type)

        # Get recommended action
        action = self.ACTION_RECOMMENDATIONS.get(
            (provider, best_intent),
            "respond"
        )

        # Calculate confidence
        confidence = min(best_score / 3.0, 1.0)  # Normalize to 0-1
        if len(matched_keywords) >= 3:
            confidence = min(confidence + 0.2, 1.0)

        return {
            "type": best_intent,
            "action": action,
            "confidence": confidence,
            "keywords": matched_keywords,
            "provider": provider,
            "interaction_type": interaction_type
        }

    def _extract_text(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract text content from interaction data"""
        # Common text field names
        text_fields = [
            "text", "message", "content", "body",
            "title", "description", "comment",
            "pull_request.title", "pull_request.body",
            "issue.title", "issue.body"
        ]

        for field in text_fields:
            if "." in field:
                # Handle nested fields
                parts = field.split(".")
                value = data
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = None
                        break
                if value:
                    return str(value)
            elif field in data:
                return str(data[field])

        return None

    def _unknown_intent(
        self,
        provider: str,
        interaction_type: str
    ) -> Dict[str, Any]:
        """Return unknown intent result"""
        return {
            "type": "unknown",
            "action": "analyze",
            "confidence": 0.0,
            "keywords": [],
            "provider": provider,
            "interaction_type": interaction_type
        }
