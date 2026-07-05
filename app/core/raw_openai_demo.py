from openai import OpenAI

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.llm_base_url or None,
    )

    messages = [
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "In one sentence, what is an AI agent?"},
    ]

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )

    print(response.choices[0].message.content)

    u = response.usage
    print(f"prompt={u.prompt_tokens} completion={u.completion_tokens} total={u.total_tokens}")


if __name__ == "__main__":
    main()