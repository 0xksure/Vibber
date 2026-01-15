"""
Core Agent Implementation
The AI agent that acts as an employee's clone
"""

import json
import time
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from src.config import settings
from src.core.personality import PersonalityEngine
from src.core.intent import IntentClassifier
from src.core.confidence import ConfidenceCalculator
from src.embeddings.embedder import Embedder
from src.memory.vector_store import VectorStore
from src.memory.redis_cache import RedisCache
from src.tools.base import ToolRegistry
from src.tools.slack import SlackTool
from src.tools.github import GitHubTool
from src.tools.jira import JiraTool

logger = structlog.get_logger()


class Agent:
    """
    AI Agent that acts as an employee's clone.

    Architecture inspired by Cursor's agentic patterns and Anthropic's
    constitutional AI approaches for safe, helpful assistants.
    """

    def __init__(
        self,
        agent_id: UUID,
        user_id: UUID,
        anthropic_client: AsyncAnthropic,
        openai_client: AsyncOpenAI,
        embedder: Embedder,
        vector_store: VectorStore,
        cache: RedisCache,
        personality_engine: PersonalityEngine,
    ):
        self.agent_id = agent_id
        self.user_id = user_id
        self.anthropic = anthropic_client
        self.openai = openai_client
        self.embedder = embedder
        self.vector_store = vector_store
        self.cache = cache
        self.personality_engine = personality_engine

        # Agent state
        self.config: Dict[str, Any] = {}
        self.personality_profile: Dict[str, Any] = {}
        self.active_tools: Dict[str, Any] = {}

        # Components
        self.intent_classifier = IntentClassifier()
        self.confidence_calculator = ConfidenceCalculator()
        self.tool_registry = ToolRegistry()

        # Metrics
        self.total_interactions = 0
        self.successful_interactions = 0
        self.escalated_interactions = 0

    async def load(self):
        """Load agent state and configuration"""
        logger.info("Loading agent", agent_id=str(self.agent_id))

        # Load config from cache or database
        cached_config = await self.cache.get(f"agent:{self.agent_id}:config")
        if cached_config:
            self.config = json.loads(cached_config)
        else:
            self.config = {
                "confidence_threshold": settings.default_confidence_threshold,
                "auto_mode": False,
                "model": settings.default_model,
            }

        # Load personality profile
        self.personality_profile = await self.personality_engine.load_profile(
            self.agent_id
        )

        # Register available tools
        self._register_tools()

        logger.info("Agent loaded successfully", agent_id=str(self.agent_id))

    async def save_state(self):
        """Persist agent state"""
        await self.cache.set(
            f"agent:{self.agent_id}:config",
            json.dumps(self.config),
            ttl=3600 * 24  # 24 hours
        )

    def _register_tools(self):
        """Register available tools for the agent"""
        self.tool_registry.register(SlackTool())
        self.tool_registry.register(GitHubTool())
        self.tool_registry.register(JiraTool())

    async def process(self, interaction_data: dict) -> dict:
        """
        Process an incoming interaction.

        Pipeline:
        1. Classify intent
        2. Retrieve relevant context
        3. Generate response with personality
        4. Calculate confidence
        5. Decide: execute, escalate, or suggest
        """
        start_time = time.time()

        provider = interaction_data.get("provider")
        interaction_type = interaction_data.get("interaction_type")
        input_data = interaction_data.get("input_data", {})

        logger.info(
            "Processing interaction",
            agent_id=str(self.agent_id),
            provider=provider,
            type=interaction_type
        )

        try:
            # Step 1: Classify intent
            intent = await self.intent_classifier.classify(
                provider=provider,
                interaction_type=interaction_type,
                data=input_data
            )

            # Step 2: Retrieve relevant context
            context = await self._build_context(intent, input_data)

            # Step 3: Generate response
            response = await self._generate_response(
                intent=intent,
                context=context,
                input_data=input_data,
                provider=provider
            )

            # Step 4: Calculate confidence
            confidence = await self.confidence_calculator.calculate(
                intent=intent,
                response=response,
                context_quality=context.get("quality", 0.5)
            )

            # Step 5: Decide action
            threshold = self.config.get(
                "confidence_threshold",
                settings.default_confidence_threshold
            )

            processing_time = int((time.time() - start_time) * 1000)

            if confidence >= threshold and self.config.get("auto_mode", False):
                # Execute action automatically
                execution_result = await self._execute_action(
                    provider=provider,
                    response=response,
                    input_data=input_data
                )

                self.successful_interactions += 1

                return {
                    "status": "completed",
                    "action": "executed",
                    "response": response,
                    "confidence": confidence,
                    "execution_result": execution_result,
                    "processing_time": processing_time
                }

            elif confidence >= threshold:
                # Suggest action (shadow mode)
                return {
                    "status": "completed",
                    "action": "suggested",
                    "response": response,
                    "confidence": confidence,
                    "processing_time": processing_time
                }

            else:
                # Escalate to human
                self.escalated_interactions += 1

                return {
                    "status": "escalated",
                    "action": "escalate",
                    "response": response,
                    "confidence": confidence,
                    "reason": self._get_escalation_reason(confidence, intent),
                    "processing_time": processing_time
                }

        except Exception as e:
            logger.error(
                "Error processing interaction",
                agent_id=str(self.agent_id),
                error=str(e)
            )
            return {
                "status": "error",
                "error": str(e),
                "processing_time": int((time.time() - start_time) * 1000)
            }

        finally:
            self.total_interactions += 1

    async def _build_context(
        self,
        intent: dict,
        input_data: dict
    ) -> dict:
        """Build context from various sources for RAG"""
        context = {
            "personality": self.personality_profile,
            "relevant_samples": [],
            "domain_knowledge": [],
            "quality": 0.5
        }

        # Get query for semantic search
        query = self._extract_query(input_data)
        if not query:
            return context

        # Search for relevant personality samples (how user responds)
        style_samples = await self.vector_store.search(
            namespace=f"agent:{self.agent_id}:style",
            query_embedding=await self.embedder.embed(query),
            top_k=5
        )
        context["relevant_samples"] = style_samples

        # Search for domain knowledge
        knowledge = await self.vector_store.search(
            namespace=f"agent:{self.agent_id}:knowledge",
            query_embedding=await self.embedder.embed(query),
            top_k=3
        )
        context["domain_knowledge"] = knowledge

        # Calculate context quality based on relevance scores
        if style_samples:
            avg_score = sum(s.get("score", 0) for s in style_samples) / len(style_samples)
            context["quality"] = min(avg_score * 1.5, 1.0)  # Scale up, cap at 1.0

        return context

    def _extract_query(self, input_data: dict) -> Optional[str]:
        """Extract searchable query from input data"""
        # Try common fields
        for field in ["text", "message", "content", "body", "title", "description"]:
            if field in input_data:
                return input_data[field]

        # For nested structures
        if isinstance(input_data, dict):
            for value in input_data.values():
                if isinstance(value, str) and len(value) > 10:
                    return value

        return None

    async def _generate_response(
        self,
        intent: dict,
        context: dict,
        input_data: dict,
        provider: str
    ) -> dict:
        """Generate response using LLM with personality"""

        # Build system prompt with personality
        system_prompt = self._build_system_prompt(context, provider)

        # Build user message
        user_message = self._build_user_message(intent, input_data, context)

        # Call Claude
        response = await self.anthropic.messages.create(
            model=self.config.get("model", settings.default_model),
            max_tokens=settings.max_output_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )

        response_text = response.content[0].text

        # Parse structured response if needed
        return self._parse_response(response_text, provider, intent)

    def _build_system_prompt(self, context: dict, provider: str) -> str:
        """Build system prompt with personality injection"""
        personality = context.get("personality", {})
        samples = context.get("relevant_samples", [])

        # Base prompt
        prompt = f"""You are an AI assistant acting as a clone of a specific person. Your goal is to respond exactly as they would - matching their communication style, tone, knowledge, and decision-making patterns.

PERSONALITY PROFILE:
- Communication style: {personality.get('style', 'professional and helpful')}
- Tone: {personality.get('tone', 'friendly but concise')}
- Expertise areas: {', '.join(personality.get('expertise', ['general']))}
- Common phrases: {', '.join(personality.get('phrases', []))}

EXAMPLES OF HOW THIS PERSON RESPONDS:
"""

        # Add relevant samples
        for i, sample in enumerate(samples[:3], 1):
            prompt += f"""
Example {i}:
Input: {sample.get('input', '')}
Response: {sample.get('output', '')}
"""

        # Provider-specific instructions
        provider_instructions = {
            "slack": """
When responding to Slack messages:
- Keep responses concise and conversational
- Use appropriate emoji reactions when suitable
- Reference previous context if available
- Tag people with @ when necessary
""",
            "github": """
When reviewing code or PRs:
- Be constructive and specific in feedback
- Reference best practices and patterns
- Suggest improvements with examples
- Acknowledge good code as well as issues
""",
            "jira": """
When handling Jira tickets:
- Update status appropriately
- Add clear, actionable comments
- Estimate effort when asked
- Link related tickets when relevant
"""
        }

        prompt += provider_instructions.get(provider, "")

        prompt += """

IMPORTANT GUIDELINES:
1. Respond EXACTLY as this person would - not as a generic AI
2. If unsure, acknowledge uncertainty rather than guessing
3. For complex decisions, recommend human review
4. Never share sensitive information or make irreversible changes without approval
5. Match the emotional tone of the person you're cloning
"""

        return prompt

    def _build_user_message(
        self,
        intent: dict,
        input_data: dict,
        context: dict
    ) -> str:
        """Build the user message for the LLM"""
        knowledge = context.get("domain_knowledge", [])

        message = f"""
INTENT: {intent.get('type', 'unknown')} - {intent.get('action', 'respond')}

INPUT DATA:
{json.dumps(input_data, indent=2)}

"""

        if knowledge:
            message += """
RELEVANT KNOWLEDGE:
"""
            for k in knowledge[:2]:
                message += f"- {k.get('content', '')}\n"

        message += """
Based on the personality profile and examples provided, generate an appropriate response.
Return your response in JSON format:
{
    "response_text": "The actual response to send",
    "action": "reply|comment|update|approve|none",
    "reasoning": "Brief explanation of why this response is appropriate",
    "needs_review": true/false
}
"""

        return message

    def _parse_response(
        self,
        response_text: str,
        provider: str,
        intent: dict
    ) -> dict:
        """Parse LLM response into structured format"""
        try:
            # Try to parse as JSON
            # Find JSON in response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # Fallback to simple response
        return {
            "response_text": response_text,
            "action": "reply",
            "reasoning": "Direct response generated",
            "needs_review": True
        }

    async def _execute_action(
        self,
        provider: str,
        response: dict,
        input_data: dict
    ) -> dict:
        """Execute the decided action using appropriate tool"""
        tool = self.tool_registry.get(provider)
        if not tool:
            return {"success": False, "error": "No tool available for provider"}

        try:
            result = await tool.execute(
                action=response.get("action", "reply"),
                response_text=response.get("response_text", ""),
                input_data=input_data
            )
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {"success": False, "error": str(e)}

    def _get_escalation_reason(self, confidence: int, intent: dict) -> str:
        """Generate human-readable escalation reason"""
        if confidence < 30:
            return "Very low confidence - request is unclear or outside expertise"
        elif confidence < 50:
            return "Low confidence - may need human judgment for accuracy"
        elif confidence < 70:
            return "Moderate confidence - recommending human review before action"
        else:
            return "Auto-mode disabled - awaiting approval"

    async def train(self, training_data: dict) -> dict:
        """Train the agent with new samples"""
        samples = training_data.get("samples", [])

        for sample in samples:
            # Generate embedding
            embedding = await self.embedder.embed(sample.get("input", ""))

            # Store in vector database
            await self.vector_store.upsert(
                namespace=f"agent:{self.agent_id}:style",
                vectors=[{
                    "id": sample.get("id", str(self.agent_id)),
                    "values": embedding,
                    "metadata": {
                        "input": sample.get("input"),
                        "output": sample.get("output"),
                        "type": sample.get("type", "response")
                    }
                }]
            )

        # Refresh personality profile
        self.personality_profile = await self.personality_engine.analyze_and_update(
            self.agent_id,
            samples
        )

        return {
            "success": True,
            "samples_processed": len(samples)
        }

    async def get_status(self) -> dict:
        """Get current agent status"""
        return {
            "loaded": True,
            "status": "active",
            "config": self.config,
            "metrics": {
                "total_interactions": self.total_interactions,
                "successful": self.successful_interactions,
                "escalated": self.escalated_interactions,
                "success_rate": (
                    self.successful_interactions / self.total_interactions * 100
                    if self.total_interactions > 0 else 0
                )
            }
        }

    async def update_settings(self, new_settings: dict):
        """Update agent configuration"""
        self.config.update(new_settings)
        await self.save_state()
