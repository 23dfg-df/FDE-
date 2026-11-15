# FDE 完整学习知识库：从基础到交付

这是基于学习者提供的24周FDE大纲、已有文档服务/知识库/DocLens项目，以及官方开源项目资料编写的中文学习知识库。课程按客户场景中的软件开发、AI应用、系统集成、部署与交付能力组织，不把任何公司岗位要求简化为一个通用证书标准。

**[打开在线知识库](https://23dfg-df.github.io/FDE-/academy/) · [阅读Markdown教程](docs/README.md) · [开源研究记录](docs/SOURCES.md) · [110项大纲对照](docs/COVERAGE.md)**

## 内容与使用方法

| 主线 | 内容 | 课程 |
|---|---|---:|
| 工程基础 | Python、Git、测试、HTTP、前端请求、三层架构、SQL、Linux、网络、并发、缓存、源码阅读 | 12 |
| AI 应用与系统集成 | 模型调用、提示、OCR、RAG、评测、Agent、MCP/Skills、企业接口、小模型训练、微调认知、AI研发工具 | 12 |
| 云与客户交付 | 需求澄清、验收、服务运维、Docker、CI/CD、观测排障、云网络、Kubernetes、离线部署、容量成本、培训复盘 | 12 |

共36课、72道自测、9个可运行CPU实验、4个阶段项目和12份交付模板。每课包含连续讲解、代码例子、一个独立练习、分层提示、折叠参考解释、失败排查与官方阅读入口。页面支持全文关键词搜索、课程筛选、可调日程、笔记和JSON备份。

开始时只选一课，先写预测，再运行练习，最后核对输出和解释。源码、样本、模板与课程由助手准备，不构成学习者已经掌握的证据。

## 年底核心与三个月进阶

默认计划以北京时间日历日期为准，包含首尾当天：

- 2026-11-16至12-14：29天，每天2小时，共58小时。
- 2026-12-15至12-31：17天，每天4小时，共68小时。
- 合计126小时：18节核心课程预算108小时，综合项目核验与补漏18小时。
- 2027年1月至3月：18节进阶课程144小时，加12周、每周8小时的项目实践96小时；剩余日期和时间用于复习、环境适配与演示。

课时包含阅读、练习、排障和记录，是学习预算，不是阅读计时或掌握保证。全部110项都有课程入口，但高阶算法、复杂Agent、Kubernetes、多卡并行等主要在进阶路线中深化。按当前时间不足时，页面明确显示缺口，不自动压缩课程或把未完成项记为完成。

## 离线使用与记录

完整发布包中的 `FDE完整学习知识库.html` 可以直接双击打开，无需账号、Python、Node或网络。课程、示例、自测和计划都包含在文件中；外部GitHub与官方资料链接仍需联网。

笔记与进度保存在**当前浏览器、当前地址**，不会自动上传或跨设备同步。离线文件移动、浏览器清理或无痕模式可能影响本地存储，请使用“导出记录”保存JSON，并在另一设备“笔记与备份”中导入。导入会校验格式并显示合并预览，只有主动确认后才写入；同一课程保留时间较新的记录。导入文件限制8 MiB。

本知识库使用独立的记录键 `fde-academy-progress-v1`，不会覆盖原学习工坊或旧项目的学习记录。旧格式备份应在原页面中使用，不能直接导入这里。

页面分别记录“已阅读”“亲自练习”“本课自验”。本课自验要求：阅读、练习、两类至少20字的证据，以及本课自测全对。系统不核实文字真实性，也不把两道题当作全面能力测量；独立复做、解释与新情境排障仍需人工核对。

## 运行CPU教学实验

建议Python 3.11+。实验仅使用标准库，不安装模型，不访问实验室服务器；HTTP实验只在本机随机回环端口监听并自动关闭。

在本目录执行：

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 labs/engineering_sql.py
python3 labs/engineering_async.py
python3 labs/engineering_http.py
python3 labs/ai_retrieval.py
python3 labs/ai_tools.py
python3 labs/ai_training.py
python3 labs/delivery_backup.py
python3 labs/delivery_logs.py
python3 labs/delivery_capacity.py
```

脚本的具体参数以 `--help` 或文件说明为准。实验输出来自教学数据、临时数据库或容量假设，不代表真实LLM、Redis/PostgreSQL、云平台或GPU成绩。实际模型和云部署实验在各课中单独标明前提与未执行边界。

## 从源码构建

构建器只使用Python标准库；Node.js 22用于可选的交互逻辑测试。

```bash
python3 build.py --output dist/index.html --docs docs
node --test tests/test_core.cjs
node --check web/app.js
```

双击 `dist/index.html` 即可。若浏览器限制本地存储，可在本目录执行以下命令，再打开终端所示的本机地址：

```bash
python3 -m http.server 18700 --bind 127.0.0.1 --directory dist
```

网页仅展示课程，不执行其中的Shell/Python命令，也不内置远程终端。学习者按每课说明在自己的获准环境执行。

## 文件结构

```text
content/engineering.json    工程基础课程与来源
content/ai.json             AI应用与系统集成课程与来源
content/delivery.json       云、运维与客户交付课程与来源
content/original-outline.json  原始22模块110知识点
content/projects.json       四个阶段项目书
web/                       无外部资源依赖的交互界面
labs/                      九个可运行CPU实验
tests/                     实验、内容、排期与备份行为测试
templates/                 十二份交付和学习记录模板
docs/                      从内容生成的完整Markdown教程
build.py                   离线单文件与教程生成器
package.py                 只打包公开白名单文件
evidence/                  本版实际检查记录
```

## 开源资料怎样使用

每个来源记录核对日期、借鉴内容、源码阅读入口、最小复现范围、环境边界与许可状态。课程正文是围绕当前学习任务编写的原创中文说明，不复制整个上游教程，也不把“看过仓库”写成“已部署并验收”。

上游主分支会变化，HunyuanOCR、vLLM、MCP等组件应按实际版本核对。现有实验使用的固定版本可以继续保留；阅读最新文档不意味着应直接升级正在运行的环境。

第三方代码、模型与教材分别适用原许可。公开仓库未替上游重新授权；本项目原创源码的许可证仍由仓库所有者决定，本次没有擅自添加MIT等许可证。

## 发布与检查边界

GitHub Pages托管静态课程，不运行Python后端或GPU模型。CPU CI会验证原项目及知识库实验、课程结构、原纲映射和离线构建；CPU通过不代替真实模型质量、云环境兼容、客户验收或学习者掌握。

本版未启动新GPU任务，也未替学习者完成WeKnora、Kubernetes、公有云、MCP真实外部系统或微调的新部署。每次实际复现应保存自己的实现与学习证据。
