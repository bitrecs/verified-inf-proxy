import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import os

# Add the project root to sys.path so 'app' can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.llm_providers import LLMProvider, LLMProviderStats

class TestPingProvider(unittest.TestCase):
    
    @patch('app.llm_providers.subprocess.run')
    @patch('app.llm_providers.socket.gethostbyname')
    def test_ping_provider_with_domain(self, mock_gethostbyname, mock_subprocess_run):
        """Test ping_provider for a provider with a domain (e.g., CHAT_GPT)."""
        # Mock DNS resolution
        mock_gethostbyname.return_value = "104.18.32.146"
        
        # Mock ping and traceroute subprocess calls
        mock_ping = MagicMock()
        mock_ping.returncode = 0
        mock_ping.stdout = "PING successful"
        mock_trace = MagicMock()
        mock_trace.returncode = 0
        mock_trace.stdout = "Traceroute successful"
        mock_subprocess_run.side_effect = [mock_ping, mock_trace]
        
        # Capture printed output
        captured_output = io.StringIO()
        with patch('sys.stdout', captured_output):
            LLMProviderStats.ping_provider(LLMProvider.CHAT_GPT)
        
        # Assert output contains expected table elements
        output = captured_output.getvalue()
        self.assertIn("CHAT_GPT", output)
        self.assertIn("api.openai.com", output)
        self.assertIn("104.18.32.146", output)
        self.assertIn("PING successful", output)
        self.assertIn("Traceroute successful", output)
        self.assertIn("+", output)  # Table borders
    
    @patch('app.llm_providers.subprocess.run')
    @patch('app.llm_providers.socket.gethostbyname')
    def test_ping_provider_dns_failure(self, mock_gethostbyname, mock_subprocess_run):
        """Test ping_provider when DNS resolution fails."""
        # Mock DNS failure
        mock_gethostbyname.side_effect = Exception("DNS error")
        
        # Mock ping and traceroute (they should still run)
        mock_ping = MagicMock()
        mock_ping.returncode = 0
        mock_ping.stdout = "PING output"
        mock_trace = MagicMock()
        mock_trace.returncode = 0
        mock_trace.stdout = "Traceroute output"
        mock_subprocess_run.side_effect = [mock_ping, mock_trace]
        
        # Capture printed output
        captured_output = io.StringIO()
        with patch('sys.stdout', captured_output):
            LLMProviderStats.ping_provider(LLMProvider.CHAT_GPT)
        
        # Assert DNS failure is noted
        output = captured_output.getvalue()
        self.assertIn("DNS resolution failed", output)
    
    def test_ping_provider_no_domain(self):
        """Test ping_provider for a provider without a domain (e.g., OLLAMA_LOCAL)."""
        # Capture printed output
        captured_output = io.StringIO()
        with patch('sys.stdout', captured_output):
            LLMProviderStats.ping_provider(LLMProvider.OLLAMA_LOCAL)
        
        # Assert no-domain message is printed
        output = captured_output.getvalue()
        self.assertIn("No domain to ping for provider OLLAMA_LOCAL", output)

if __name__ == '__main__':
    #unittest.main()

    a = LLMProviderStats.ping_provider(LLMProvider.OPEN_ROUTER)
    print(a)
    a = LLMProviderStats.ping_provider(LLMProvider.VLLM)
    print(a)

    #infos = LLMProviderStats.print_all_providers_info()
    #print(infos)
    