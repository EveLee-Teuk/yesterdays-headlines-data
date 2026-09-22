# 昨日头条 · 七日独立存档

每天北京时间 00:15（GitHub 可能延迟）运行 archive_window.py。沿用 GitHub Secret DEEPSEEK_API_KEY，不向前端传递密钥。

真实网页检索与正文抓取 → DeepSeek 摘要 → 原文证据/日期校验 → 第二次模型复核 → 保存日报。
自动复核不能保证事实零错误，网页提供来源与证据供查阅。

## 文件职责

- archives/YYYY-MM-DD.json：独立日报，保留今天及前六天，共七个文件。已有历史日报保持不变，今天更新不会覆盖它们；超过窗口的文件从当前分支删除，仍可从 Git 历史恢复。
- archive_index.json：七天日期索引，前端据此读取独立日报。
- issue.json、today_news.json：仅当日报告与旧格式兼容输出，不是历史存档。
- catalog.json：内部累积事件资料缓存，包含不同月日，前端不直接读取。它的 updatedAt 不是每条事件发生的日期。
- window_status.json：本次采集失败日期。失败日保留旧文件；不存在旧文件时写 unavailable，稍后自动重试。成功检索但无合格事件记 empty，不冒充采集故障。

每日任务补齐缺失或失败的历史日报，再更新今天，最终校验七个文件并发布。部分日期失败仍发布其他成功文件，并将 Action 标为失败供排查。每个文件只允许对应月日的事件，日期错配会拒绝发布。

## 验证

Python 3.12+：pip install -r requirements.txt；python -m unittest discover -s tests -v。
python collect_history.py --retrieve-only 仅测试检索，不需要密钥。
python archive_window.py --days 7 执行七日流程（需要密钥）。
python archive_window.py --days 7 --finalize-only 仅校验、生成索引和执行滚动保留。
