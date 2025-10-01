from app.llm_providers import LLMPRovider


def test_parse_provider_from_text():
    p = "chat_gpt"
    thing = LLMPRovider.from_str(p)
    assert thing == LLMPRovider.CHAT_GPT

    p = "GeminI"
    thing = LLMPRovider.from_str(p)
    assert thing == LLMPRovider.GEMINI

def test_provider_to_string():
    p = LLMPRovider.CLAUDE
    s = str(p)
    assert s == "CLAUDE"
    assert s != "claude"