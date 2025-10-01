from enum import Enum


class LLMProvider(Enum):
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
    def from_str(value: str) -> 'LLMProvider':
         match value.upper():
            case "OLLAMA_LOCAL":
                return LLMProvider.OLLAMA_LOCAL
            case "OPEN_ROUTER":
                return LLMProvider.OPEN_ROUTER
            case "CHAT_GPT":
                return LLMProvider.CHAT_GPT
            case "VLLM":
                return LLMProvider.VLLM
            case "GEMINI":
                return LLMProvider.GEMINI
            case "GROK":
                return LLMProvider.GROK
            case "CLAUDE":
                return LLMProvider.CLAUDE
            case "CHUTES":
                return LLMProvider.CHUTES
            case "CEREBRAS":
                return LLMProvider.CEREBRAS
            case "GROQ":
                return LLMProvider.GROQ                
            case _:
                raise ValueError("Unknown LLMPRovider server")
        
    def __str__(self):
        return self.name.upper()
