import httpx

from app.config import settings


class LlmClientError(RuntimeError):
    pass


STOP_SEQUENCES = [
    "\nThinking Process:",
    "\nInternal Monologue:",
    "\nDrafting the response:",
    "\nCheck Constraints:",
    "\nCheck Against Constraints:",
    "\nCheck Accuracy",
    "\nFinal Output Generation:",
    "\nOutput Generation",
    "\nSelf-Correction/",
    "\n* Meets all constraints",
    "\n* Output matches",
    "\n* Proceed",
    "\n* Done",
    "\n4. Check",
    "\n5. Final",
    "\n**4. Check",
    "\n**5. Final",
]


async def create_chat_completion(
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> dict[str, str]:
    payload = {
        "model": settings.vllm_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stop": STOP_SEQUENCES,
    }
    headers = {"Authorization": f"Bearer {settings.vllm_api_key}"}

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.post(
                f"{settings.vllm_base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise LlmClientError("vLLM request failed") from exc

    try:
        data = response.json()
        message = data["choices"][0]["message"]
        if not isinstance(message, dict):
            raise TypeError

        role = message["role"]
        content = message["content"]
        if role != "assistant" or not isinstance(content, str):
            raise TypeError

        return {"role": role, "content": content}
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise LlmClientError("vLLM response format is invalid") from exc
