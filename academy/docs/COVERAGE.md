# 原大纲逐项映射

110项全部保留；映射是课程覆盖入口，不是熟练度认证。

## s1-1 编程语言与工程化

- Python 编程语言基础 → [eng-01](eng-01.md)
- 类型标注、异步编程、装饰器与上下文管理器 → [eng-01](eng-01.md)、[eng-08](eng-08.md)
- 包管理、虚拟环境、代码规范与静态检查 → [eng-01](eng-01.md)、[eng-02](eng-02.md)
- Git 分支模型与 PR 流程、Linux 命令行与日志检索 → [eng-02](eng-02.md)、[eng-05](eng-05.md)
- 基础 Web 与接口对接（页面搭建、接口调用、流式响应渲染） → [eng-03](eng-03.md)
- 单元测试、断点调试与日志排查 → [eng-02](eng-02.md)、[eng-11](eng-11.md)

## s1-2 数据结构与算法

- 数组、链表、栈与队列、哈希表 → [eng-07](eng-07.md)
- 二叉树、堆、图（遍历与最短路） → [eng-07](eng-07.md)
- 排序、二分、双指针、滑动窗口 → [eng-07](eng-07.md)
- 递归与动态规划入门 → [eng-07](eng-07.md)
- 时间与空间复杂度分析 → [eng-07](eng-07.md)

## s1-3 计算机网络

- HTTP / HTTPS 报文结构与状态码语义 → [eng-03](eng-03.md)、[eng-09](eng-09.md)
- TCP 三次握手与四次挥手 → [eng-09](eng-09.md)
- DNS 解析、TLS 握手 → [eng-09](eng-09.md)
- Cookie / Session / Token → [eng-09](eng-09.md)
- 反向代理与负载均衡 → [ops-07](ops-07.md)、[ops-08](ops-08.md)

## s1-4 操作系统

- 进程 / 线程 / 协程的区别与适用场景 → [eng-05](eng-05.md)、[eng-08](eng-08.md)
- 内存管理与虚拟内存 → [eng-05](eng-05.md)
- IO 模型（阻塞、非阻塞、多路复用） → [eng-05](eng-05.md)、[eng-08](eng-08.md)
- 文件系统与文件描述符 → [eng-05](eng-05.md)
- 上下文切换开销 → [eng-05](eng-05.md)、[eng-08](eng-08.md)

## s1-5 数据库与存储

- 关系模型、SQL、索引原理与执行计划 → [eng-04](eng-04.md)
- 事务与隔离级别、连接池 → [eng-04](eng-04.md)、[eng-10](eng-10.md)
- Redis 常用数据结构与缓存策略 → [eng-10](eng-10.md)
- 关系库与文档库的选型边界 → [eng-10](eng-10.md)

## s1-6 软件工程基础

- 分层架构（接口 / 业务 / 数据） → [eng-03](eng-03.md)
- REST 接口设计与 OpenAPI 文档 → [eng-03](eng-03.md)、[eng-06](eng-06.md)
- 参数校验、鉴权、异常处理 → [eng-06](eng-06.md)、[eng-09](eng-09.md)
- 配置管理与结构化日志 → [ops-02](ops-02.md)、[ops-04](ops-04.md)

## s2-1 大模型基础

- 大模型工作原理直觉（Transformer、注意力、Tokenizer） → [ai-01](ai-01.md)
- 上下文窗口、采样参数（温度、top-p） → [ai-01](ai-01.md)
- 幻觉成因与能力边界 → [ai-01](ai-01.md)、[ai-05](ai-05.md)
- 多模态能力范围 → [ai-03](ai-03.md)
- 模型选型、Token 计费与成本对照 → [ai-02](ai-02.md)、[ops-10](ops-10.md)

## s2-2 模型调用工程

- API / SDK 调用、鉴权、流式输出 → [ai-02](ai-02.md)
- 超时与重试、限流与降级 → [ai-02](ai-02.md)
- 多模型路由、Token 计费与成本核算 → [ai-02](ai-02.md)、[ops-10](ops-10.md)

## s2-3 提示与上下文工程

- 结构化 Prompt、角色与约束设计 → [ai-01](ai-01.md)
- Few-shot 示例设计、思维链 → [ai-01](ai-01.md)
- 上下文压缩与摘要、多轮状态管理 → [ai-08](ai-08.md)
- Prompt 版本管理 → [ai-01](ai-01.md)、[eng-02](eng-02.md)
- Harness 工程（Agent 运行外壳：上下文装配、工具注入、循环控制、失败恢复、可观测埋点） → [ai-06](ai-06.md)、[ai-08](ai-08.md)

## s2-4 RAG 全链路

- 多模态文档解析（文本、扫描件 OCR、图片与表格提取） → [ai-03](ai-03.md)
- 文档清洗与分块策略 → [ai-03](ai-03.md)
- Embedding 选型与相似度度量 → [ai-04](ai-04.md)
- 向量库（Milvus / pgvector / ES 等） → [ai-04](ai-04.md)、[ai-11](ai-11.md)
- 混合检索与重排模型 → [ai-04](ai-04.md)
- 引用溯源、多轮问题改写与增量入库 → [ai-03](ai-03.md)、[ai-05](ai-05.md)、[ai-11](ai-11.md)

## s2-5 RAG 与 Agent 评测

- RAG 评测指标（召回率、上下文相关性等） → [ai-05](ai-05.md)
- Agent 评测指标（任务成功率、工具调用正确率、时延与成本等） → [ai-05](ai-05.md)、[ai-06](ai-06.md)
- 评测集构建与常用评测工具使用 → [ai-05](ai-05.md)、[ai-11](ai-11.md)

## s2-6 Agent 工程

- ReAct、Plan-Execute、Reflection 等架构 → [ai-06](ai-06.md)、[ai-08](ai-08.md)
- 工具定义与参数 Schema、Function Calling、调用编排 → [ai-06](ai-06.md)、[ai-07](ai-07.md)
- 并行调用、失败重试、幂等设计 → [ai-08](ai-08.md)、[eng-08](eng-08.md)
- 记忆管理（短期 / 长期 / 向量记忆） → [ai-08](ai-08.md)
- 工作流编排与自主 Agent、多 Agent 的取舍与成本 → [ai-06](ai-06.md)、[ai-08](ai-08.md)
- 安全护栏（提示注入防护、越权工具调用拦截、参数幻觉纠正） → [ai-06](ai-06.md)、[ai-07](ai-07.md)

## s2-7 MCP、Skill 封装与系统集成

- MCP 协议规范与 Server 编写 → [ai-07](ai-07.md)
- 资源与工具的暴露方式、权限边界 → [ai-07](ai-07.md)
- Skill 的结构与编写（能力封装、触发条件、参数约定、依赖声明） → [ai-07](ai-07.md)、[ai-12](ai-12.md)
- 企业系统对接（CRM / ERP / OA 的接口集成、数据同步、鉴权方式） → [ai-07](ai-07.md)

## s2-8 AI 产品与工具链

- WorkBuddy：Skills / Connector 生态、场景搭建 → [ai-12](ai-12.md)
- CodeBuddy：IDE 集成、研发流程融入 → [ai-12](ai-12.md)
- 主流 AI Coding 工具（Codex / Claude Code 类） → [ai-12](ai-12.md)
- 编排框架与低代码平台（LangChain / LlamaIndex / Dify） → [ai-12](ai-12.md)、[ai-11](ai-11.md)、[ai-06](ai-06.md)

## s3-1 公有云产品体系

- 计算：云服务器、容器服务、Serverless → [ops-06](ops-06.md)、[ops-07](ops-07.md)
- 存储：对象存储、文件存储 → [ops-06](ops-06.md)、[ops-07](ops-07.md)
- 数据库：关系库、缓存、向量库托管服务 → [ops-07](ops-07.md)
- 网络：VPC、负载均衡、网关、DNS、证书 → [ops-07](ops-07.md)
- 安全与访问控制、计费模型与成本构成 → [ops-07](ops-07.md)、[ops-10](ops-10.md)

## s3-2 应用部署工程

- Docker 镜像构建与多阶段构建、镜像瘦身 → [ops-03](ops-03.md)
- Compose 编排、配置与密钥管理 → [ops-03](ops-03.md)
- K8s 核心对象（Deployment / Service / ConfigMap / Secret） → [ops-08](ops-08.md)
- CI/CD 流水线 → [ops-03](ops-03.md)、[eng-11](eng-11.md)
- 灰度发布与回滚 → [ops-08](ops-08.md)

## s3-3 私有化与专有云交付

- 公有云、私有化、专有云、混合部署的形态差异 → [ops-06](ops-06.md)
- 离线部署与内网无外网环境适配 → [ops-09](ops-09.md)
- 镜像与依赖的离线分发 → [ops-09](ops-09.md)
- 数据不出域约束、资源与 License 规划、数据合规要求 → [ops-09](ops-09.md)、[ops-10](ops-10.md)
- 客户机房交付流程与验收方式 → [ops-06](ops-06.md)、[ops-12](ops-12.md)
- 需求澄清与边界确认 → [ops-01](ops-01.md)
- 架构选型对比、部署拓扑设计 → [ops-01](ops-01.md)、[ops-07](ops-07.md)
- 高可用与容量规划 → [ops-10](ops-10.md)
- 成本测算与验收标准定义 → [ops-01](ops-01.md)、[ops-10](ops-10.md)
- 安全与合规设计（数据脱敏、内容过滤、权限边界） → [ops-07](ops-07.md)、[ops-09](ops-09.md)
- 方案文档与拓扑图撰写 → [ops-01](ops-01.md)
- 实施计划拆解与上线护航 → [ops-12](ops-12.md)
- 故障定位与排查方法 → [ops-04](ops-04.md)
- 效果与业务指标跟踪 → [ops-12](ops-12.md)、[ai-05](ai-05.md)
- 客户培训与知识转移 → [ops-12](ops-12.md)
- 交付资产沉淀（场景包、行业模板、操作手册、SOP） → [ops-12](ops-12.md)

## s4-1 算力与硬件基础

- GPU 显存构成（权重、KV Cache、激活值、框架开销） → [ops-05](ops-05.md)
- 算力与显存带宽指标 → [ops-05](ops-05.md)
- 常用卡型对比与选型 → [ops-05](ops-05.md)、[ops-11](ops-11.md)
- 多卡互联与并行方式（数据并行 / 张量并行 / 流水并行） → [ops-11](ops-11.md)

## s4-2 推理服务部署

- vLLM / TGI 等推理引擎的原理与使用 → [ops-05](ops-05.md)
- 模型加载与服务化 → [ops-05](ops-05.md)
- 连续批处理、KV Cache 与 PagedAttention → [ops-05](ops-05.md)、[ops-11](ops-11.md)
- 多实例部署与负载均衡、流式输出的服务端实现 → [ops-11](ops-11.md)、[ai-02](ai-02.md)

## s4-3 性能指标与调优

- TTFT（首 token 时延）、TPOT（单 token 生成时延） → [ops-05](ops-05.md)、[ops-11](ops-11.md)
- 吞吐与并发数之间的相互制约 → [ops-11](ops-11.md)
- 压测方法与工具 → [ops-11](ops-11.md)
- 瓶颈定位（显存 / 带宽 / 计算 / 调度 / 应用层） → [ops-04](ops-04.md)、[ops-11](ops-11.md)

## s4-4 成本与容量规划

- 自建推理与调用 API 的成本临界点测算 → [ops-10](ops-10.md)
- 实例选型与弹性伸缩 → [ops-08](ops-08.md)、[ops-10](ops-10.md)
- 资源利用率优化 → [ops-10](ops-10.md)、[ops-11](ops-11.md)
- SLA 与容量估算方法 → [ops-10](ops-10.md)

## s4-5 模型压缩与微调认知（了解级）

- 量化（INT8 / INT4 / FP8）的原理与收益 → [ai-10](ai-10.md)
- 精度损失的回归验证、什么情况下值得压缩 → [ai-10](ai-10.md)
- 微调（LoRA / QLoRA）流程与数据构造 → [ai-09](ai-09.md)、[ai-10](ai-10.md)
