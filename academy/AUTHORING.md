# FDE 完整学习知识库编写约定

本次交付是一个可独立验证的知识库版本；学习活动仍按每轮一个小任务执行。已有22模块110知识点为范围来源，覆盖不等于掌握。默认2026-11-16至12-31核心学习126小时，12-15前2小时/日、之后4小时/日；2027-01-01起12周进阶。写原创中文讲解，代码英文，不复制上游README；用已实际打开的官方仓库/文档支撑选型与接口约定。

## 内容文件约定

每个作者写 content/<track>.json，结构为 {"track": {"id":"engineering|ai|delivery","title":"...","description":"..."},"sources":[...],"lessons":[...]}。

source = {"id":"唯一前缀ID","title":"...","url":"https://...","kind":"repository|documentation|course","checked":"2026-11-16","license":"已核实的许可或未单独核对","use":"本课程借鉴什么","reading":"打开后先看哪些目录/章节","reproduction":"一个有限的复现任务","limits":"环境/版本/不包含什么"}。至少4个真正研究的官方GitHub项目/课程，附官方文档。不要用星数当推荐依据，不假称部署过。

lesson = {"id":"eng-01|ai-01|ops-01","title":"...","level":"core|advanced","hours":6,"prerequisites":[],"outline":["s1-1"],"summary":"...","outcomes":["..."],"sections":[{"title":"...","body":"原创中文段落，用\\n\\n分段"}],"example":{"title":"...","language":"python|bash|sql|json|text","code":"实际换行的示例","explanation":"输出和边界"},"exercise":{"task":"本课只做一个可验证任务","steps":["..."],"hints":["由浅入深的提示"],"solution":"默认折叠的参考解释，按用户主动展开提供","acceptance":["明确验收条件"],"deliverable":"需保存什么"},"pitfalls":[{"symptom":"...","cause":"...","check":"..."}],"quiz":[{"question":"...","options":["...","...","..."],"answer":0,"explanation":"..."}],"sources":["source-id"],"lab":"labs/xxx.py 或空字符串"}。

每篇至少4个相互衔接的讲解段，讲清原理、具体请求/数据例子、取舍、定位失败的方法；目标每篇约1000–1800中文正文字符，不用模板重复凑数。每篇2道有区分度的自测。每轨12篇，前6篇core各6小时，后6篇advanced各8小时。依赖只使用已知本轨ID，跨轨由根代理补充。所有示例注明运行环境，不对未经执行的代码声称已实测。

## 验证与隐私

每轨交付3个可离线运行的Python标准库教学实验及必要unittest（可用tempfile，不读实际业务库），放labs/<track>_*.py与tests/test_<track>_labs.py。README里给出命令和可观察证据；实验为教学模型，不伪装真实GPU/数据库服务指标。记录到evidence/<track>-checks.json：测试、示例执行情况、失败与未执行项目。只写自己负责的文件，不改根README、构建器、UI、PROGRESS或其他作者文件。

不要在公开内容包含私人服务器地址、用户名、凭据、真实业务数据或未经许可的截图。原有FDE与DocLens链接可使用公开GitHub地址；本次不启动任何服务器GPU任务。课程页面只展示脚本，实际执行由学习者在自己的环境完成。
