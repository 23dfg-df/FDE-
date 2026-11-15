# 开源项目与官方资料研究记录

核对日期：2026-11-16。记录用途、源码阅读入口和最小复现范围；研究不等于所有项目已部署。

## MIT Missing Semester：工程工具课程

[原始来源](https://github.com/missing-semester/missing-semester)

- 借鉴：补足Shell、Git、调试与环境使用；本教程独立撰写，不复制课程正文。
- 阅读入口：按课程网站的Shell、版本控制、调试主题阅读；仓库_2020与_2026是不同年份课程。
- 最小复现：在临时仓库完成一次分支修改、测试和差异审查，保留终端记录。
- 边界：课程网站源码采用Jekyll；学习课程不要求搭建它的网站。许可证为CC BY-NC-SA 4.0，不能当MIT源码许可。
- 许可：CC BY-NC-SA 4.0（README已核对）

## FastAPI Full Stack Template

[原始来源](https://github.com/fastapi/full-stack-fastapi-template)

- 借鉴：研究一个请求怎样经过前端、API、当前用户与数据库，而非复制整套业务。
- 阅读入口：先看backend/app/api/routes/items.py、backend/app/api/deps.py、backend/app/models.py，再定位frontend调用。
- 最小复现：在固定提交的个人副本中给item列表补一个边界测试并解释owner_id过滤。
- 边界：上游含React、SQLModel、PostgreSQL及部署配置；完整运行需另备依赖。本知识库未部署上游模板。
- 许可：MIT（仓库许可标识已核对）

## TheAlgorithms/Python

[原始来源](https://github.com/TheAlgorithms/Python)

- 借鉴：阅读小型算法的输入约定、边界示例和复杂度分析。
- 阅读入口：从searches/binary_search.py的doctest读起，再读函数的区间约定；无需一次学习全部目录。
- 最小复现：自己写保持顺序去重和二分边界查找，再用空输入、重复值与缺失目标验证。
- 边界：主分支会变化；示例文件可能使用较新Python语法，先核对pyproject.toml。本课程示例独立实现。
- 许可：MIT（仓库许可标识已核对）

## SQLModel：模型、会话与测试组织

[原始来源](https://github.com/fastapi/sqlmodel)

- 借鉴：从小型SQL示例建立会话生命周期与API模型分工的认识。
- 阅读入口：先读docs_src及tests对应示例，再对照Session with Dependency教程。
- 最小复现：在临时数据库观察提交与回滚，标出一次请求的会话创建与关闭位置。
- 边界：ORM不会替你决定业务事务边界；本地SQLite验证不能替代PostgreSQL并发验收。
- 许可：MIT（仓库许可标识已核对）

## Python 官方教程与异常章节

[原始来源](https://docs.python.org/3/tutorial/)

- 借鉴：查证语言行为，区分类型提示、可变对象、异常传播与资源管理。
- 阅读入口：函数、数据结构、错误和异常、虚拟环境四个章节。
- 最小复现：使用独立venv执行本知识库的标准库实验，并记录解释器版本。
- 边界：请切换到实际解释器对应文档版本。
- 许可：未单独核对；以官方页面为准

## Python asyncio：任务与取消

[原始来源](https://docs.python.org/3/library/asyncio-task.html)

- 借鉴：理解协作式等待、任务取消及finally清理。
- 阅读入口：Coroutines、Task cancellation、Running in threads，按实际版本核对可用接口。
- 最小复现：运行engineering_async.py，验证工人数上限和取消后的active归零。
- 边界：sleep是等待的教学替身，不表示真实网络或GPU性能。
- 许可：未单独核对；以官方页面为准

## Python sqlite3：事务与参数绑定

[原始来源](https://docs.python.org/3/library/sqlite3.html)

- 借鉴：查证参数绑定、连接与事务控制的不同职责。
- 阅读入口：Transaction control、Using the connection as a context manager及占位符章节。
- 最小复现：运行engineering_sql.py，比较失败批次前后的条数与索引计划。
- 边界：本实验显式BEGIN/commit/rollback，避免默认事务行为随Python版本变化。
- 许可：未单独核对；以官方页面为准

## PostgreSQL 事务隔离

[原始来源](https://www.postgresql.org/docs/current/transaction-iso.html)

- 借鉴：理解并发读写的快照与隔离语义。
- 阅读入口：Read Committed和Repeatable Read，再阅读Serializable失败重试说明。
- 最小复现：用两会话记录读取、修改、提交的时间线；真实PostgreSQL实验属于后续选做。
- 边界：当前文档是移动版本；本知识库未运行PostgreSQL双会话实验。
- 许可：未单独核对；以官方页面为准

## MDN：Fetch 请求与错误处理

[原始来源](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch)

- 借鉴：区分HTTP错误、网络错误、JSON解析错误与流式读取。
- 阅读入口：Checking response status、Setting headers、Reading the response body。
- 最小复现：在本地应用中构造404，验证页面显示HTTP失败而不是成功提示。
- 边界：浏览器同源策略与服务器响应都影响结果；no-cors不是绕过鉴权的方法。
- 许可：未单独核对；以官方页面为准

## SQLModel：请求内的Session依赖

[原始来源](https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/)

- 借鉴：对照阅读会话创建、yield与关闭的完整生命周期。
- 阅读入口：先看get_session与路由依赖，再看测试替换依赖。
- 最小复现：画出成功和异常两条请求路径，指出谁提交、谁关闭连接。
- 边界：依赖清理负责生命周期，不能据此推断所有写入已提交。
- 许可：未单独核对；以官方页面为准

## Redis 数据结构官方说明

[原始来源](https://redis.io/docs/latest/develop/data-types/)

- 借鉴：根据访问模式选择字符串、哈希、列表、集合和有序集合。
- 阅读入口：从基础类型的命令和时间复杂度阅读，避免把不同模块能力混为一谈。
- 最小复现：在纸上设计文档缓存键和失效时间线，再在获准的本地Redis实例验证。
- 边界：本课程缓存时序实验是教学模型，不证明真实分布式一致性；Redis许可随版本变化需另核对。
- 许可：未单独核对；以官方页面为准

## GitHub Actions 官方入门

[原始来源](https://docs.github.com/en/actions/get-started/quickstart)

- 借鉴：理解触发事件、作业、步骤与构建结果。
- 阅读入口：先看workflow语法与运行日志，再看依赖缓存和权限章节。
- 最小复现：为自己的小型仓库加入CPU测试，在故意错误和修复后分别观察失败与成功。
- 边界：GitHub托管runner不等于实验室GPU；本教程不会在CI加载模型。
- 许可：未单独核对；以官方页面为准

## MDN HTTP 概览

[原始来源](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview)

- 借鉴：建立请求、连接、代理和应用状态的分层认识。
- 阅读入口：阅读client、server、proxies及HTTP消息，再查实际协议版本。
- 最小复现：沿一次请求分别记录域名、协议、状态码和业务结果。
- 边界：常见HTTP/1.1或HTTP/2基于TCP；HTTP/3采用QUIC，不能一概而论。
- 许可：未单独核对；以官方页面为准

## Pro Git：记录变更

[原始来源](https://git-scm.com/book/en/v2/Git-Basics-Recording-Changes-to-the-Repository)

- 借鉴：核对工作区、暂存区和提交的差别。
- 阅读入口：重点看git status、git diff与git diff --staged。
- 最小复现：在临时仓库把两个独立变更分成两个提交。
- 边界：不要在重要仓库中练习未理解的破坏性历史改写。
- 许可：未单独核对；以官方页面为准

## Tencent / WeKnora

[原始来源](https://github.com/Tencent/WeKnora)

- 借鉴：参考文档接入、模型配置、检索与引用的完整产品边界。
- 阅读入口：先看README和v0.9.0的docs/LITE.md，再沿知识上传路由追踪索引任务。
- 最小复现：只导入一页Markdown，用一条有标准证据的问题核验来源。
- 边界：与已有Haystack功能重叠；本课程没有部署新实例，不承诺Lite免登录。
- 许可：未单独核对；复现前阅读仓库及模型各自许可证

## Tencent-Hunyuan / HunyuanOCR

[原始来源](https://github.com/Tencent-Hunyuan/HunyuanOCR)

- 借鉴：参考图像输入、文档任务以及模型环境与权重的分离。
- 阅读入口：先看README的Inference和docs/inference/inference.md，再检查实际模型提交。
- 最小复现：保留一张样本、原始输出、耗时、版本与人工差异记录。
- 边界：当前main环境要求已变化；不把最新README直接用于已有固定版本环境。模型和应用许可分开。
- 许可：未单独核对；复现前阅读仓库及模型各自许可证

## deepset-ai / haystack

[原始来源](https://github.com/deepset-ai/haystack)

- 借鉴：参考可拆解的检索、路由与生成组件。
- 阅读入口：从官方Get Started进入，重点看pipeline组件输入输出和测试。
- 最小复现：固定三条文档，打印检索候选，再接生成；每次只换一个组件。
- 边界：当前文档存在多个主版本，必须和安装的haystack-ai版本匹配。
- 许可：仓库页面标注Apache-2.0及其他许可文件，集成前保留相应声明

## Microsoft / AI Agents for Beginners

[原始来源](https://github.com/microsoft/ai-agents-for-beginners)

- 借鉴：参考工具、规划、记忆与评测的分课组织。
- 阅读入口：先读工具调用和Agent设计章节，再看各课code_samples的依赖说明。
- 最小复现：将只读任务查询做成一个受控工具，用三种输入验证。
- 边界：当前示例使用Microsoft框架与Foundry服务，部分运行需Azure账号；本课程CPU实验不调用该云服务。
- 许可：未单独核对；复现前阅读仓库及模型各自许可证

## Model Context Protocol / Python SDK

[原始来源](https://github.com/modelcontextprotocol/python-sdk)

- 借鉴：参考协议工具发现、输入约定与客户端/服务端分离。
- 阅读入口：先核对README、VERSIONING和migration guide，再看examples与docs_src。
- 最小复现：固定SDK版本，注册一个只读查询工具，比较schema和实际错误。
- 边界：检索时README已采用v2 MCPServer、Python3.11+；旧FastMCP教程不能直接视为相同接口。
- 许可：仓库页面标注MIT

## tRPC-Agent-Go

[原始来源](https://github.com/trpc-group/trpc-agent-go)

- 借鉴：参考Go服务中的图工作流、取消、状态和可观测性。
- 阅读入口：先读README的runner、tools、session主题，再查看对应examples。
- 最小复现：已有Python工具契约稳定后，用Go调用一个只读任务查询接口。
- 边界：需先补Go基础；复用模型端点仍消耗上游资源，框架不保证模型会正确调用工具。
- 许可：未单独核对；复现前阅读仓库及模型各自许可证

## Hugging Face / PEFT

[原始来源](https://github.com/huggingface/peft)

- 借鉴：参考少量可训练参数与适配器保存、加载的接口关系。
- 阅读入口：重点看LoRA配置、目标模块与PeftModel加载示例。
- 最小复现：在获准小模型上确认训练参数数目，并在新进程加载匹配基座的适配器。
- 边界：README显存表是特定环境结果，不能移植为本机预算；本课不运行LLM微调。
- 许可：未单独核对；复现前阅读仓库及模型各自许可证

## LlamaFactory

[原始来源](https://github.com/hiyouga/LlamaFactory)

- 借鉴：参考数据格式、模型模板和训练配置的分离。
- 阅读入口：先看Supported Models，再看examples与数据说明，记录提交号。
- 最小复现：先离线审核十条数据和模板，再计划少步数训练与重载验收。
- 边界：当前模型表有Hunyuan家族，不等于任意混元权重、模板和量化组合都已在本机验证。
- 许可：未单独核对；复现前阅读仓库及模型各自许可证

## Hugging Face：Tokenizers

[原始来源](https://huggingface.co/docs/course/chapter2/4)

- 借鉴：理解文本到词项ID的处理及预处理一致性。
- 阅读入口：阅读tokenization、special tokens及解码相关章节。
- 最小复现：用自己的已下载tokenizer比较三种输入，保存ID与长度。
- 边界：下载模型可能需要联网；正文中的预算示例仅用教学整数，不伪称真实token统计。
- 许可：未单独核对；复现前阅读仓库及模型各自许可证

## Haystack：Pipelines

[原始来源](https://docs.haystack.deepset.ai/docs/pipelines)

- 借鉴：理解组件连接与中间结果定位。
- 阅读入口：先核对页面版本，再看Creating、Debugging与Visualizing章节。
- 最小复现：为一次检索生成画出数据进入和离开的字段。
- 边界：当前在线文档可领先于现有项目版本，不直接复制未核对的类名。
- 许可：未单独核对；复现前阅读仓库及模型各自许可证

## MCP：Architecture overview

[原始来源](https://modelcontextprotocol.io/docs/learn/architecture)

- 借鉴：理解host、client、server和工具/资源边界。
- 阅读入口：从参与者与数据层读起，再看工具发现示例。
- 最小复现：把一个已有HTTP接口写成工具契约表，先不接模型。
- 边界：本课JSON为自定义业务契约示意，不是完整MCP报文或合规测试。
- 许可：未单独核对；复现前阅读仓库及模型各自许可证

## Python：urllib.request

[原始来源](https://docs.python.org/3/library/urllib.request.html)

- 借鉴：参考HTTP客户端输入、响应和异常的边界。
- 阅读入口：查看Request、urlopen及上下文管理示例，按本机Python版本阅读。
- 最小复现：本地假服务分别返回正常JSON、错误状态和超时。
- 边界：本课不替用户请求收费模型接口；真实重试要按提供方协议处理。
- 许可：未单独核对；复现前阅读仓库及模型各自许可证

## WeKnora v0.9.0：模型配置

[原始来源](https://github.com/Tencent/WeKnora/blob/v0.9.0/website-docs/03-features/06-models.md)

- 借鉴：核对生成与向量模型配置的区别。
- 阅读入口：按生成、embedding及兼容接口段落阅读。
- 最小复现：用一条聊天请求和一批向量请求分别验收。
- 边界：只读官方文档，未实际部署此版本。
- 许可：未单独核对；复现前阅读仓库及模型各自许可证

## WeKnora v0.9.0：评测

[原始来源](https://github.com/Tencent/WeKnora/blob/v0.9.0/website-docs/03-features/15-evaluation.md)

- 借鉴：核对评测入口、并发与结果保留的边界。
- 阅读入口：先看请求参数与结果管理，再决定共享机器并发。
- 最小复现：以五题运行有限评测并导出原始结果。
- 边界：部署前再次核对固定版本，不把默认并发直接用于高核数共享机器。
- 许可：未单独核对；复现前阅读仓库及模型各自许可证

## CodeBuddy：Skills官方文档

[原始来源](https://www.codebuddy.cn/docs/ide/Features/Skills)

- 借鉴：理解任务说明、脚本与参考资料的模块化封装。
- 阅读入口：阅读Skill结构及加载方式，核对本机产品版本。
- 最小复现：只为一个只读代码审阅任务写输入、步骤和验收约定。
- 边界：不保证不同产品的Skill格式、权限和Connector可直接互换。
- 许可：未单独核对；复现前阅读仓库及模型各自许可证

## WorkBuddy Enterprise：产品简介

[原始来源](https://cloud.tencent.com/document/product/1831/134342)

- 借鉴：将办公协作和代码研发工具放回需求与交付流程。
- 阅读入口：先确认产品形态，再看本机可用能力与组织授权。
- 最小复现：选择一个不含真实客户信息的整理任务，保留输入、草稿与审阅记录。
- 边界：不假定当前账号拥有全部产品权限；产品功能可能随版本变化。
- 许可：未单独核对；复现前阅读仓库及模型各自许可证

## langgenius / Dify

[原始来源](https://github.com/langgenius/dify)

- 借鉴：对比低代码工作流与可编程后端的交付边界。
- 阅读入口：从README和部署说明了解组件，再检查自定义扩展方式。
- 最小复现：用同一只读任务画流程并列出代码扩展位置。
- 边界：本课程不部署Dify；许可证含项目专属条件，不能默认当作纯Apache-2.0。
- 许可：未单独核对；复现前阅读仓库及模型各自许可证

## langchain-ai / langchain

[原始来源](https://github.com/langchain-ai/langchain)

- 借鉴：作为模型应用组件与集成的比较阅读。
- 阅读入口：先核对版本，再从一个最小示例追踪模型调用和状态。
- 最小复现：只替换一层接口，比较原始请求与输出是否一致。
- 边界：不要求同时学习所有框架；库升级可能改变接口。
- 许可：未单独核对；复现前阅读仓库及模型各自许可证

## run-llama / llama_index

[原始来源](https://github.com/run-llama/llama_index)

- 借鉴：作为数据接入与检索组件的比较阅读。
- 阅读入口：重点查看数据加载、索引和检索的最小示例。
- 最小复现：为同一份公开文本记录导入后节点与来源信息。
- 边界：示例可能需要模型API或额外服务；本课程仅安排有界复现。
- 许可：未单独核对；复现前阅读仓库及模型各自许可证

## Docker Getting Started

[原始来源](https://github.com/docker/getting-started)

- 借鉴：理解镜像、容器和持久化边界
- 阅读入口：先看README与Dockerfile，再对照docs；官方教程入口可能跳转新版。
- 最小复现：在获准的个人环境运行一个示例，验证容器和卷的生命周期。
- 边界：未安装Docker；旧仓库与新文档可能不同，执行时固定提交。
- 许可：Apache-2.0（仓库标识）

## Docker：构建与运行应用

[原始来源](https://docs.docker.com/get-started/tutorials/run-an-app/)

- 借鉴：官方运行与构建入口
- 阅读入口：Run a container、Build an image、Clean up。
- 最小复现：解释端口映射与容器内监听的区别。
- 边界：本轮未部署容器。
- 许可：未单独核对；复制代码前检查上游许可

## Docker：多阶段构建

[原始来源](https://docs.docker.com/build/building/multi-stage/)

- 借鉴：区分构建工具与最终产物
- 阅读入口：命名阶段与COPY --from。
- 最小复现：指出哪些构建文件无需进入运行镜像。
- 边界：镜像变小不等于性能或安全自动改善。
- 许可：未单独核对；复制代码前检查上游许可

## Kubernetes Examples

[原始来源](https://github.com/kubernetes/examples)

- 借鉴：通过一个实例学习声明式部署
- 阅读入口：先看README，选择web目录一个例子；_archived仅作历史参考。
- 最小复现：在测试集群观察一个应用的副本与访问入口。
- 边界：本轮未建集群；执行需核对当前API版本与配额。
- 许可：未单独核对；复制代码前检查上游许可

## Kubernetes：Deployment

[原始来源](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)

- 借鉴：理解副本、更新与回退
- 阅读入口：Creating、Updating、Rolling Back。
- 最小复现：推演新Pod未就绪时的更新过程。
- 边界：Pod模板回滚不恢复数据库。
- 许可：未单独核对；复制代码前检查上游许可

## Kubernetes：Secret

[原始来源](https://kubernetes.io/docs/concepts/configuration/secret/)

- 借鉴：配置与敏感值管理边界
- 阅读入口：使用方式与存储保护说明。
- 最小复现：用虚构值解释编码与加密的区别。
- 边界：不提供真实凭据；平台控制需按组织要求验证。
- 许可：未单独核对；复制代码前检查上游许可

## OpenTelemetry Demo

[原始来源](https://github.com/open-telemetry/opentelemetry-demo)

- 借鉴：学习一次请求的跨组件关联
- 阅读入口：README、src、docker-compose.yml及官方架构图。
- 最小复现：只追踪一条请求路径，定位最长子调用。
- 边界：完整示例包含多个服务，先看资源要求；本轮未启动。
- 许可：Apache-2.0（仓库标识）

## OpenTelemetry Demo Architecture

[原始来源](https://opentelemetry.io/docs/demo/architecture/)

- 借鉴：公开系统的调用链阅读
- 阅读入口：从入口顺着一条下游链阅读。
- 最小复现：画入口与两个下游的trace关联。
- 边界：不将演示系统性能外推到自己的项目。
- 许可：未单独核对；复制代码前检查上游许可

## Prometheus

[原始来源](https://github.com/prometheus/prometheus)

- 借鉴：理解指标采集与时间序列职责
- 阅读入口：README、documentation与配置示例。
- 最小复现：定义有限标签的请求计数与耗时。
- 边界：本课日志程序不是Prometheus实现，未部署监控系统。
- 许可：Apache-2.0（仓库标识）

## Prometheus：Instrumentation

[原始来源](https://prometheus.io/docs/practices/instrumentation/)

- 借鉴：指标、标签和监测口径
- 阅读入口：各类服务的监测建议及标签数量。
- 最小复现：比较状态码标签与每请求ID标签的数量。
- 边界：真实告警阈值需业务基线。
- 许可：未单独核对；复制代码前检查上游许可

## vLLM

[原始来源](https://github.com/vllm-project/vllm)

- 借鉴：推理服务、调度与模型支持边界
- 阅读入口：README和examples，再进入对应版本文档。
- 最小复现：固定小模型做有界请求对照。
- 边界：不升级已有环境，不自动占满设备。
- 许可：Apache-2.0（官方仓库许可）

## vLLM：Production Metrics

[原始来源](https://docs.vllm.ai/en/latest/usage/metrics/)

- 借鉴：区分排队、首token与端到端指标
- 阅读入口：对照实际版本/metrics及单位。
- 最小复现：保存客户端结果并对应一个服务指标。
- 边界：最新文档指标可能与旧服务不同；未新压测。
- 许可：未单独核对；复制代码前检查上游许可

## Google SRE Workbook：Implementing SLOs

[原始来源](https://sre.google/workbook/implementing-slos/)

- 借鉴：以用户行为定义可靠性目标
- 阅读入口：SLI定义、目标选择与迭代。
- 最小复现：为问答入口写分母、分子和窗口。
- 边界：学习目标不是客户承诺；不转载正文。
- 许可：未单独核对；复制代码前检查上游许可

## Google SRE：Postmortem Culture

[原始来源](https://sre.google/sre-book/postmortem-culture/)

- 借鉴：用故障复盘生成可验收改进项
- 阅读入口：事实、影响、原因与改进记录。
- 最小复现：写一份教学故障的时间线。
- 边界：演练必须标明，不冒充真实事故。
- 许可：未单独核对；复制代码前检查上游许可

## GitHub：Deployment Environments

[原始来源](https://docs.github.com/en/actions/concepts/workflows-and-actions/deployment-environments)

- 借鉴：测试与发布环境的区别
- 阅读入口：环境记录、分支及保护规则。
- 最小复现：解释CPU检查通过为何不代表GPU已发布。
- 边界：是否审核以仓库规则和授权为准。
- 许可：未单独核对；复制代码前检查上游许可

## OpenSSH：ssh手册

[原始来源](https://man.openbsd.org/ssh)

- 借鉴：核对本地转发和执行位置
- 阅读入口：阅读-L与-N。
- 最小复现：对自己的授权测试服务建立回环转发。
- 边界：账号地址用占位符，未新连服务器。
- 许可：未单独核对；复制代码前检查上游许可

## Python：SQLite Backup API

[原始来源](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup)

- 借鉴：用一致快照验证数据库恢复
- 阅读入口：Connection.backup、事务和连接管理。
- 最小复现：运行临时数据库备份实验。
- 边界：哈希不代替业务查询，SQLite方式不可泛化为所有数据库。
- 许可：未单独核对；复制代码前检查上游许可

## Kubernetes：kubectl rollout status

[原始来源](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_rollout/kubectl_rollout_status/)

- 借鉴：核对等待与API请求超时参数
- 阅读入口：查看--timeout及继承的--request-timeout说明。
- 最小复现：解释观察超时和Deployment回滚为什么不同。
- 边界：本轮只验Bash语法，不访问集群。
- 许可：文档许可未单独核对；仅作官方阅读入口

## Google Cloud：Cloud SQL概览

[原始来源](https://docs.cloud.google.com/sql/docs/introduction)

- 借鉴：用官方关系库服务说明区分托管范围
- 阅读入口：阅读What Cloud SQL provides并核对具体配置。
- 最小复现：为关系库写平台与应用团队责任表。
- 边界：产品仅作类别示例，未创建资源、未比较价格。
- 许可：文档许可未单独核对；仅作官方阅读入口

## Google Cloud：Memorystore for Redis概览

[原始来源](https://docs.cloud.google.com/memorystore/docs/redis/memorystore-for-redis-overview)

- 借鉴：以托管缓存理解节点维护与缓存策略边界
- 阅读入口：阅读服务概览及配置、持久化与访问选项。
- 最小复现：区分节点管理与TTL、失效等应用规则。
- 边界：不同产品版本能力不同，不保证默认配置满足业务要求。
- 许可：文档许可未单独核对；仅作官方阅读入口

## Google Cloud：Vector Search概览

[原始来源](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/vector-search/overview)

- 借鉴：以托管向量检索理解索引服务与RAG质量边界
- 阅读入口：阅读索引及查询能力，再对照数据导入与维度要求。
- 最小复现：列出向量模型、过滤和评测仍需应用负责的事项。
- 边界：官方原Vertex AI路径在本次读取时跳转至此，后续需重新核对；未部署。
- 许可：文档许可未单独核对；仅作官方阅读入口
