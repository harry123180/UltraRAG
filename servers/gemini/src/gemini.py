"""Gemini API Generation Server for UltraRAG.

This server provides text generation capabilities using Google's Gemini API.
"""
import asyncio
import os
from typing import Any, Dict, List, Optional, Union

import google.generativeai as genai
from tqdm import tqdm

from ultrarag.server import UltraRAG_MCP_Server

app = UltraRAG_MCP_Server("gemini")


class GeminiGeneration:
    """Generation class using Google Gemini API."""

    def __init__(self, mcp_inst: UltraRAG_MCP_Server):
        mcp_inst.tool(
            self.gemini_init,
            output="api_key,model_name,generation_config->None",
        )
        mcp_inst.tool(
            self.generate,
            output="prompt_ls,system_prompt->ans_ls",
        )
        mcp_inst.tool(
            self.multiturn_generate,
            output="messages,system_prompt->ans_ls",
        )

        self.model = None
        self.generation_config = None

    def _extract_text_prompts(
        self, prompt_ls: List[Union[str, Dict[str, Any]]]
    ) -> List[str]:
        """Extract text content from various prompt formats.

        Args:
            prompt_ls: List of prompts in various formats (str, dict, etc.)

        Returns:
            List of text strings
        """
        prompts = []
        for m in prompt_ls:
            if hasattr(m, "content") and hasattr(m.content, "text"):
                prompts.append(m.content.text)
            elif isinstance(m, dict):
                if (
                    "content" in m
                    and isinstance(m["content"], dict)
                    and "text" in m["content"]
                ):
                    prompts.append(m["content"]["text"])
                elif "content" in m and isinstance(m["content"], str):
                    prompts.append(m["content"])
                elif "text" in m:
                    prompts.append(m["text"])
                else:
                    app.logger.warning(f"Unsupported dict prompt format: {m}")
                    prompts.append(str(m))
            elif isinstance(m, str):
                prompts.append(m)
            else:
                prompts.append(str(m))
        return prompts

    def gemini_init(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-3-pro-preview",
        generation_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize Gemini API client.

        Args:
            api_key: Google API key (or set GOOGLE_API_KEY env var)
            model_name: Gemini model name (default: gemini-3-pro-preview)
            generation_config: Generation configuration dict
        """
        api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "api_key is required. Set GOOGLE_API_KEY env var or pass api_key parameter."
            )

        genai.configure(api_key=api_key)

        self.generation_config = generation_config or {
            "temperature": 0.7,
            "top_p": 0.8,
            "max_output_tokens": 2048,
        }

        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=self.generation_config,
        )
        self.model_name = model_name

        app.logger.info(f"Gemini initialized with model: {model_name}")

    async def _generate_single(
        self,
        prompt: str,
        system_prompt: str = "",
    ) -> str:
        """Generate response for a single prompt.

        Args:
            prompt: User prompt
            system_prompt: Optional system instruction

        Returns:
            Generated text response
        """
        try:
            if system_prompt:
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    generation_config=self.generation_config,
                    system_instruction=system_prompt,
                )
            else:
                model = self.model

            response = await asyncio.to_thread(
                model.generate_content, prompt
            )
            return response.text
        except Exception as e:
            app.logger.error(f"Generation error: {e}")
            return f"<error: {str(e)}>"

    async def generate(
        self,
        prompt_ls: List[Union[str, Dict[str, Any]]],
        system_prompt: str = "",
    ) -> Dict[str, List[str]]:
        """Generate responses for a list of prompts.

        Args:
            prompt_ls: List of prompts
            system_prompt: Optional system instruction

        Returns:
            Dictionary with 'ans_ls' containing generated responses
        """
        if self.model is None:
            raise RuntimeError("Gemini not initialized. Call gemini_init first.")

        system_prompt = str(system_prompt or "").strip()
        prompts = [str(p).strip() for p in self._extract_text_prompts(prompt_ls)]

        if not prompts:
            app.logger.info("Empty prompt list; return empty ans_ls.")
            return {"ans_ls": []}

        results = []
        for prompt in tqdm(prompts, desc="Gemini Generating"):
            result = await self._generate_single(prompt, system_prompt)
            results.append(result)

        return {"ans_ls": results}

    async def multiturn_generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
    ) -> Dict[str, List[str]]:
        """Generate response for multi-turn conversation.

        Args:
            messages: Conversation history list
            system_prompt: Optional system instruction

        Returns:
            Dictionary with 'ans_ls' containing assistant response
        """
        if self.model is None:
            raise RuntimeError("Gemini not initialized. Call gemini_init first.")

        if not messages:
            app.logger.info("Empty messages; return empty ans_ls.")
            return {"ans_ls": []}

        system_prompt = str(system_prompt or "").strip()

        if system_prompt:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=self.generation_config,
                system_instruction=system_prompt,
            )
        else:
            model = self.model

        # Convert messages to Gemini format
        history = []
        last_user_msg = None

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "user":
                last_user_msg = content
                history.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                history.append({"role": "model", "parts": [content]})

        if not history:
            return {"ans_ls": []}

        try:
            # Start chat with history (except last message)
            chat = model.start_chat(history=history[:-1] if len(history) > 1 else [])

            # Send last user message
            response = await asyncio.to_thread(
                chat.send_message, last_user_msg or history[-1]["parts"][0]
            )
            return {"ans_ls": [response.text]}
        except Exception as e:
            app.logger.error(f"Multiturn generation error: {e}")
            return {"ans_ls": [f"<error: {str(e)}>"]}


if __name__ == "__main__":
    GeminiGeneration(app)
    app.run(transport="stdio")
