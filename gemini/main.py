from textwrap import indent
import time
import json
import orjson
import uuid
import requests
from typing import List, Optional, Dict, Any, Union

from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict
from gemini_webapi import GeminiClient
from bc3 import get_secure_code

from config import getConfig
from logger import logger

# --- 配置区 ---
# 假设 get_secure_code 会自动从浏览器或配置文件获取最新的 Cookie
SECURE_1PSID, SECURE_1PSIDTS = get_secure_code([".google.com"])
client = GeminiClient(SECURE_1PSID, SECURE_1PSIDTS)

app = FastAPI(title="Gemini to OpenAI API")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"],
)

# --- Pydantic 模型 (OpenAI 规范，适配 Roo Cline) ---

class ChatMessage(BaseModel):
    role: str
    # content 可能是字符串，也可能是 Roo Cline 发送的复杂列表 (多模态)
    content: Union[str, List[Dict[str, Any]]]

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7
    
    # 核心：允许 Roo Cline 发送的所有额外参数 (如 tools, tool_choice 等)
    model_config = ConfigDict(extra='allow')

# --- 辅助函数 ---

def parse_messages_to_prompt(messages: List[ChatMessage]) -> str:
    """将 OpenAI 格式的 messages 转换为 Gemini 接受的单条 prompt"""
    prompt_parts = []
    for msg in messages:
        role = "User" if msg.role == "user" else "Assistant"
        
        # 处理 content 可能是列表的情况
        if isinstance(msg.content, list):
            text_content = ""
            for item in msg.content:
                if item.get("type") == "text":
                    text_content += item.get("text", "")
                elif item.get("type") == "image_url":
                    text_content += "[Image]"
            content_str = text_content
        else:
            content_str = msg.content
            
        prompt_parts.append(f"{role}: {content_str}")
    
    return "\n\n".join(prompt_parts)

def create_chat_chunk(content: str, model: str, finish_reason: Optional[str] = None):
    """构建 OpenAI 格式的流式 Chunk"""
    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"content": content} if content else {},
            "finish_reason": finish_reason
        }]
    }

# --- 鉴权 ---

security = HTTPBearer()
VALID_API_KEYS = {"sk-gemini-webapi-123"}

async def verify_api_key(auth: HTTPAuthorizationCredentials = Depends(security)):
    if auth.credentials not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth.credentials

# --- 错误处理 ---

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, enxc: RequestValidationError):
    # 如果仍然出现 422，这里会打印出详细的字段错误
    # print(f"DEBUG - 参数校验失败: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": enxc.errors(), "body": await request.body()},
    )

# --- 接口实现 ---

@app.get("/v1/models")
async def list_models(token: str = Depends(verify_api_key)):
    # 这里的 API Key 是 Google 公开的列表 Key 或你的私 Key
    url = "https://generativelanguage.googleapis.com/v1beta/models/?key={}".format(getConfig("google-aistudio-key"))
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        
        raw_data = orjson.loads(resp.text)
        openai_models = []
        for m in raw_data.get("models", []):
            model_id = m["name"].replace("models/", "")
            openai_models.append({
                "id": model_id,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "google"
            })
        return {"object": "list", "data": openai_models}
    except Exception as e:
        # 备选：如果请求失败，返回硬编码的基础列表
        return {
            "object": "list", 
            "data": [{"id": "gemini-3-pro", "object": "model", "created": int(time.time()), "owned_by": "google"}]
        }

@app.post("/v1/chat/completions")
async def chat_completions(request_data: ChatCompletionRequest, token: str = Depends(verify_api_key)):
    logger.info(f"DEBUG - 接收到请求数据:\n{json.dumps(request_data.model_dump(), indent=2)}")
    model_name = request_data.model
    prompt = parse_messages_to_prompt(request_data.messages)
    
    # 记录请求日志（可选）
    print(f"DEBUG - 收到请求模型: {model_name}, 流式: {request_data.stream}")

    # --- 1. 流式响应 ---
    if request_data.stream:
        async def stream_generator():
            try:
                async for chunk in client.generate_content_stream(prompt):
                    if chunk.text_delta:
                        data = create_chat_chunk(chunk.text_delta, model_name)
                        # ensure_ascii=False 确保中文不被转义
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                
                # 发送停止位
                stop_chunk = create_chat_chunk("", model_name, "stop")
                yield f"data: {json.dumps(stop_chunk, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                error_msg = {"error": {"message": str(e), "type": "gemini_error"}}
                yield f"data: {json.dumps(error_msg)}\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    # --- 2. 非流式响应 ---
    else:
        try:
            response = await client.generate_content(prompt)
            return {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model_name,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": response.text},
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(prompt) // 2, # 粗略估算
                    "completion_tokens": len(response.text) // 2,
                    "total_tokens": (len(prompt) + len(response.text)) // 2
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # 使用 reload=True 方便你改代码自动重启
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)