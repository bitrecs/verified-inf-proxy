import json
from typing import List, Dict, Any

class HTMLTemplates:
    @staticmethod
    def render_verified_display(verified: List[Dict[str, Any]], bt_network: str, bt_netuid: int) -> str:
        """Render the verified responses display page."""
        rows_html = ""
        for item in verified:
            timestamp = item.get('timestamp', 'N/A')
            hotkey = item.get('hotkey', 'N/A')
            model = item.get('model', 'N/A')
            duration = item.get('duration', 'N/A') or 'N/A'
            signature = item.get('signature', 'N/A')
            
            # Parse response_json to extract content
            response_content = 'N/A'
            try:
                response_data = json.loads(item.get('response_json', '{}'))
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

            rows_html += f"""
                        <tr>
                            <td class="timestamp">{timestamp}</td>
                            <td class="hotkey">{hotkey}</td>
                            <td class="model">{model}</td>
                            <td class="response">{response_content}</td>
                            <td class="duration">{duration}s</td>
                            <td class="signature">{signature}</td>
                        </tr>
            """

        return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verified Responses</title>
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
            }}
            .header {{
                background: #161b22;
                padding: 20px;
                border-bottom: 1px solid #30363d;
                margin-bottom: 20px;
            }}
            .header h1 {{
                font-size: 24px;
                color: #58a6ff;
                margin-bottom: 10px;
            }}
            .stats {{
                display: flex;
                gap: 20px;
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
                position: sticky;
                top: 0;
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
                font-size: 12px;
                color: #79c0ff;
                word-break: break-all;
            }}
            .model {{
                color: #a5d6ff;
                font-size: 13px;
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
                width: 8px;
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
                max-width: 200px;
                word-break: break-all;
            }}
            @media (max-width: 768px) {{
                .container {{
                    padding: 10px;
                }}
                th, td {{
                    padding: 8px;
                    font-size: 12px;
                }}
                .response {{
                    max-width: 200px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Verified Responses</h1>
                <div class="stats">
                    <div class="stat-item">
                        <span class="stat-label">Total:</span>
                        <span>{len(verified)}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Network:</span>
                        <span>{bt_network}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Netuid:</span>
                        <span>{bt_netuid}</span>
                    </div>
                </div>
            </div>
            
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Hotkey</th>
                            <th>Model</th>
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
        </div>
    </body>
    </html>
        """