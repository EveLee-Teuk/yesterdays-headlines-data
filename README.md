# 昨日头条 · 七日独立存档

每天北京时间 00:15（GitHub 可能延迟）运行 archive_window.py。沿用 GitHub Secret DEEPSEEK_API_KEY，不向前端传递密钥。

真实网页检索与正文抓取 → DeepSeek 摘要 → 原文证据/日期校验 → 第二次模型复核 → 保存日报。
自动复核不能保证事实零错误，网页提供来源与证据供查阅。

## 文件职责

- archives/YYYY-MM-DD.json：独立日报，保留今天及前六天，共七个文件。已有 ready 历史日报保持不变，empty/unavailable 日允许有限重试；超过窗口的文件从当前分支删除，仍可从 Git 历史恢复。
- archive_index.json：七天日期索引，前端据此读取独立日报。可选 lastAttempt 仅包含今天最近尝试的 date、outcome、completedAt（北京时间 ISO 时间）；结果可为 ready/empty/failed/validation_failed/review_rejected，不包含来源或候选全文。
- issue.json、today_news.json：仅当日报告与旧格式兼容输出，不是历史存档。
- catalog.json：内部累积事件资料缓存，包含不同月日，前端不直接读取。它的 updatedAt 不是每条事件发生的日期。
- window_status.json：本次采集失败日期、尝试日期、历史重试次数和今天的尝试诊断。失败日保留旧文件；不存在旧文件时写 unavailable。编辑模型确实返回零候选可记 empty；生成候选全被原文/格式校验拒绝或全被复核拒绝则记本次失败，不能伪装为正常空日。
- collection_diagnostics/YYYY-MM-DD.json：每次尝试的诊断，包含搜索成功数/结果数、来源 URL、候选日期/标题/sourceId、校验原因、一次修正及复核计数。成功失败均保存，由 Actions artifact 提供，不进入前端日报。不保存密钥、请求头、完整网页或完整模型响应。

每日任务先更新今天，再按日期从近到远尝试最多两个非 ready 历史日。每个历史日期在七日窗口中最多重试两次，同一个北京时间日期内不重复重试同一历史日。预算耗尽或达到上限的空日仍如实保留 empty/unavailable，不能承诺七天一定都有事件。部分日期失败仍发布其他成功文件，并将 Action 标为失败供排查。每个文件只允许对应月日的事件，日期错配会拒绝发布。

历史回补不把 catalog/archive_index 的 lastRun 倒退到过去；该字段代表最近成功采集，今天失败则查 window_status.todayAttempt，不把旧成功状态当成本次成功。

## 检索、修正与成本边界

每个尝试日先做 5 条检索；取得少于 4 页合格正文时，补充 3 条科技/民生/工程行动词查询。每日期最多抓取 48 个白名单 HTTPS URL，最多向模型传入 8 页日期匹配正文，原有日期门槛和证书校验不变。检索和来源可用性仍依赖外部网站。

category 明确限定科技/民生/社会。格式或引用失败时，将原候选、校验错误及同一批来源反馈做一次修正，再执行原有严格校验和独立复核；不得用模糊引用、记忆或手工事件填补空日。合格候选不因另一条被拒就强制删除。

默认一次运行最多采集 3 个日期，每日期最多编辑、修正、复核 3 次逻辑模型调用；每调用保留最多 3 次网络/响应异常重试，因此一次运行最多 9 次逻辑调用、27 次 HTTP 尝试。通常无修正或无候选时更少，实际 token 和费用取决于来源长度及模型返回，不承诺固定金额。

这些是调用次数上限，不是耗时保证；外部服务过慢可能触发工作流 45 分钟上限。修正调用发生网络/响应失败时，本次整日采集保守失败并保留旧日报，即使同批另有尚未复核的新候选也不会发布半套结果。

手动 workflow_dispatch 的 backfill_budget 可选择 0–6，默认 2；这控制本轮历史日预算（今天始终尝试），不会绕过每日期两次历史重试上限或同日去重。一次性选择 5 可覆盖最多 5 个仍有重试额度的历史日；极端选择 6 时最多 7 日期、21 次逻辑模型调用、63 次 HTTP 尝试，仍受工作流 45 分钟上限限制。自动定时运行始终使用默认 2。

## 验证

Python 3.12+：pip install -r requirements.txt；python -m unittest discover -s tests -v。
python collect_history.py --retrieve-only 仅测试检索，不需要密钥。
python archive_window.py --days 7 执行七日流程（需要密钥）。
python archive_window.py --days 7 --backfill-budget 5 用有上限的扩大预算恢复空日（需要密钥）。
python archive_window.py --days 7 --finalize-only 仅校验、生成索引和执行滚动保留。
