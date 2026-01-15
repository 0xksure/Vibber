"""
Confidence Calculator - Determines how confident the agent is in its response
"""

from typing import Any, Dict
import structlog

logger = structlog.get_logger()


class ConfidenceCalculator:
    """
    Calculates confidence scores for agent responses.

    Factors considered:
    - Intent classification confidence
    - Context relevance (RAG quality)
    - Response quality signals
    - Historical accuracy
    """

    # Weights for different confidence factors
    WEIGHTS = {
        "intent_confidence": 0.25,
        "context_quality": 0.30,
        "response_quality": 0.25,
        "domain_match": 0.20
    }

    # Risk factors that reduce confidence
    RISK_FACTORS = {
        "financial": -20,      # Financial decisions
        "security": -25,       # Security-related
        "irreversible": -30,   # Can't be undone
        "public": -10,         # Public-facing
        "sensitive": -15,      # Sensitive data
        "complex": -10,        # Complex multi-step
    }

    # Keywords that indicate high-risk situations
    RISK_KEYWORDS = {
        "financial": ["payment", "invoice", "refund", "money", "price", "cost", "budget", "expense"],
        "security": ["password", "token", "secret", "credential", "access", "permission", "auth"],
        "irreversible": ["delete", "remove", "drop", "destroy", "terminate", "cancel"],
        "public": ["customer", "client", "external", "public", "announcement"],
        "sensitive": ["personal", "private", "confidential", "pii", "gdpr"],
        "complex": ["migrate", "refactor", "redesign", "architecture", "multi-step"]
    }

    async def calculate(
        self,
        intent: Dict[str, Any],
        response: Dict[str, Any],
        context_quality: float = 0.5
    ) -> int:
        """
        Calculate overall confidence score (0-100).

        Args:
            intent: Intent classification result
            response: Generated response
            context_quality: Quality of retrieved context (0-1)

        Returns:
            Confidence score from 0-100
        """
        # Base scores
        intent_confidence = intent.get("confidence", 0.5)

        # Response quality assessment
        response_quality = self._assess_response_quality(response)

        # Domain match assessment
        domain_match = self._assess_domain_match(intent, response)

        # Calculate weighted score
        weighted_score = (
            intent_confidence * self.WEIGHTS["intent_confidence"] +
            context_quality * self.WEIGHTS["context_quality"] +
            response_quality * self.WEIGHTS["response_quality"] +
            domain_match * self.WEIGHTS["domain_match"]
        )

        # Convert to 0-100 scale
        base_confidence = int(weighted_score * 100)

        # Apply risk adjustments
        risk_adjustment = self._calculate_risk_adjustment(intent, response)

        # Final confidence
        final_confidence = max(0, min(100, base_confidence + risk_adjustment))

        logger.debug(
            "Confidence calculated",
            base=base_confidence,
            risk_adjustment=risk_adjustment,
            final=final_confidence
        )

        return final_confidence

    def _assess_response_quality(self, response: Dict[str, Any]) -> float:
        """Assess the quality of the generated response"""
        score = 0.5  # Base score

        response_text = response.get("response_text", "")

        # Check if response exists and has content
        if not response_text:
            return 0.1

        # Length check (not too short, not too long)
        word_count = len(response_text.split())
        if 10 < word_count < 500:
            score += 0.1

        # Check for reasoning
        if response.get("reasoning"):
            score += 0.15

        # Check for explicit needs_review flag
        if response.get("needs_review") == False:
            score += 0.1
        elif response.get("needs_review") == True:
            score -= 0.1

        # Check for action specification
        if response.get("action") and response.get("action") != "none":
            score += 0.1

        # Penalize generic responses
        generic_phrases = [
            "i'm not sure",
            "i cannot",
            "i don't know",
            "please contact",
            "i apologize"
        ]

        response_lower = response_text.lower()
        for phrase in generic_phrases:
            if phrase in response_lower:
                score -= 0.1

        return max(0.0, min(1.0, score))

    def _assess_domain_match(
        self,
        intent: Dict[str, Any],
        response: Dict[str, Any]
    ) -> float:
        """Assess how well the response matches the expected domain"""
        score = 0.5  # Base score

        intent_type = intent.get("type", "unknown")
        action = response.get("action", "")

        # Check if action matches intent expectations
        expected_actions = {
            "question": ["respond", "reply"],
            "request": ["respond", "reply", "execute"],
            "review_request": ["review_code", "comment", "approve"],
            "bug_report": ["triage", "respond", "update"],
            "escalation": ["escalate", "respond"],
        }

        expected = expected_actions.get(intent_type, [])
        if action in expected:
            score += 0.3

        # Check keyword relevance
        keywords = intent.get("keywords", [])
        response_text = response.get("response_text", "").lower()

        keyword_matches = sum(1 for k in keywords if k in response_text)
        if keywords:
            keyword_score = keyword_matches / len(keywords)
            score += keyword_score * 0.2

        return max(0.0, min(1.0, score))

    def _calculate_risk_adjustment(
        self,
        intent: Dict[str, Any],
        response: Dict[str, Any]
    ) -> int:
        """Calculate confidence adjustment based on risk factors"""
        adjustment = 0

        # Combine all text for analysis
        text_to_analyze = (
            str(intent.get("keywords", [])) +
            response.get("response_text", "") +
            response.get("reasoning", "")
        ).lower()

        # Check for risk keywords
        for risk_type, keywords in self.RISK_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_to_analyze:
                    adjustment += self.RISK_FACTORS.get(risk_type, 0)
                    break  # Only apply each risk type once

        # Check action type risks
        action = response.get("action", "")

        high_risk_actions = ["approve", "merge", "delete", "execute", "deploy"]
        if action in high_risk_actions:
            adjustment -= 15

        medium_risk_actions = ["update", "comment", "assign"]
        if action in medium_risk_actions:
            adjustment -= 5

        return adjustment

    def get_confidence_explanation(self, confidence: int) -> str:
        """Get human-readable explanation of confidence level"""
        if confidence >= 90:
            return "Very high confidence - response closely matches expected patterns"
        elif confidence >= 75:
            return "High confidence - response is appropriate for the context"
        elif confidence >= 60:
            return "Moderate confidence - response may need human review"
        elif confidence >= 40:
            return "Low confidence - human review recommended"
        elif confidence >= 20:
            return "Very low confidence - significant uncertainty in response"
        else:
            return "Minimal confidence - unable to generate appropriate response"
