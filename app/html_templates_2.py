import json
import html
import base64
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
            provider = item.get('provider', 'N/A')
            response_json = item.get('response_json', '{}')  # Full response dict as JSON string
            proof_json = item.get('proof', {})  # Now a dict from D1 select
            
            # Base64 encode the JSON strings (response_json is already string, proof_json is dict so dumps first)
            response_b64 = base64.b64encode(response_json.encode('utf-8')).decode('utf-8')
            proof_b64 = base64.b64encode(json.dumps(proof_json).encode('utf-8')).decode('utf-8')
            
            # Parse response_json to extract content
            response_content = 'N/A'
            miner_url = f"https://dashboard.bitrecs.ai/miner?uid={hotkey}"
            try:
                response_data = json.loads(response_json)
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
                            <td data-label="Timestamp" class="timestamp">{timestamp}</td>
                            <td data-label="Hotkey" class="hotkey"><a href="{miner_url}" target="_blank" rel="noopener noreferrer">{hotkey}</a></td>
                            <td data-label="Model" class="model">{model}</td>
                            <td data-label="Provider" class="model">{provider}</td>
                            <td data-label="Response" class="response">{response_content}</td>
                            <td data-label="Duration" class="duration">{duration}s</td>
                            <td data-label="Signature" class="signature">{signature}</td>
                            <td data-label="Verify" class="verify">
                                <button class="verify-btn" 
                                        data-response="{response_b64}" 
                                        data-proof="{proof_b64}" 
                                        data-signature="{html.escape(signature)}" 
                                        data-timestamp="{html.escape(timestamp)}" 
                                        data-ttl="{html.escape(str(item.get('ttl', 'N/A')))}">Verify</button>
                            </td>
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
                font-size: 12px;
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
            .verify {{
                text-align: center;
            }}
            .verify-btn {{
                background: #238636;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
            }}
            .verify-btn:hover {{
                background: #2ea043;
            }}
            .verify-btn:disabled {{
                background: #30363d;
                cursor: not-allowed;
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
                    font-size: 11px;
                }}
                
                .response {{
                    max-width: 100%;
                    max-height: 150px;
                    font-size: 11px;
                }}
                
                .timestamp, .model, .duration {{
                    font-size: 12px;
                }}
                
                .verify {{
                    text-align: left;
                }}
                .verify-btn {{
                    width: 100%;
                    padding: 10px;
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
                            <th>Provider</th>
                            <th>Response</th>
                            <th>Duration</th>
                            <th>Signature</th>
                            <th>Verify</th>
                        </tr>
                    </thead>
                    <tbody>
{rows_html}
                    </tbody>
                </table>
            </div>
        </div>
        
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const verifyButtons = document.querySelectorAll('.verify-btn');
                
                verifyButtons.forEach(button => {{
                    button.addEventListener('click', async function() {{
                        const btn = this;
                        btn.disabled = true;
                        btn.textContent = 'Verifying...';
                        
                        try {{
                            // Decode base64 and parse JSON for response and proof
                            const responseB64 = btn.getAttribute('data-response');
                            const proofB64 = btn.getAttribute('data-proof');
                            const response = JSON.parse(atob(responseB64));
                            const proof = JSON.parse(atob(proofB64));
                            const signature = btn.getAttribute('data-signature');
                            const timestamp = btn.getAttribute('data-timestamp');
                            const ttl = btn.getAttribute('data-ttl');
                            
                            const signedResponse = {{
                                response: response,
                                proof: proof,
                                signature: signature,
                                timestamp: timestamp,
                                ttl: ttl
                            }};
                            console.log('Sending signedResponse:', JSON.stringify(signedResponse, null, 2));
                            // POST to /verify endpoint
                            const verifyResponse = await fetch('/verify', {{
                                method: 'POST',
                                headers: {{
                                    'Content-Type': 'application/json'
                                }},
                                body: JSON.stringify(signedResponse)
                            }});
                            
                            const result = await verifyResponse.json();
                            console.log('Received result:', result);
                            if (result.valid) {{
                                alert(`Verification successful!\\nHotkey: ${{result.hotkey}}\\nModel: ${{result.model}}\\nProvider: ${{result.provider}}\\nUnique ID: ${{result.unique_id}}`);
                            }} else {{
                                alert(`Verification failed: ${{result.error || 'Unknown error'}}`);
                            }}
                        }} catch (error) {{
                            alert('Error during verification: ' + error.message);
                        }} finally {{
                            btn.disabled = false;
                            btn.textContent = 'Verify';
                        }}
                    }});
                }});
            }});
        </script>
    </body>
    </html>
        """