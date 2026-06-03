import requests
import json
import datetime
import os
from duckduckgo_search import DDGS  # 👈 新增的搜图神器

# --- 1. 核心配置区 ---
API_KEY = os.environ.get("DEEPSEEK_API_KEY")
API_URL = "https://api.deepseek.com/chat/completions"
today_str = datetime.datetime.now().strftime("%m月%d日")

# --- 2. 核心指令 (Prompt) 设定 ---
system_instruction = f"""
你是一个严谨且擅长讲故事的中国历史编辑。请搜索并提取发生在历史上的今天（{today_str}）的“中国伟大成就”。
严格遵守以下规则（违背任何一条将导致严重错误）：
1. 标签分类：只能从【科技】、【民生】、【社会】中选择。
2. 绝对真实与日期锁定：事件发生日期**必须严格是 {today_str}**！宁缺毋滥（3到10条均可），严禁拿其他月份事件凑数。
3. 详情要求：summary（摘要）必须详尽有深度（200-300字）。
4. 详情开头：summary必须以“XXXX年{today_str}，”开头。
5. 新增搜图词：请为每个事件提炼一个高度概括的图片搜索关键词（image_keyword），最好是具体的名词或历史原貌词汇，例如“神舟十四号 发射 现场”、“1969 北京地铁 老照片”。
6. 输出格式：必须输出纯 JSON 数组，严禁 Markdown 标记。

必须完全匹配以下 JSON 结构：
[
  {{
    "title": "简短有力的大标题",
    "subtitle": "时间与地点",
    "year": 2022,
    "category": "科技",
    "summary": "2022年{today_str}，...",
    "image_keyword": "神舟十四号 发射"
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
        "temperature": 0.1
    }

    print(f"⏳ 正在向 DeepSeek 请求 {today_str} 的历史成就数据...")
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        result_text = response.json()['choices'][0]['message']['content'].strip()
        data = json.loads(result_text)
        
        # 👇 核心黑科技：全自动图片搜索
        print("🔍 正在为新闻全网搜索真实历史配图...")
        with DDGS() as ddgs:
            for item in data:
                keyword = item.get('image_keyword', item['title'])
                try:
                    # 获取搜索结果的第1张图片
                    results = list(ddgs.images(keyword, max_results=1))
                    if results:
                        item['cover_image'] = results[0]['image']
                        print(f"🖼️ [{keyword}] 搜图成功！")
                    else:
                        item['cover_image'] = "" # 没搜到就留空
                except Exception as e:
                    print(f"⚠️ [{keyword}] 搜图失败，跳过: {e}")
                    item['cover_image'] = ""
        
        # 按年份排序
        data = sorted(data, key=lambda x: x.get('year', 9999))
        
        with open("today_news.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        print("✅ 数据及图片链接获取成功！已保存到 today_news.json。")
        
    except Exception as e:
        print(f"❌ 运行出现错误: {e}")

if __name__ == "__main__":
    fetch_today_history()
