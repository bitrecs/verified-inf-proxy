import html
import json
from typing import List, Dict, Any


class HTMLLog:

    @staticmethod
    def render_verified_display(verified: List[Dict[str, Any]], bt_network: str, bt_netuid: int) -> str:
        """Render the verified responses display page."""
        rows_html = ""
        miners = set()
        for item in verified:
            timestamp = item.get('timestamp', 'N/A')
            hotkey = item.get('hotkey', 'N/A')
            model = item.get('model', 'N/A')
            duration = item.get('duration', 'N/A') or 'N/A'
            signature = item.get('signature', 'N/A')
            provider = item.get('provider', 'N/A')
            miners.add(hotkey)
            
            # Parse response_json to extract content
            response_content = 'N/A'
            miner_url = f"https://dashboard.bitrecs.ai/miner?uid={html.escape(hotkey)}"
            
            try:
                response_data = json.loads(item.get('completion_response', '{}'))
                if 'choices' in response_data and response_data['choices']:
                    content = response_data['choices'][0].get('message', {}).get('content', '')
                    response_content = content[:300] + '...' if len(content) > 300 else content
                elif 'output' in response_data:
                    output = response_data['output']
                    if isinstance(output, list) and len(output) > 0:
                        for out in output:
                            if out.get('type') == 'message':
                                content_list = out.get('content', [])
                                if content_list and isinstance(content_list, list):
                                    text = content_list[0].get('text', '')
                                    response_content = text[:300] + '...' if len(text) > 300 else text
                                    break
            except:
                pass

            # Escape all dynamic content for HTML safety
            escaped_timestamp = html.escape(str(timestamp))
            escaped_hotkey = html.escape(str(hotkey))
            escaped_model = html.escape(str(model))
            escaped_provider = html.escape(str(provider))
            escaped_response_content = html.escape(str(response_content))
            escaped_duration = html.escape(str(duration))
            escaped_signature = html.escape(str(signature))

            rows_html += f"""
                        <tr>
                            <td data-label="{html.escape('Timestamp')}" class="timestamp">{escaped_timestamp}</td>
                            <td data-label="{html.escape('Hotkey')}" class="hotkey"><a href="{miner_url}" target="_blank" rel="noopener noreferrer">{escaped_hotkey}</a></td>
                            <td data-label="{html.escape('Model')}" class="model">{escaped_model}</td>
                            <td data-label="{html.escape('Provider')}" class="model">{escaped_provider}</td>
                            <td data-label="{html.escape('Response')}" class="response">{escaped_response_content}</td>
                            <td data-label="{html.escape('Duration')}" class="duration">{escaped_duration}s</td>
                            <td data-label="{html.escape('Signature')}" class="signature">{escaped_signature}</td>
                        </tr>
            """

        # Escape header data as well
        escaped_bt_network = html.escape(str(bt_network))
        escaped_bt_netuid = html.escape(str(bt_netuid))
        escaped_len_verified = html.escape(str(len(verified)))
        escaped_len_miners = html.escape(str(len(miners)))

        return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verified Inference Log</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: #0d1117;
                color: #c9d1d9;
                line-height: 1.6;
            }}
            .container {{
                width: 100%;
                padding: 20px;
                max-width: 100vw;
                overflow-x: hidden;
            }}
            .header {{
                background: #161b22;
                padding: 20px;
                border-bottom: 1px solid #30363d;
                margin-bottom: 20px;
                border-radius: 6px;
            }}
            .header h1 {{
                font-size: 24px;
                color: #58a6ff;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
                gap: 15px;  /* Space between logo and title */
            }}
            .header img {{
                height: 40px;  /* Adjust logo size as needed */
                width: auto;
            }}
            .stats {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                font-size: 14px;
            }}
            .stat-item {{
                background: #0d1117;
                padding: 8px 12px;
                border-radius: 6px;
                border: 1px solid #30363d;
            }}
            .stat-label {{
                color: #8b949e;
                margin-right: 8px;
            }}
            .table-container {{
                overflow-x: auto;
                background: #161b22;
                border-radius: 6px;
                border: 1px solid #30363d;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            thead {{
                background: #0d1117;
            }}
            th {{
                padding: 12px;
                text-align: left;
                font-weight: 600;
                color: #c9d1d9;
                border-bottom: 1px solid #30363d;
                white-space: nowrap;
            }}
            td {{
                padding: 12px;
                border-bottom: 1px solid #21262d;
                vertical-align: top;
            }}
            tr:hover {{
                background: #0d1117;
            }}
            .timestamp {{
                color: #8b949e;
                font-size: 13px;
                white-space: nowrap;
            }}
            .hotkey {{
                font-family: 'Courier New', monospace;
                font-size: 14px;
                color: #79c0ff;
                word-break: break-all;
                max-width: 150px;
            }}
            .model {{
                color: #a5d6ff;
                font-size: 13px;
                white-space: nowrap;
            }}
            .response {{
                max-width: 400px;
                max-height: 100px;
                overflow-y: auto;
                font-size: 12px;
                color: #c9d1d9;
                background: #0d1117;
                padding: 8px;
                border-radius: 4px;
                word-break: break-word;
            }}
            .response::-webkit-scrollbar {{
                width: 6px;
            }}
            .response::-webkit-scrollbar-track {{
                background: #161b22;
            }}
            .response::-webkit-scrollbar-thumb {{
                background: #30363d;
                border-radius: 4px;
            }}
            .duration {{
                color: #7ee787;
                font-size: 13px;
                white-space: nowrap;
            }}
            .signature {{
                font-family: 'Courier New', monospace;
                font-size: 11px;
                color: #8b949e;
                max-width: 120px;
                word-break: break-all;
            }}
            
            .finney {{
                color: lawngreen;
            }}
            
            .test {{
                color: orange;
            }}
            
            /* Footer styles */
            .footer {{
                margin-top: 20px;
                padding: 15px;
                background: #161b22;
                border-top: 1px solid #30363d;
                border-radius: 6px;
                text-align: center;
                font-size: 14px;
                color: #8b949e;
            }}
            .footer a {{
                color: #58a6ff;
                text-decoration: none;
            }}
            .footer a:hover {{
                text-decoration: underline;
            }}
            .nav-links {{
                margin: 20px 0;  
                text-align: center;
                font-size: 14px;
                color: #8b949e;
            }}
            .nav-link {{
                color: #58a6ff;
                text-decoration: none;
            }}
            .nav-link:hover {{
                text-decoration: underline;
            }}
            
            /* Mobile responsive styles */
            @media (max-width: 768px) {{
                .container {{
                    padding: 10px;
                }}
                .header {{
                    padding: 15px;
                }}
                .header h1 {{
                    font-size: 20px;
                }}
                .stats {{
                    gap: 8px;
                }}
                .stat-item {{
                    font-size: 12px;
                    padding: 6px 10px;
                }}
                
                /* Hide table headers on mobile */
                thead {{
                    display: none;
                }}
                
                /* Make table rows display as cards */
                table, tbody {{
                    display: block;
                }}
                
                tr {{
                    display: block;
                    margin-bottom: 15px;
                    background: #161b22;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    padding: 12px;
                }}
                
                tr:hover {{
                    background: #1c2128;
                }}
                
                td {{
                    display: block;
                    padding: 8px 0;
                    border: none;
                    text-align: left;
                }}
                
                /* Add labels before content on mobile */
                td:before {{
                    content: attr(data-label);
                    font-weight: 600;
                    color: #8b949e;
                    display: block;
                    margin-bottom: 4px;
                    font-size: 11px;
                    text-transform: uppercase;
                }}
                
                .hotkey, .signature {{
                    max-width: 100%;
                    font-size: 14px;
                }}
                
                .response {{
                    max-width: 100%;
                    max-height: 150px;
                    font-size: 11px;
                }}
                
                .timestamp, .model, .duration {{
                    font-size: 12px;
                }}
                
                .footer {{
                    font-size: 12px;
                    padding: 10px;
                }}
                .nav-links {{
                    margin: 15px 0;
                }}
              
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>
                    <img src="https://www.bitrecs.ai/assets/logo/x7k9m2n8/whiteonblack.png" alt="BitRecs Logo">
                    Bitrecs Verified Inference
                </h1>
                <div class="stats">                   
                    <div class="stat-item">
                        <span class="stat-label">Network:</span>
                        <span class="{bt_network}">{escaped_bt_network}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Netuid:</span>
                        <span>{escaped_bt_netuid}</span>
                    </div>                  
                    <div class="stat-item">
                        <span class="stat-label">Verified Miners:</span>
                        <span>{escaped_len_miners}</span>
                    </div>
                </div>
            </div>
            <div>
              <p class="nav-links">
                    <a href="/log" class="nav-link">Log</a> | <a href="/stats" class="nav-link">Stats</a> | <a href="/providers" class="nav-link">Providers</a>
                </p>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Hotkey</th>
                            <th>Model</th>
                            <th>Provider</th>
                            <th>Response</th>
                            <th>Duration</th>
                            <th>Signature</th>
                        </tr>
                    </thead>
                    <tbody>
{rows_html}
                    </tbody>
                </table>
            </div>            
            <div>
              <p class="nav-links">
                    <a href="/log" class="nav-link">Log</a> | <a href="/stats" class="nav-link">Stats</a> | <a href="/providers" class="nav-link">Providers</a>
                </p>
            </div>
            <div class="footer">
                <p>
                    Rows: {escaped_len_verified}
                </p>
                <p> <a href="https://bitrecs.ai" target="_blank" rel="noopener noreferrer">Bitrecs</a>
                | <a href="https://dashboard.bitrecs.ai" target="_blank" rel="noopener noreferrer">Dashboard</a> | <a href="https://github.com/bitrecs/" target="_blank" rel="noopener noreferrer">Github</a>
                </p>
                <p>&copy; 2025 Bitrecs. All rights reserved.<p>
            </div>
        </div>
    </body>
    </html>
        """