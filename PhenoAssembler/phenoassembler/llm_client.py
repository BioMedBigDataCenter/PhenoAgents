import json
import os
import re
import time
from dataclasses import dataclass
from typing import TypeVar

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from .prompts import SYSTEM_PROMPT
from .schemas import Critics, ExplainableDataProfile


T = TypeVar("T", bound=BaseModel)


@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    temperature: float = 0.2
    timeout: int = 130


class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config

    @classmethod
    def from_env(cls, temperature: float = 0.2) -> "LLMClient":
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required.")
        if not model:
            raise RuntimeError("OPENAI_MODEL is required.")
        base_url = os.getenv(
            "OPENAI_BASE_URL",
            "https://api.openai.com/v1/chat/completions",
        )
        return cls(
            LLMConfig(
                api_key=api_key,
                base_url=base_url,
                model=model,
                temperature=temperature,
            )
        )

    def chat(self, messages: list[dict[str, str]]) -> str:
        response = requests.post(
            self.config.base_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
            json={
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "stream": False,
            },
            timeout=self.config.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"].get("content", "")

    def complete_json(
        self,
        messages: list[dict[str, str]],
        model_class: type[T],
        max_retries: int = 3,
    ) -> T:
        last_error: Exception | None = None
        retry_messages = list(messages)

        for attempt in range(max_retries):
            try:
                content = self.chat(retry_messages)
                json_text = extract_json_object(content)
                return model_class.model_validate_json(json_text)
            except (requests.RequestException, ValidationError, ValueError, KeyError) as exc:
                last_error = exc
                if is_rate_limit_error(exc):
                    time.sleep(2**attempt)
                retry_messages = retry_messages + [
                    {
                        "role": "user",
                        "content": (
                            "The previous response could not be parsed or validated. "
                            "Return exactly one valid JSON object matching the requested schema."
                        ),
                    }
                ]

        raise RuntimeError(f"Failed to obtain valid JSON after {max_retries} attempts: {last_error}")

    def extract_profile(
        self,
        prompt: str,
        max_retries: int = 3,
        max_critics: int = 1,
    ) -> ExplainableDataProfile:
        base_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        profile = self.complete_json(base_messages, ExplainableDataProfile, max_retries)

        for _ in range(max_critics):
            answer = json.dumps(profile.model_dump(), ensure_ascii=False)
            critic_messages = base_messages + [
                {"role": "assistant", "content": answer},
                {
                    "role": "user",
                    "content": (
                        "Inspect the requirements and your previous response. "
                        "If the response should be revised, return JSON with needed=true "
                        "and a concise message explaining the issue. If it is acceptable, "
                        "return needed=false. Use this schema: "
                        f"{Critics.model_json_schema()}"
                    ),
                },
            ]
            critics = self.complete_json(critic_messages, Critics, max_retries)
            if not critics.needed:
                return profile

            revision_messages = base_messages + [
                {"role": "assistant", "content": answer},
                {
                    "role": "user",
                    "content": (
                        "Revise the JSON response according to this critique: "
                        f"{critics.message}. Return exactly one valid JSON object."
                    ),
                },
            ]
            profile = self.complete_json(revision_messages, ExplainableDataProfile, max_retries)

        return profile


def extract_json_object(text: str) -> str:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("No JSON object found in model response.")
    return text[start : end + 1]


def is_rate_limit_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "429" in text or "rate limit" in text
