import time
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import settings

logger = logging.getLogger(__name__)

class LLMProvider:
    def __init__(self):
        self.api_key = (settings.LLM_API_KEY or "").strip()
        self.base_url = (settings.LLM_BASE_URL or "").strip()
        self.model_name = (settings.LLM_MODEL_NAME or "").strip()

        self.client = None
        self.last_telemetry = {}
        self.total_invocations = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost_usd = 0.0

        self._initialize_client()

    def _initialize_client(self):
        if self.api_key:
            try:
                from langchain_openai import ChatOpenAI
                kwargs = {
                    "model": self.model_name or "gpt-4o-mini",
                    "api_key": self.api_key,
                    "temperature": 0.2,
                    "max_tokens": 1000
                }
                if self.base_url:
                    kwargs["base_url"] = self.base_url

                self.client = ChatOpenAI(**kwargs)
                logger.info(f"Initialized ChatOpenAI with model={self.model_name}, base_url={self.base_url}")
            except Exception as e:
                logger.warning(f"Failed to initialize ChatOpenAI: {e}")
                self.client = None

    def invoke(self, system_prompt: str, user_prompt: str, fallback_response: str = "") -> str:
        """Invokes LLM with automatic telemetry tracking and fallback protection."""
        start_time = time.time()

        # Re-check settings in case env was updated
        current_key = (settings.LLM_API_KEY or "").strip()
        if current_key and current_key != self.api_key:
            self.api_key = current_key
            self.base_url = (settings.LLM_BASE_URL or "").strip()
            self.model_name = (settings.LLM_MODEL_NAME or "").strip()
            self._initialize_client()

        response_content = None
        prompt_tokens = len((system_prompt + user_prompt).split()) * 1.3
        completion_tokens = 0

        if self.client:
            try:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                res = self.client.invoke(messages)
                if res and hasattr(res, 'content') and res.content:
                    response_content = str(res.content)

                    # Extract usage metadata if provided by provider
                    if hasattr(res, 'response_metadata') and isinstance(res.response_metadata, dict):
                        token_usage = res.response_metadata.get('token_usage', {})
                        if token_usage:
                            prompt_tokens = token_usage.get('prompt_tokens', prompt_tokens)
                            completion_tokens = token_usage.get('completion_tokens', completion_tokens)
            except Exception as e:
                logger.error(f"LLM API execution error: {e}. Utilizing intelligent local response fallback.")

        if not response_content:
            response_content = fallback_response
            completion_tokens = len(fallback_response.split()) * 1.3

        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Estimate cost ($0.15/1M input, $0.60/1M output for mini models)
        estimated_cost = round(((prompt_tokens * 0.00000015) + (completion_tokens * 0.0000006)), 6)

        self.last_telemetry = {
            "model": self.model_name or "local-synthesis",
            "duration_ms": duration_ms,
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "total_tokens": int(prompt_tokens + completion_tokens),
            "estimated_cost_usd": estimated_cost,
            "is_llm": self.client is not None
        }

        self.total_invocations += 1
        self.total_prompt_tokens += int(prompt_tokens)
        self.total_completion_tokens += int(completion_tokens)
        self.total_cost_usd += estimated_cost

        return response_content

    def get_telemetry_summary(self):
        return {
            "last": self.last_telemetry,
            "cumulative": {
                "invocations": self.total_invocations,
                "total_prompt_tokens": self.total_prompt_tokens,
                "total_completion_tokens": self.total_completion_tokens,
                "total_cost_usd": round(self.total_cost_usd, 6)
            }
        }

llm_provider = LLMProvider()
