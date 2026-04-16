import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()

api_key = os.getenv("api_key")
invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
print(f"API Key: {api_key[:4]}...")  # 只顯示前4個字元以確認讀取成功
stream = True

# --- 1. 設定系統提示詞 ---
system_prompt = "你是一位專業的繁體中文 AI 助手，擅長分析問題並提供結構化的建議。請使用 Markdown 格式回答。"

# --- 2. 獲取使用者輸入 ---
user_input = input("請輸入您的問題：")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "text/event-stream" if stream else "application/json"
}

payload = {
    "model": "qwen/qwen3.5-397b-a17b",
    "messages": [
        {"role": "system", "content": system_prompt}, # 系統指令
        {"role": "user", "content": user_input}        # 使用者提問
    ],
    "max_tokens": 16384,
    "temperature": 0.7,
    "top_p": 0.95,
    "stream": stream,
    "chat_template_kwargs": {"enable_thinking": False},
}

try:
    response = requests.post(invoke_url, headers=headers, json=payload, stream=stream)
    
    # 檢查 API 是否成功回傳 (HTTP 狀態碼為 200)
    if response.status_code != 200:
        print(f"\n[HTTP 請求錯誤] 狀態碼: {response.status_code}")
        print(f"錯誤詳細訊息: {response.text}")
        exit()

    if stream:
        print("\n--- AI 回答中 ---\n")
        for line in response.iter_lines():
            if line:
                chunk = line.decode("utf-8")
                if chunk.startswith("data: "):
                    data_str = chunk[len("data: "):]
                    
                    # 處理流結束標記
                    if data_str.strip() == "[DONE]":
                        break
                        
                    try:
                        data_json = json.loads(data_str)
                        # 確保 content 存在以避免 KeyError
                        if "choices" in data_json and len(data_json["choices"]) > 0:
                            content = data_json["choices"][0]["delta"].get("content", "")
                            print(content, end="", flush=True)
                            
                    except json.JSONDecodeError as e:
                        print(f"\n[JSON 解析錯誤] 無法解析此行資料: {e}")
                        print(f"原始資料字串: {data_str}")
                    except KeyError as e:
                        print(f"\n[資料結構錯誤] 找不到預期的欄位: {e}")
                        print(f"解析後的資料: {data_json}")
                    except Exception as e:
                        print(f"\n[未知錯誤]: {e}")
                        
        print("\n\n--- 回答完畢 ---")
    else:
        print(response.json())

except requests.exceptions.RequestException as e:
    print(f"\n[網路請求錯誤] 連線失敗: {e}")