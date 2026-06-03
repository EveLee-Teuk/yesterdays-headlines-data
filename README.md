🗞️ 昨日头条 (Yesterday's Headlines) - 数据引擎
这是一个基于 GitHub Actions 和大语言模型 (LLM) 驱动的全自动历史记录聚合器数据端。

📖 项目简介
“昨日头条”致力于挖掘并重现历史上的今天所发生的“中国伟大成就”。本项目是该独立 App 的纯数据驱动中心。

系统利用 Python 脚本配合 DeepSeek API，每天准时在云端唤醒，完成对历史事件的抓取、整理、排版和校验，并自动构建成标准化的 JSON 文件，为前端提供免运维、高稳定的 Serverless 数据流。

✨ 核心特性
🤖 全自动无人值守：基于 GitHub Actions 定时任务 (Cron Job)，每日避开整点拥堵自动触发，彻底解放双手。

🧠 AI 精准提炼：接入 DeepSeek API，通过严苛的 Prompt 工程锁死 AI 幻觉。严格聚焦【科技】、【民生】、【社会】三大领域，每日稳定输出 8-10 条高质量历史数据。

⏱️ 智能时间轴排序：内置 Python 逻辑，自动提取事件年份（year）并进行从早到晚的时间线排序，确保前端渲染的沉浸感。

📦 极简云端接口：舍弃传统后端数据库，直接利用 GitHub 仓库存储 today_news.json 作为 API 接口，实现真正的零服务器成本。

⚙️ 系统工作流 (Workflow)
定时触发：GitHub Actions 在预设时间自动启动 Ubuntu 运行环境。

数据抓取：执行 fetch_history.py，向大模型发起定制化请求。

数据清洗：Python 脚本对返回内容进行严格的 JSON 格式校验与时间序排列。

自动提交：通过 Git 命令将最新的数据文件自动推送 (Push) 并覆盖至 main 分支。

前端分发：客户端 App (Next.js/PWA) 实时拉取最新 JSON 完成渲染展示。

🗂️ 核心数据结构
输出的 today_news.json 严格遵循以下数据契约：
   ```bash
JSON
[
  {
    "title": "神舟十四号载人飞船发射成功",
    "subtitle": "2022年 酒泉",
    "year": 2022,
    "category": "科技",
    "summary": "2022年06月05日，神舟十四号载人飞船成功发射，开启中国空间站建造阶段首次载人飞行任务..."
  }
]
   ```
🛠️ 本地运行指南
如果您希望 Fork 本项目进行二次开发：

配置环境：确保本地已安装 Python 3.x。

安装依赖：

   ```bash pip install requests
   ```

3. **注入密钥**：在系统环境变量中配置您的 `DEEPSEEK_API_KEY`。
4. **手动抓取**：
   ```bash python fetch_history.py# yesterdays-headlines-data
   ```
