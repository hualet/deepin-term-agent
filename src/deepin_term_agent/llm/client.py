"""Moonshot K2 API client for LLM integration."""

import os
import json
import logging
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class MoonshotClient:
    """Client for Moonshot K2 API using OpenAI-compatible interface."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.moonshot.cn/v1"):
        """Initialize Moonshot client.

        Args:
            api_key: Moonshot API key. If None, reads from MOONSHOT_API_KEY env var.
            base_url: Moonshot API base URL.
        """
        self.api_key = api_key or os.getenv("MOONSHOT_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Moonshot API key not found. Set MOONSHOT_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=base_url
        )

        # Available models from Moonshot K2
        self.models = {
            "k2": "kimi-k2-0711-preview",
        }

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "k2",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send chat completion request to Moonshot API.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys.
            model: Model name to use.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            tools: List of available tools for function calling.
            tool_choice: Tool choice strategy.

        Returns:
            API response dictionary.
        """
        try:
            # Map model names
            model_id = self.models.get(model, model)

            params = {
                "model": model_id,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            if tools:
                params["tools"] = tools
                if tool_choice:
                    params["tool_choice"] = tool_choice

            response = await self.client.chat.completions.create(**params)

            # Convert to dict format
            return {
                "id": response.id,
                "model": response.model,
                "choices": [
                    {
                        "index": choice.index,
                        "message": {
                            "role": choice.message.role,
                            "content": choice.message.content,
                            "tool_calls": [
                                {
                                    "id": tool_call.id,
                                    "type": tool_call.type,
                                    "function": {
                                        "name": tool_call.function.name,
                                        "arguments": tool_call.function.arguments
                                    }
                                }
                                for tool_call in (choice.message.tool_calls or [])
                            ]
                        },
                        "finish_reason": choice.finish_reason
                    }
                    for choice in response.choices
                ],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }

        except Exception as e:
            logger.error(f"Error calling Moonshot API: {e}")
            raise

    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: List[Dict[str, str]] = None,
        tools: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a response using the LLM.

        Args:
            system_prompt: System prompt for the AI.
            user_message: User's message.
            conversation_history: Previous conversation messages.
            tools: Available tools for function calling.

        Returns:
            Dictionary with response and tool calls.
        """
        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": user_message})

        return await self.chat_completion(
            messages=messages,
            tools=tools,
            temperature=0.1  # Lower temperature for more deterministic responses
        )