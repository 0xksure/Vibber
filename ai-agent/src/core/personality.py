"""
Personality Engine - Captures and reproduces user's communication style
"""

import json
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from anthropic import AsyncAnthropic

from src.config import settings
from src.embeddings.embedder import Embedder
from src.memory.vector_store import VectorStore
from src.memory.redis_cache import RedisCache

logger = structlog.get_logger()


class PersonalityEngine:
    """
    Captures, analyzes, and reproduces a user's unique communication style.

    Key aspects:
    - Writing style (formal/casual, verbose/concise)
    - Common phrases and vocabulary
    - Response patterns by context
    - Tone variations
    - Decision-making tendencies
    """

    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        cache: RedisCache,
    ):
        self.embedder = embedder
        self.vector_store = vector_store
        self.cache = cache
        self.anthropic = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def load_profile(self, agent_id: UUID) -> Dict[str, Any]:
        """Load personality profile from cache or generate default"""
        cache_key = f"agent:{agent_id}:personality"

        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            return json.loads(cached)

        # Return default profile
        return self._get_default_profile()

    def _get_default_profile(self) -> Dict[str, Any]:
        """Return default personality profile"""
        return {
            "style": "professional",
            "tone": "helpful and friendly",
            "verbosity": "moderate",
            "formality": 0.6,  # 0 = very casual, 1 = very formal
            "expertise": [],
            "phrases": [],
            "response_patterns": {
                "greeting": "Hi! ",
                "acknowledgment": "Got it. ",
                "clarification": "Just to clarify, ",
                "closing": "Let me know if you need anything else."
            },
            "preferences": {
                "uses_emoji": False,
                "bullet_points": True,
                "code_formatting": True,
                "mentions_people": True
            }
        }

    async def analyze_and_update(
        self,
        agent_id: UUID,
        samples: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze samples and update personality profile"""
        if not samples:
            return await self.load_profile(agent_id)

        # Prepare samples for analysis
        sample_texts = []
        for sample in samples[:50]:  # Limit to 50 samples
            sample_texts.append(f"Input: {sample.get('input', '')}\nResponse: {sample.get('output', '')}")

        combined_text = "\n\n---\n\n".join(sample_texts)

        # Use Claude to analyze personality
        analysis_prompt = f"""Analyze the following communication samples to extract a personality profile.

SAMPLES:
{combined_text}

Based on these samples, provide a personality analysis in JSON format:
{{
    "style": "description of overall communication style",
    "tone": "description of tone",
    "verbosity": "concise|moderate|verbose",
    "formality": 0.0 to 1.0 (0=casual, 1=formal),
    "expertise": ["list", "of", "expertise", "areas"],
    "phrases": ["common", "phrases", "used"],
    "response_patterns": {{
        "greeting": "how they typically start messages",
        "acknowledgment": "how they acknowledge things",
        "clarification": "how they ask for clarification",
        "closing": "how they end messages"
    }},
    "preferences": {{
        "uses_emoji": true/false,
        "bullet_points": true/false,
        "code_formatting": true/false,
        "mentions_people": true/false
    }},
    "unique_traits": ["any", "unique", "communication", "traits"]
}}

Respond with only the JSON object, no additional text."""

        try:
            response = await self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{"role": "user", "content": analysis_prompt}]
            )

            # Parse response
            response_text = response.content[0].text
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                profile = json.loads(response_text[start:end])

                # Cache the profile
                cache_key = f"agent:{agent_id}:personality"
                await self.cache.set(cache_key, json.dumps(profile), ttl=86400)

                logger.info(
                    "Personality profile updated",
                    agent_id=str(agent_id),
                    style=profile.get("style")
                )

                return profile

        except Exception as e:
            logger.error(f"Failed to analyze personality: {e}")

        return await self.load_profile(agent_id)

    async def get_style_prompt(
        self,
        agent_id: UUID,
        context: str = "general"
    ) -> str:
        """Generate a style prompt for response generation"""
        profile = await self.load_profile(agent_id)

        prompt = f"""Communication Style Guidelines:

OVERALL STYLE: {profile.get('style', 'professional')}
TONE: {profile.get('tone', 'helpful')}
VERBOSITY: {profile.get('verbosity', 'moderate')}
FORMALITY LEVEL: {profile.get('formality', 0.5) * 100}%

COMMON PHRASES TO USE:
{chr(10).join('- ' + p for p in profile.get('phrases', [])[:5])}

RESPONSE PATTERNS:
- Start messages with: "{profile.get('response_patterns', {}).get('greeting', '')}"
- Acknowledge with: "{profile.get('response_patterns', {}).get('acknowledgment', '')}"
- Ask for clarification with: "{profile.get('response_patterns', {}).get('clarification', '')}"

PREFERENCES:
- Uses emoji: {'Yes' if profile.get('preferences', {}).get('uses_emoji') else 'No'}
- Uses bullet points: {'Yes' if profile.get('preferences', {}).get('bullet_points') else 'No'}
- Formats code properly: {'Yes' if profile.get('preferences', {}).get('code_formatting') else 'No'}

UNIQUE TRAITS:
{chr(10).join('- ' + t for t in profile.get('unique_traits', [])[:3])}

Remember: Your response should sound EXACTLY like this person would respond, not like a generic AI assistant.
"""

        return prompt

    async def score_response_authenticity(
        self,
        agent_id: UUID,
        response: str,
        context: str
    ) -> float:
        """
        Score how authentic a response is to the user's personality.
        Returns 0.0-1.0 where 1.0 is perfect match.
        """
        profile = await self.load_profile(agent_id)

        # Check for common phrases
        phrase_matches = 0
        phrases = profile.get("phrases", [])
        for phrase in phrases:
            if phrase.lower() in response.lower():
                phrase_matches += 1
        phrase_score = min(phrase_matches / max(len(phrases), 1), 1.0) if phrases else 0.5

        # Check formality match
        formality = profile.get("formality", 0.5)
        informal_indicators = ["hey", "gonna", "wanna", "lol", "haha", "!!", "???"]
        formal_indicators = ["therefore", "additionally", "furthermore", "regarding"]

        response_lower = response.lower()
        informal_count = sum(1 for i in informal_indicators if i in response_lower)
        formal_count = sum(1 for i in formal_indicators if i in response_lower)

        estimated_formality = 0.5
        if informal_count > formal_count:
            estimated_formality = 0.3
        elif formal_count > informal_count:
            estimated_formality = 0.7

        formality_score = 1.0 - abs(formality - estimated_formality)

        # Check verbosity match
        verbosity = profile.get("verbosity", "moderate")
        word_count = len(response.split())

        verbosity_score = 0.5
        if verbosity == "concise" and word_count < 50:
            verbosity_score = 1.0
        elif verbosity == "moderate" and 30 < word_count < 150:
            verbosity_score = 1.0
        elif verbosity == "verbose" and word_count > 100:
            verbosity_score = 1.0

        # Check preferences
        prefs = profile.get("preferences", {})
        pref_score = 0.5

        has_emoji = any(ord(c) > 127000 for c in response)
        if prefs.get("uses_emoji", False) == has_emoji:
            pref_score += 0.25

        has_bullets = "•" in response or "- " in response or "* " in response
        if prefs.get("bullet_points", False) == has_bullets:
            pref_score += 0.25

        # Weighted average
        final_score = (
            phrase_score * 0.3 +
            formality_score * 0.25 +
            verbosity_score * 0.25 +
            pref_score * 0.2
        )

        return round(final_score, 2)
