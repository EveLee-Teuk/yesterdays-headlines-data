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
system_instruction = f"""
你是一个严谨且擅长讲故事的中国历史编辑。请搜索并提取发生在历史上的今天（{today_str}）的“中国伟大成就”。
严格遵守以下规则（违背任何一条将导致严重错误）：
1. 标签分类：只能从【科技】、【民生】、【社会】中选择。
2. 绝对真实与日期锁定（最高优先级）：事件发生日期**必须严格是 {today_str}**！绝对不能把其他月份或日期的事件拿来凑数！如果历史上的今天没有那么多惊天动地的成就，就只输出真实的几条（8到12条均可），**宁缺毋滥，严禁伪造日期**。
3. 详情要求：summary（摘要）字段的内容必须丰富、详尽、有深度（字数控制在 200 到 300 字之间）。你需要生动地描述该事件的时代背景、面临的困难、核心突破的具体细节，以及深远影响。
4. 详情开头（格式锁死）：summary（摘要）字段的内容，**必须且只能以“XXXX年{today_str}，”开头**。请注意，月份和日期必须严格与 {today_str} 一致！
5. 输出格式：**必须且只能**输出纯 JSON 数组，不能有任何开头/结尾的问候语，绝对不要输出 ```json 这样的 Markdown 标记。

必须完全匹配以下 JSON 结构：
[
  {{
    "title": "简短有力的大标题（例：神舟十四号载人飞船发射成功）",
    "subtitle": "时间与地点（例：2022年 酒泉）",
    "year": 2022,
    "category": "科技",
    "summary": "2022年{today_str}，神舟十四号载人飞船在酒泉卫星发射中心成功点火升空。在当时复杂的空间站建造任务背景下......（此处需确保字数充实饱满）"
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
        
        # 将文本解析为 Python 的字典/列表对象，顺便验证 AI 是否按要求输出了规范的 JSON
        data = json.loads(result_text)
        
        # 将结构化的数据保存到本地文件中（自动按年份排序）
        data = sorted(data, key=lambda x: x.get('year', 9999))
        
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
