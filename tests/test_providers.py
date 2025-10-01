from app.llm_providers import LLMProvider


def test_parse_provider_from_text():
    p = "chat_gpt"
    thing = LLMProvider.from_str(p)
    assert thing == LLMProvider.CHAT_GPT

    p = "GeminI"
    thing = LLMProvider.from_str(p)
    assert thing == LLMProvider.GEMINI

def test_provider_to_string():
    p = LLMProvider.CLAUDE
    s = str(p)
    assert s == "CLAUDE"
    assert s != "claude"