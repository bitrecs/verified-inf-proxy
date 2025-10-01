from enum import Enum


class LLMPRovider(Enum):
    OLLAMA_LOCAL = 1
    OPEN_ROUTER = 2
    CHAT_GPT = 3
    VLLM = 4
    GEMINI = 5
    GROK = 6
    CLAUDE = 7
    CHUTES = 8
    CEREBRAS = 9
    GROQ = 10

    @staticmethod
    def from_str(value: str) -> 'LLMPRovider':
         match value.upper():
            case "OLLAMA_LOCAL":
                return LLMPRovider.OLLAMA_LOCAL
            case "OPEN_ROUTER":
                return LLMPRovider.OPEN_ROUTER
            case "CHAT_GPT":
                return LLMPRovider.CHAT_GPT
            case "VLLM":
                return LLMPRovider.VLLM
            case "GEMINI":
                return LLMPRovider.GEMINI
            case "GROK":
                return LLMPRovider.GROK
            case "CLAUDE":
                return LLMPRovider.CLAUDE
            case "CHUTES":
                return LLMPRovider.CHUTES
            case "CEREBRAS":
                return LLMPRovider.CEREBRAS
            case "GROQ":
                return LLMPRovider.GROQ                
            case _:
                raise ValueError("Unknown LLMPRovider server")
        
    def __str__(self):
        return self.name.upper()
