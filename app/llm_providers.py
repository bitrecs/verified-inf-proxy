from enum import Enum
import subprocess
import socket
import platform
import re
from itertools import islice

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


class LLMProviderStats:

    @staticmethod
    def provider_domain(provider: LLMProvider) -> str:
        match provider:
            case LLMProvider.OLLAMA_LOCAL:
                return ""
            case LLMProvider.CHAT_GPT:
                return "api.openai.com"
            case LLMProvider.OPEN_ROUTER:
                return "openrouter.ai"
            case LLMProvider.VLLM:
                return ""
            case LLMProvider.GEMINI:
                return "generativelanguage.googleapis.com"
            case LLMProvider.GROK:
                return "api.x.ai"
            case LLMProvider.CLAUDE:
                return "api.anthropic.com"
            case LLMProvider.CHUTES:
                return "llm.chutes.ai"
            case LLMProvider.CEREBRAS:
                return "api.cerebras.ai"
            case LLMProvider.GROQ:
                return "api.groq.com"
            case _:
                raise ValueError("Unknown LLMProvider server")  
            
    @staticmethod
    def ping_provider(provider: LLMProvider) -> str:
        """Pings, traceroutes, and retrieves domain info for the given LLMProvider, returning the report as a string."""
        domain = LLMProviderStats.provider_domain(provider)
        if not domain:
            return f"No domain to ping for provider {provider} (likely local)."
        
        # Gather domain info
        try:
            ip_address = socket.gethostbyname(domain)
        except socket.gaierror:
            ip_address = "DNS resolution failed"
        
        print(f"Pinging provider {provider} at domain {domain} (IP: {ip_address})")
        # Perform ping and extract average time
        avg_ping_time = "N/A"
        ping_status = "Failure"
        try:
            ping_cmd = ["ping", "-c", "4", domain] if platform.system() != "Windows" else ["ping", "-n", "4", domain]
            ping_result = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=10)
            if ping_result.returncode == 0:
                ping_status = "Success"
                # Parse average ping time from output (e.g., "round-trip min/avg/max/stddev = 10.0/15.0/20.0/5.0 ms")
                match = re.search(r'round-trip.*= (\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+) ms', ping_result.stdout)
                if match:
                    avg_ping_time = f"{match.group(2)} ms"
        except subprocess.TimeoutExpired:
            ping_status = "Failure (Timeout)"
        except Exception as e:
            ping_status = f"Failure ({str(e)})"
        
        # Perform traceroute
        trace_output = ""
        if 1==2:
            try:
                trace_cmd = ["traceroute", domain] if platform.system() != "Windows" else ["tracert", domain]
                trace_result = subprocess.run(trace_cmd, capture_output=True, text=True, timeout=30)
                trace_output = trace_result.stdout.strip() if trace_result.returncode == 0 else "Traceroute failed"
            except subprocess.TimeoutExpired:
                trace_output = "Traceroute timed out"
            except Exception as e:
                trace_output = f"Traceroute error: {str(e)}"
            
        # Prepare table data as list of tuples (metric, details)
        table_data = [
            ("Provider", str(provider)),
            ("Domain", domain),
            ("IP Address", ip_address),
            ("Ping Status", ping_status),
            ("Average Ping Time", avg_ping_time),
            #("Traceroute Results", trace_output)
        ]
        
        # Build table as a string using standard Python formatting
        col_width_metric = 20  # Fixed width for "Metric" column
        col_width_details = 80  # Fixed width for "Details" column (adjust as needed for long outputs)
        
        output = ""
        # Print table header
        output += "+" + "-" * col_width_metric + "+" + "-" * col_width_details + "+\n"
        output += f"| {'Metric'.ljust(col_width_metric)} | {'Details'.ljust(col_width_details)} |\n"
        output += "+" + "-" * col_width_metric + "+" + "-" * col_width_details + "+\n"
        
        # Print table rows
        for metric, details in table_data:
            # Truncate or wrap details if too long (simple truncation here)
            details = details[:col_width_details-3] + "..." if len(details) > col_width_details else details
            output += f"| {metric.ljust(col_width_metric)} | {details.ljust(col_width_details)} |\n"
        
        # Print table footer
        output += "+" + "-" * col_width_metric + "+" + "-" * col_width_details + "+\n"
        
        return output
    
    @staticmethod
    def ping_provider_html(provider: LLMProvider) -> str:
        """Pings, traceroutes, and retrieves domain info for the given LLMProvider, returning a clean HTML page."""
        domain = LLMProviderStats.provider_domain(provider)
        if not domain:
            html_content = f"No domain to ping for provider {provider} (likely local)."
        else:
            # Gather domain info
            try:
                ip_address = socket.gethostbyname(domain)
            except socket.gaierror:
                ip_address = "DNS resolution failed"
            
            print(f"Pinging provider {provider} at domain {domain} (IP: {ip_address})")
            # Perform ping and extract average time
            avg_ping_time = "N/A"
            ping_status = "Failure"
            try:
                ping_cmd = ["ping", "-c", "4", domain] if platform.system() != "Windows" else ["ping", "-n", "4", domain]
                ping_result = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=10)
                if ping_result.returncode == 0:
                    ping_status = "Success"
                    # Parse average ping time from output (e.g., "round-trip min/avg/max/stddev = 10.0/15.0/20.0/5.0 ms")
                    match = re.search(r'round-trip.*= (\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+) ms', ping_result.stdout)
                    if match:
                        avg_ping_time = f"{match.group(2)} ms"
            except subprocess.TimeoutExpired:
                ping_status = "Failure (Timeout)"
            except Exception as e:
                ping_status = f"Failure ({str(e)})"
            
            # Perform traceroute
            trace_output = ""
            if 1==2:
                try:
                    trace_cmd = ["traceroute", domain] if platform.system() != "Windows" else ["tracert", domain]
                    trace_result = subprocess.run(trace_cmd, capture_output=True, text=True, timeout=30)
                    trace_output = trace_result.stdout.strip() if trace_result.returncode == 0 else "Traceroute failed"
                except subprocess.TimeoutExpired:
                    trace_output = "Traceroute timed out"
                except Exception as e:
                    trace_output = f"Traceroute error: {str(e)}"
                
            # Prepare table data
            table_data = [
                ("Provider", str(provider)),
                ("Domain", domain),
                ("IP Address", ip_address),
                ("Ping Status", ping_status),
                ("Average Ping Time", avg_ping_time),
                #("Traceroute Results", trace_output)
            ]
            
            # Build HTML table rows
            rows_html = ""
            for metric, details in table_data:
                rows_html += f"<tr><td>{metric}</td><td>{details}</td></tr>\n"
            
            html_content = f"""
            <table>
                <thead>
                    <tr><th>Metric</th><th>Details</th></tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
            """
        
        # Full HTML page with inline CSS to match a clean /log style
        html_page = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Ping Report for {provider}</title>
            <style>
                body {{
                    font-family: 'Courier New', monospace;
                    background-color: #f4f4f4;
                    color: #333;
                    margin: 20px;
                    padding: 20px;
                    text-align: center;
                }}
                h1 {{
                    color: #555;
                }}
                table {{
                    width: 80%;
                    margin: 20px auto;
                    border-collapse: collapse;
                    background-color: #fff;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                    font-weight: bold;
                }}
                tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
            </style>
        </head>
        <body>
            <h1>Ping Report for {provider}</h1>
            {html_content}
        </body>
        </html>
        """
        return html_page
    
    @staticmethod
    def print_all_providers_info() -> str:
        output = ""
        for provider in islice(LLMProvider, 3):
        #for provider in LLMProvider:
            output += "\n" + "="*80 + "\n"
            output += LLMProviderStats.ping_provider(provider)
            output += "\n" + "="*80 + "\n"
        return output
    
    @staticmethod
    def print_all_providers_info_html() -> str:
        exemptions = [LLMProvider.OLLAMA_LOCAL, LLMProvider.VLLM]
        html_output = ""
        #for provider in islice(LLMProvider, 3):
        for provider in LLMProvider:
            if provider in exemptions:
                continue
            html_output += LLMProviderStats.ping_provider_html(provider)
        return html_output