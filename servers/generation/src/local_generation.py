import os
import sys
import base64
import mimetypes
import traceback
import asyncio
from typing import Any, Dict, List, Union, Optional


class LocalGenerationService:
    """Local generation service for streaming generation in demo mode.

    This service provides streaming generation capabilities for the UI demo,
    supporting both OpenAI-compatible API endpoints and Google Gemini API.
    """

    def __init__(
        self,
        backend_configs: Dict[str, Any],
        sampling_params: Dict[str, Any],
        extra_params: Optional[Dict[str, Any]] = None,
        backend: str = "openai",
    ):
        """Initialize local generation service.

        Args:
            backend_configs: Dictionary of backend configurations
            sampling_params: Sampling parameters for generation
            extra_params: Optional extra parameters
            backend: Backend name ("openai" or "gemini")
        """
        self.backend = backend
        self.sampling_params = sampling_params.copy()
        if extra_params:
            self.sampling_params["extra_body"] = extra_params

        if backend == "gemini":
            self._init_gemini(backend_configs)
        else:
            self._init_openai(backend_configs)

    def _init_openai(self, backend_configs: Dict[str, Any]) -> None:
        """Initialize OpenAI backend."""
        from openai import AsyncOpenAI

        openai_cfg = backend_configs.get("openai", {})
        self.model_name = openai_cfg.get("model_name")
        base_url = openai_cfg.get("base_url")
        api_key = openai_cfg.get("api_key") or os.environ.get("LLM_API_KEY")

        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    def _init_gemini(self, backend_configs: Dict[str, Any]) -> None:
        """Initialize Gemini backend."""
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "google-generativeai is not installed. "
                "Install with: pip install google-generativeai"
            )

        gemini_cfg = backend_configs.get("gemini", {})
        api_key = gemini_cfg.get("api_key") or os.environ.get("GOOGLE_API_KEY")

        if not api_key:
            raise ValueError(
                "Gemini API key required. Set GOOGLE_API_KEY env var or pass in backend_configs."
            )

        genai.configure(api_key=api_key)

        self.model_name = gemini_cfg.get("model_name", "gemini-3-pro-preview")
        generation_config = gemini_cfg.get("generation_config", {
            "temperature": self.sampling_params.get("temperature", 0.7),
            "top_p": self.sampling_params.get("top_p", 0.8),
            "max_output_tokens": self.sampling_params.get("max_tokens", 2048),
        })

        self.genai = genai
        self.gemini_model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=generation_config,
        )
        self.generation_config = generation_config

    def _extract_text_prompts(
        self, prompt_ls: List[Union[str, Dict[str, Any]]]
    ) -> List[str]:
        """Extract text content from various prompt formats.

        Args:
            prompt_ls: List of prompts in various formats (str, dict, etc.)

        Returns:
            List of text strings

        Raises:
            ValueError: If prompt format is not supported
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
                    raise ValueError(f"Unsupported dict prompt format: {m}")
            elif isinstance(m, str):
                prompts.append(m)
            else:
                raise ValueError(f"Unsupported message format: {m}")
        return prompts

    def _to_data_url(self, path_or_url: str) -> str:
        """Convert image path to data URL.

        Args:
            path_or_url: Image file path or URL

        Returns:
            Data URL string (data:image/...;base64,...)

        Raises:
            FileNotFoundError: If image file doesn't exist
        """
        s = str(path_or_url).strip()

        if s.startswith(("http://", "https://", "data:image/")):
            return s

        if not os.path.isfile(s):
            raise FileNotFoundError(f"image not found: {s}")
        mime, _ = mimetypes.guess_type(s)
        mime = mime or "image/jpeg"
        with open(s, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime};base64,{b64}"

    async def generate_stream(
        self,
        prompt_ls: List[Union[str, Dict[str, Any]]],
        system_prompt: str = "",
        multimodal_path: List[List[str]] = None,
        image_tag: Optional[str] = None,
        **kwargs,
    ):
        """Generate streaming response for prompts with optional multimodal inputs.

        Args:
            prompt_ls: List of prompts (only first prompt is used)
            system_prompt: Optional system prompt
            multimodal_path: Optional list of image path lists
            image_tag: Optional tag to split prompt and insert images
            **kwargs: Additional keyword arguments

        Yields:
            Content delta strings as they are generated
        """
        prompts = self._extract_text_prompts(prompt_ls)
        if not prompts:
            return

        p = prompts[0]

        pths = []
        if multimodal_path and len(multimodal_path) > 0:
            entry = multimodal_path[0]
            if isinstance(entry, (str, bytes)):
                entry = [str(entry)]
            elif not isinstance(entry, list):
                entry = []
            pths = [str(pth).strip() for pth in entry if str(pth).strip()]

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if not pths:
            messages.append({"role": "user", "content": p})
        else:
            content: List[Dict[str, Any]] = []

            use_tag_mode = bool(image_tag) and bool(str(image_tag).strip())
            tag = str(image_tag).strip() if use_tag_mode else None

            if use_tag_mode:
                parts = p.split(tag)
                for j, part in enumerate(parts):
                    if part.strip():
                        content.append({"type": "text", "text": part})
                    if j < len(pths):
                        img_url = self._to_data_url(pths[j])
                        if img_url:
                            content.append(
                                {"type": "image_url", "image_url": {"url": img_url}}
                            )
            else:
                for mp in pths:
                    img_url = self._to_data_url(mp)
                    if img_url:
                        content.append(
                            {"type": "image_url", "image_url": {"url": img_url}}
                        )
                if p:
                    content.append({"type": "text", "text": p})

            messages.append({"role": "user", "content": content})

        try:
            stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=True,
                **self.sampling_params,
            )

            async for chunk in stream:
                if chunk.choices:
                    content_delta = chunk.choices[0].delta.content or ""
                    if content_delta:
                        yield content_delta

        except Exception as e:
            print("\n[LocalGen] Error Detected:")
            traceback.print_exc()
            yield f"\n[Error: {e}]"

    async def multiturn_generate_stream(
        self, messages: List[Dict[str, str]], system_prompt: str = "", **kwargs
    ):
        """Generate streaming response for multi-turn conversation.

        Args:
            messages: Conversation history list, each message format: {"role": "user"|"assistant", "content": "..."}
            system_prompt: Optional system prompt
            **kwargs: Additional keyword arguments

        Yields:
            Content delta strings as they are generated
        """
        if not messages:
            return

        if self.backend == "gemini":
            async for token in self._gemini_multiturn_stream(messages, system_prompt):
                yield token
        else:
            async for token in self._openai_multiturn_stream(messages, system_prompt):
                yield token

    async def _openai_multiturn_stream(
        self, messages: List[Dict[str, str]], system_prompt: str = ""
    ):
        """OpenAI backend for multi-turn streaming."""
        # Build complete message list
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})

        # Add conversation history
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant", "system") and content:
                full_messages.append({"role": role, "content": str(content)})

        if not full_messages or all(m["role"] == "system" for m in full_messages):
            return

        try:
            stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=full_messages,
                stream=True,
                **self.sampling_params,
            )

            async for chunk in stream:
                if chunk.choices:
                    content_delta = chunk.choices[0].delta.content or ""
                    if content_delta:
                        yield content_delta

        except Exception as e:
            print("\n[LocalGen Multiturn OpenAI] Error Detected:")
            traceback.print_exc()
            yield f"\n[Error: {e}]"

    async def _gemini_multiturn_stream(
        self, messages: List[Dict[str, str]], system_prompt: str = ""
    ):
        """Gemini backend for multi-turn streaming."""
        import queue
        import threading

        token_queue = queue.Queue()

        def generate_in_thread():
            """Run Gemini generation in a separate thread."""
            try:
                # Create model with system instruction if provided
                if system_prompt:
                    model = self.genai.GenerativeModel(
                        model_name=self.model_name,
                        generation_config=self.generation_config,
                        system_instruction=system_prompt,
                    )
                else:
                    model = self.gemini_model

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
                    token_queue.put(None)
                    return

                # Start chat with history (except last message)
                chat = model.start_chat(history=history[:-1] if len(history) > 1 else [])

                # Send last user message with streaming
                response = chat.send_message(
                    last_user_msg or history[-1]["parts"][0],
                    stream=True,
                )

                # Put tokens into queue
                for chunk in response:
                    if chunk.text:
                        token_queue.put(chunk.text)

                token_queue.put(None)  # Signal completion

            except Exception as e:
                print("\n[LocalGen Multiturn Gemini] Error in thread:")
                traceback.print_exc()
                token_queue.put(f"\n[Error: {e}]")
                token_queue.put(None)

        # Start generation in background thread
        thread = threading.Thread(target=generate_in_thread, daemon=True)
        thread.start()

        # Yield tokens from queue
        while True:
            try:
                # Use timeout to allow async context switches
                token = await asyncio.to_thread(token_queue.get, timeout=60)
                if token is None:
                    break
                yield token
            except queue.Empty:
                # Timeout - check if thread is still alive
                if not thread.is_alive():
                    break
            except Exception as e:
                print(f"\n[LocalGen Multiturn Gemini] Queue error: {e}")
                yield f"\n[Error: {e}]"
                break
