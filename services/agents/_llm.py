from groq import Groq
from google import genai
from config import GROQ_API_KEY, GROQ_MODEL, GEMINI_API_KEY, GEMINI_MODEL

PROVIDERS = {
    "groq": {"label": "Groq Llama 3.1 8B", "model": GROQ_MODEL},
    "gemini": {"label": "Gemini 2.5 Flash", "model": GEMINI_MODEL},
}
DEFAULT_PROVIDER = "groq"

_groq_client = None
_gemini_client = None


def _get_groq() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


def _get_gemini() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client


def chat_completion(prompt: str, provider: str = DEFAULT_PROVIDER) -> str:
    if provider not in PROVIDERS:
        provider = DEFAULT_PROVIDER

    if provider == "gemini":
        response = _get_gemini().models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return response.text

    response = _get_groq().chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content
