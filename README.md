# 昨日头条 · 每日历史资料

每天北京时间 00:15（GitHub 调度可能延迟）检索历史上的今天，抓取官方原文，再用 DeepSeek 整理和复核。沿用仓库 Secret `DEEPSEEK_API_KEY`，密钥不进入前端或提交记录。

## 发布流程

1. DDGS 检索政府、新华社、科学院等来源，抓取 HTTPS 正文。
2. DeepSeek 从正文选择最多 5 条新事件。每条必须附可在原文找到的短句及明确年月日。
3. 代码拒绝错月日、无来源、伪造引文、网页发布时间；第二次模型调用复核摘要与事件日期。
4. 合并进 catalog.json，保留已有人工校对事件；输出 issue.json、today_news.json、archives/ 和 collection_status.json。
5. 主分支 Action 自动提交；网页服务端自动读取 catalog.json，无需每天重新部署前端。

自动校验可降低日期错误，不能保证模型永不犯错。网页区分人工核对与 AI 整理，并提供原文与证据短句。没有合格资料时允许空页，不移动其他事件的日期。检索/API 失败则任务失败并保留已发布文件，不伪装成今日更新成功。

## 本地验证

Python 3.12+：`pip install -r requirements.txt`，然后 `python -m unittest discover -s tests -v`。
`python collect_history.py --retrieve-only` 仅测试真实检索，无需密钥。
`python collect_history.py` 需要环境变量 DEEPSEEK_API_KEY。
`python fetch_history.py --date 2026-09-22` 仅从已有库生成当日刊，不调用模型。

Actions 页面可手动运行 Collect and publish daily history。非 main 分支只生成构建附件，不提交发布；PR 不接触密钥。

## 相邻日期覆盖（2026-09-22）

每日任务依次采集昨天、明天、今天，允许前后翻页阅读对应月日的历史。每个日期均执行真实检索、DeepSeek 整理、原文证据校验与复核，今天最后执行以保持首页更新时间语义。新增内容长期保留在事件库，不会随明天更新被删除。任一步骤失败，本次任务不提交，已发布资料保持不变。
