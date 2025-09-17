# backend/assistants/weather_ai.py
from __future__ import annotations
import os
import asyncio
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

HF_MODEL_ID = os.environ.get("HF_MODEL_ID", "tiiuae/falcon-7b-instruct")
HF_API_TOKEN = os.environ.get("HF_API_TOKEN")  # put this in your .env

SYSTEM_PROMPT = (
    "You are an advanced meteorological assistant specializing in severe weather, tornadoes, "
    "and radar interpretation. Use clear, actionable language suitable for the general public. "
    "When giving protective actions, prioritize life safety and brevity."
)

TEMPLATE_FALLBACK = (
    "Automated summary: Elevated risk noted in the near term. Monitor official warnings. "
    "Seek sturdy shelter if a tornado warning is issued. Have multiple ways to receive alerts."
)

class HFWeatherAssistantHTTP:
    """
    Simple async client for Hugging Face Inference API text-generation models.
    No local model hosting required.
    """
    def __init__(self, model_id: Optional[str] = None, token: Optional[str] = None, timeout: float = 25.0):
        self.model_id = model_id or HF_MODEL_ID
        self.token = token or HF_API_TOKEN
        self.timeout = timeout
        if not self.token:
            logger.warning("[HFWeatherAssistant] HF_API_TOKEN not set; responses will use fallback text.")

    async def _generate(self, prompt: str, max_new_tokens: int = 220) -> str:
        if not self.token:
            return TEMPLATE_FALLBACK

        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": int(max_new_tokens),
                "return_full_text": False,
                "temperature": 0.2,
                "top_p": 0.9
            }
        }
        url = f"https://api-inference.huggingface.co/models/{self.model_id}"

        # light retry for 503 (model loading)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 503:  # loading
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    if isinstance(data, list) and data and "generated_text" in data[0]:
                        return (data[0]["generated_text"] or "").strip() or TEMPLATE_FALLBACK
                    if isinstance(data, dict) and "generated_text" in data:
                        return (data["generated_text"] or "").strip() or TEMPLATE_FALLBACK
                    if isinstance(data, dict) and "error" in data:
                        logger.warning(f"[HF] API error: {data.get('error')}")
                        return TEMPLATE_FALLBACK
                    return TEMPLATE_FALLBACK
                except Exception as e:
                    logger.warning(f"[HF] attempt {attempt+1} failed: {e}")
                    await asyncio.sleep(0.8 * (attempt + 1))
        return TEMPLATE_FALLBACK

    async def summarize_alert(self, prompt: str, max_new_tokens: int = 220) -> str:
        text = (
            f"{SYSTEM_PROMPT}\n\n"
            f"{prompt.strip()}\n\n"
            "Write a concise, public-facing summary (<= 150 words) with 1) immediate threat, "
            "2) protective actions, 3) key meteorological factors."
        )
        return await self._generate(text, max_new_tokens=max_new_tokens)

    async def answer_question(self, question: str, context: Optional[str] = None, max_new_tokens: int = 220) -> str:
        text = f"{SYSTEM_PROMPT}\n\n"
        if context:
            text += f"Context:\n{context.strip()}\n\n"
        text += f"User question: {question.strip()}\n\nAnswer clearly and briefly."
        return await self._generate(text, max_new_tokens=max_new_tokens)


# export a ready-to-use singleton
weather_ai = HFWeatherAssistantHTTP()
