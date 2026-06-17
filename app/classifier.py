import json
import asyncio
import os
import httpx

from pydantic import ValidationError
from .prompts import SYSTEM_PROMPT
from .schemas import LLMOutput, RequestResult, Category, Priority

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = os.getenv("GROQ_URL")
GROQ_MODEL = os.getenv("GROQ_MODEL")


def build_prompt(row: dict) -> str:
    return f"""Channel: {row['channel']}
Timestamp: {row['timestamp']}
Request text: {row['raw_text']}"""


def fallback_result(row: dict, error: str) -> RequestResult:
    return RequestResult(
        id=str(row["id"]),
        channel=str(row["channel"]),
        timestamp=str(row["timestamp"]),
        raw_text=str(row["raw_text"]),
        category=Category.OUT_OF_SCOPE,
        target_department=None,
        priority=Priority.LOW,
        short_summary="Could not classify this request automatically.",
        requested_actions=[],
        needs_clarification=True,
        estimated_effort=None,
        confidence_score=None,
        llm_error=error,
    )


async def classify_request(row: dict, client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> RequestResult:
    async with semaphore:
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_prompt(row)},
            ],
            "temperature": 0.1,
        }

        try:
            response = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()

            data = response.json()

            if not data.get("choices"):
                return fallback_result(row, f"Unexpected Groq response: {data}")

            raw_text = data["choices"][0]["message"]["content"].strip()

            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
                raw_text = raw_text.strip()

            parsed = json.loads(raw_text)
            llm_output = LLMOutput(**parsed)

            return RequestResult(
                id=str(row["id"]),
                channel=str(row["channel"]),
                timestamp=str(row["timestamp"]),
                raw_text=str(row["raw_text"]),
                **llm_output.model_dump(),
            )

        except json.JSONDecodeError as e:
            return fallback_result(row, f"JSON parse error: {e}")
        except ValidationError as e:
            return fallback_result(row, f"Validation error: {e}")
        except httpx.HTTPStatusError as e:
            return fallback_result(row, f"Groq API error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            return fallback_result(row, f"Unexpected error: {e}")


async def classify_all(rows: list[dict]) -> list[RequestResult]:
    semaphore = asyncio.Semaphore(5)
    async with httpx.AsyncClient() as client:
        tasks = [classify_request(row, client, semaphore) for row in rows]
        return await asyncio.gather(*tasks)