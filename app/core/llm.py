"""The LLM provider layer.

Everything in the app gets its chat model from `get_llm()`. Nobody else
constructs a model or reads provider config. Swapping OpenAI <-> local is a
.env change, never a code change.
"""


from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# ChatAnthropic / ChatGoogleGenerativeAI are imported lazily inside get_llm so
# those provider packages are only required when that provider is actually used.
from app.core.config import get_settings
from app.core.pricing import cost_usd


def get_llm(streaming: bool = False, temperature: float = None,
            model: str = None, provider: str = None):
    settings = get_settings()
    provider = provider or settings.llm_provider
    model = model or settings.llm_model
    if not model or model == "default":
        model = settings.llm_model
    temp = temperature if temperature is not None else settings.llm_temperature

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model,
            api_key=settings.anthropic_api_key,
            temperature=temp,
            max_tokens=settings.llm_max_tokens,
            streaming=streaming,
            max_retries=3,
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model,
            api_key=settings.google_api_key,
            temperature=temp,
            max_retries=3,
        )
    
    if provider == "ollama":
            return ChatOpenAI(
                model=model,
                api_key="ollama",
                base_url="http://localhost:11434/v1",
                temperature=temp,
                max_tokens=settings.llm_max_tokens,
                streaming=streaming,
                max_retries=3,
            )    

    # existing OpenAI / Ollama path (provider == "openai" or "ollama")

    if provider == "openai" and not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY not set — required for provider 'openai'. "
            "Set it in .env, or use a local provider (LLM_PROVIDER=ollama)."
        )

    return ChatOpenAI(
        model=model,
        api_key=settings.openai_api_key if provider == "openai" else "ollama",
        base_url=settings.llm_base_url,
        temperature=temp,
        max_tokens=settings.llm_max_tokens,
        streaming=streaming,
        max_retries=3,
    )
@dataclass
class CallRequest:
    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


def invoke_tracked(prompt: str, *, system: str | None = None) -> CallRequest:
    settings = get_settings()
    llm = get_llm(streaming=True)

    messages = []
    if system:
        messages.append(SystemMessage(content=system))
    messages.append(HumanMessage(content=prompt))

    response = llm.invoke(messages)

    usage = response.usage_metadata or {}
    in_tok = usage.get("input_tokens", 0)
    out_tok = usage.get("output_tokens", 0)

    return CallRequest(
        text=response.content,
        input_tokens=in_tok,
        output_tokens=out_tok,
        cost_usd=cost_usd(settings.llm_model, in_tok, out_tok),
    )
  




