import requests
import json
import datetime
import os


# --- 1. 核心配置区 ---
# 请将下方的字符串替换为你真实的 DeepSeek API Key
API_KEY = os.environ.get("DEEPSEEK_API_KEY")

API_URL = "https://api.deepseek.com/chat/completions"

# 自动获取今天的日期，例如 "06月01日"
today_str = datetime.datetime.now().strftime("%m月%d日")

# --- 2. 核心指令 (Prompt) 设定 ---
# 这就是我们的“铁律”，通过 JSON 示例锁死输出格式与内容边界
system_instruction = f"""
你是一个严谨的中国历史编辑。请搜索并提取12到15条发生在历史上的今天（{today_str}）的“中国伟大成就”。
严格遵守以下规则：
1. 标签分类：只能从【科技】、【民生】、【社会】中选择。
2. 真实性：事件必须绝对真实，不可捏造历史。
3. 详情开头：summary（摘要）字段的内容，**必须且只能**以具体的年月日开头，格式严格为“XXXX年XX月XX日，...”。
4. 输出格式：**必须且只能**输出纯 JSON 数组，不能有任何开头/结尾的问候语，绝对不要输出 ```json 这样的 Markdown 标记。

必须完全匹配以下 JSON 结构（注意我新增了 year 字段）：
[
  {{
    "title": "简短有力的大标题（例：神舟十四号发射成功）",
    "subtitle": "时间与地点（例：2022年 酒泉）",
    "year": 2022,
    "category": "科技",
    "summary": "2022年06月05日，神舟十四号载人飞船成功发射，将陈冬..."
  }}
]
"""

def fetch_today_history():
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"请给我{today_str}的中国伟大成就数据。"}
        ],
        "temperature": 0.1 # 极低的温度值，限制 AI 的发散思维，保证数据格式的严谨和稳定
    }

    print(f"⏳ 正在向 DeepSeek 请求 {today_str} 的历史成就数据...")
    
try:
        # 发送网络请求
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status() # 检查网络请求是否成功
        
        # 提取大模型返回的文本
        result_text = response.json()['choices'][0]['message']['content'].strip()
        
        # 将文本解析为 Python 的字典/列表对象
        data = json.loads(result_text)
        
        # 👇 新增的排序逻辑：按照 year 字段从小到大（最早到最新）排序
        # 如果某条数据意外缺失 year，默认放到最后(9999)
        data = sorted(data, key=lambda x: x.get('year', 9999))
        
        # 将结构化的数据保存到本地文件中
        with open("today_news.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        print("✅ 数据获取成功！已保存到当前目录的 today_news.json 文件中。")
        
    except json.JSONDecodeError:
        print("❌ 解析失败：DeepSeek 没有返回标准的 JSON 格式。")
        print(f"返回的原始内容如下:\n{result_text}")
    except Exception as e:
        print(f"❌ 运行出现错误: {e}")

if __name__ == "__main__":
    fetch_today_history()
