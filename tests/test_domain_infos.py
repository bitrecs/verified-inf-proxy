import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.llm_providers import LLMProviderStats


def test_provider_ping():
    ip = "104.18.3.115" # openrouter.com
    thing = LLMProviderStats.tcp_ping(ip, port=443, timeout=2.0)
    print(f"TCP ping {ip}: {thing}")


if __name__ == '__main__':    
    # a = LLMProviderStats.ping_provider_html(LLMProvider.OPEN_ROUTER)
    # print(a)
    # a = LLMProviderStats.ping_provider_html(LLMProvider.VLLM)
    # print(a)
    #infos = LLMProviderStats.print_all_providers_info()
    #print(infos)
    test_provider_ping()
    