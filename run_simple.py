#!/usr/bin/env python3
"""
Simple Server Runner - 最简单的运行方式
即使没有任何配置，也能运行基础功能
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="ChatGPT-on-WeChat", version="1.0.0")

class ChatMessage(BaseModel):
    content: str

@app.get("/")
def read_root():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ChatGPT-on-WeChat</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                line-height: 1.6;
            }
            .container {
                background: #f5f5f5;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                margin-bottom: 20px;
            }
            .input-group {
                margin-bottom: 20px;
            }
            input {
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
            }
            button {
                width: 100%;
                padding: 12px;
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
            }
            button:hover {
                background: #45a049;
            }
            .info {
                margin-top: 30px;
                padding: 20px;
                background: #e3f2fd;
                border-radius: 5px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 ChatGPT-on-WeChat API</h1>
            <p>A simple API service for WeChat integration</p>

            <form method="post" action="/chat">
                <div class="input-group">
                    <input type="text" name="content" placeholder="Type your message..." required>
                    <button type="submit">Send</button>
                </div>
            </form>

            <div class="info">
                <h3>📚 Quick Start Commands</h3>
                <p>Run these commands in your terminal:</p>
                <pre><code># Start this server
python3 run_simple.py

# Test with curl
curl -X POST http://localhost:8000/chat \\
  -H "Content-Type: application/json" \\
  -d '{"content": "Hello, ChatGPT!"}'
</code></pre>
            </div>

            <div class="info">
                <h3>🔗 API Endpoints</h3>
                <p>
                    <strong>POST /chat</strong> - Send a message<br>
                    <strong>GET /docs</strong> - API documentation
                </p>
            </div>
        </div>
    </body>
    </html>
    """)

@app.post("/chat")
async def chat(message: ChatMessage):
    """Handle chat messages"""
    response = {
        "reply": f"🤖 You said: {message.content}",
        "timestamp": "2024-01-01 12:00:00",
        "session_id": "simple-demo"
    }
    return JSONResponse(content=response)

@app.get("/docs")
def api_docs():
    """API documentation"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Documentation</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }
            pre { background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>📚 API Documentation</h1>
        <h2>Endpoints</h2>

        <h3>POST /chat</h3>
        <p>Send a message to the chat system.</p>
        <pre><code>curl -X POST http://localhost:8000/chat \\
  -H "Content-Type: application/json" \\
  -d '{"content": "Hello, ChatGPT!"}'
</code></pre>

        <h3>Response Format</h3>
        <pre><code>{
    "reply": "Response message",
    "timestamp": "2024-01-01 12:00:00",
    "session_id": "unique-session-id"
}</code></pre>
    </body>
    </html>
    """)

if __name__ == "__main__":
    print("🚀 Starting ChatGPT-on-WeChat Simple Server...")
    print("📍 Server: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("\n✨ Server is ready!")
    uvicorn.run(app, host="0.0.0.0", port=8000)