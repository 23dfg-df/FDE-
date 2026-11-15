# RAG 链路与质量评测：从“答出来了”到“知道为什么这样答”

这一章围绕当前项目的一条 `/api/ask` 请求展开。目标是能沿着原文、检索片段、实际上下文、模型输出和引用记录逐步检查，指出错误发生在哪一层。

先完成 [服务器部署](服务器部署.md) 的一条真实请求。阅读和第 3 节切分练习可以离线完成；后面的检索实验需要应用服务，生成和五题评测还需要已启动的混元服务。GitHub Pages 不执行这些 API。

命令都在**服务器上的项目根目录**执行；仅第 3 节也可在自己的电脑运行。沿用已部署的 18300 应用与 18301 模型实例，不额外启动模型。每次只做一节，不把整章命令一次性粘进终端。

## 1. 先带着问题读一次请求

先写下你的预测，再向下阅读：

1. 如果问答引用了正确的文件名，答案就一定正确吗？
2. 检索出了五块资料，模型一定看到了这五块吗？
3. 模型回答“资料禁止这样操作”，`supported` 应该是 `true` 还是 `false`？
4. 修改 `corpus/` 后，已经运行的服务会自动使用新文本吗？

提示：把“文件相关”“具体原句支持”“实际进入提示”“生成回答正确”分开判断；分别查看 `retrieval.chunks`、`context_chunks`、`citations` 和 `raw_model_answer`。

```mermaid
flowchart LR
    A[原始 Markdown] --> B[按标题与字符窗口切分]
    B --> C[BM25 与文档向量索引]
    Q[用户问题] --> D[检索与可选重排]
    C --> D
    D --> E[按 tokenizer 预算组织上下文]
    E --> F[混元生成 JSON]
    F --> G[解析与引用编号检查]
    G --> H[SQLite 保存问答记录]
    G --> I[返回答案与证据]
```

| 阅读位置 | 这一层负责什么 | 调试时先看什么 |
|---|---|---|
| [main.py](../backend/main.py) 的 `AskQuery`、`ask` | 检查请求字段并交给业务层 | 字段名、范围、HTTP 状态 |
| [indexing.py](../backend/indexing.py) 的 `split_document`、`rebuild` | 从资料产生片段、向量及索引版本 | 原文、片段边界、缓存版本 |
| 同文件的 `_pipelines`、`retrieve` | 检索、融合、可选重排 | 排名、片段内容、各阶段耗时 |
| [services.py](../backend/services.py) 的 `_messages`、`ask` | 控制上下文并调用模型 | 真正传入的片段、token、模型身份 |
| 同文件的 `parse_answer`、`evaluate_rules` | 解析输出并计算有限的规则指标 | 原始标志、引用编号、人工待审项 |
| [repository.py](../backend/repository.py) 的 `Repository` | 保存与读取实验历史 | 记录 ID、类型、时间和完整 JSON |

第一次读源码只跟踪一个问题，暂时不逐行背代码。能说明每层输入与输出，就有了排障路线。

## 2. 这份实现具体做了什么

### 2.1 原始资料、运行资料与索引是三份不同的东西

`corpus/` 是随源码交付的种子资料。`Index.__init__` 第一次启动时将其中的 Markdown 复制到 `data/documents/`，并写入 `data/corpus-initialized.json`。以后启动不会无条件覆盖运行资料。

因此，修改仓库中的 `corpus/`，既不等于修改了已有的 `data/documents/`，也不等于重建了运行索引。先用 `GET /api/documents` 确认服务实际保存的文本，再用 `POST /api/reindex` 重建。新增文档接口返回的 `indexed: false` 正是在提醒这两步尚未合并。

`rebuild` 根据文档内容哈希、切分参数和向量模型身份计算索引版本；缓存还会检查内容和向量完整性。版本有助于定位“当时用了哪批资料”，但不会自动证明资料正确。向量模型身份中也含模型路径，所以换机器只改变路径也可能改变版本。生成模型与重排模型的身份不能仅靠这个索引版本表达，应另外记录配置。

本章先用已有资料做对照，不改变运行知识库。需要更新资料时使用新版本文件名；不要为了让某个答案正确，临时把参考答案塞进资料库。

### 2.2 420 与 60 是字符参数，不是 token 参数

当前切分器先遇到以 `#` 开头的行就划分标题段，再在每一段内使用最多 **420 个字符**的窗口，相邻完整窗口重叠 **60 个字符**，步长是 `420 - 60 = 360`。不同标题段之间不做这种重叠。

每块保存文件名、标题、块 ID、原文行号和文本。ID 包含块序号与内容哈希前缀；原文改变后，某些 ID 会变化，不能只凭旧 ID 寻找新资料。

这个实现是可解释的教学切分器，不是完整 Markdown 解析器：以 `#` 开头的代码行也可能被当成标题；很长的一行可能被从中间切开。重叠降低了边界丢失上下文的概率，也会带来重复内容，不能保证一句长事实始终完整地落在同一块中。

`420 字符`不能直接当成模型输入的 `420 tokens`。英文、汉字、路径和标点经 tokenizer 后的数量不同；向量编码器还采用最大 512 tokens 的截断设置。这些长度约束发生在不同阶段。

### 2.3 三种检索方式如何得到候选片段

| 模式 | 当前项目的做法 | 适合优先观察的问题 |
|---|---|---|
| `bm25` | 匹配词项；中文按单个汉字匹配，英文、数字及部分路径字符组成词项 | 型号、端口、明确错误信息有没有命中？ |
| `dense` | BGE 编码问题与片段，按余弦相似度取候选 | 换一种说法提问时还能找到对应片段吗？ |
| `hybrid` | 同时检索 BM25 与 dense，再按排名融合 | 两路检索有没有互补，或共同偏向错误资料？ |

向量模型使用首位置的隐藏向量并做归一化；问题侧会添加检索任务前缀，文档侧不会添加同一个前缀。BGE 向量模型与重排模型在当前实现中都运行于 CPU，生成模型才通过 HTTP 使用 vLLM。

BM25 分数与余弦分数不是同一种量，不能相加后就叫“置信度”。Haystack 的关键词检索与向量检索接口分别说明了两类输入和排序方式：[BM25 官方说明](https://docs.haystack.deepset.ai/docs/inmemorybm25retriever)、[向量检索官方说明](https://docs.haystack.deepset.ai/docs/inmemoryembeddingretriever)。

本项目明确配置 `DocumentJoiner(join_mode="reciprocal_rank_fusion")`，没有自定义两路权重。RRF 使用“排第几”来融合，重复出现在两路前排的片段会积累更多贡献。按 Haystack 3.5.0 的实际实现，若两路等权、排名从 1 开始，可写成：

$$
s(d)=\frac{61}{2}\sum_{j:\,d\in L_j}\frac{1}{60+r_j(d)}
$$

`L_j` 是第 j 路候选列表，`r_j(d)` 是片段在该列表中的名次；没进入某一路列表，就没有那一路贡献。前面的归一化常数不改变同一次融合的排序。这个分数仍然不是“答案正确的概率”。具体默认值和归一化见 [3.5.0 的 RRF 源码](https://github.com/deepset-ai/haystack/blob/v3.5.0/haystack/utils/misc.py)；连接方式见 [DocumentJoiner](https://docs.haystack.deepset.ai/docs/documentjoiner)。

### 2.4 打开重排，同时改变了候选范围

`rerank=false` 时每路请求 `top_k` 个候选。`rerank=true` 时先取 `max(top_k, 10)` 个候选，混合检索也先融合到这个数量，再让 BGE 重排器读取“问题—片段”对，最终返回前 `top_k` 块。

因此本项目的开关实验比较的是**扩大候选范围后再重排的整条策略**，不能将差异全部归因于重排器的排序能力。`rerank_score` 是模型的原始评分，不是经过概率校准的可靠度；重排后的 `score` 采用这个评分，原检索分数保存在 `retrieval_score`。

重排可能把相关片段升到前面，也可能使带有否定、日期或版本限制的必要片段掉出前列。要比较实际证据覆盖和耗时，不能只看排序看起来更整齐。

### 2.5 检索到的资料还要通过上下文预算

`Service._messages` 使用与混元服务匹配的 tokenizer 和聊天模板，关闭思考模式，计算**系统提示、资料、问题及模板标记合起来**的 token 数。当前输入预算是 1450 tokens，生成上限是 384，服务总上下文上限是 2048。

超出输入预算时，代码先删除排名靠后的整块资料；只剩一块且仍过长时，将其文本长度减半并重新计数；仍无法容纳则返回错误。它不会把全部检索结果无条件发送给模型。

于是要分开读三个数组：`retrieval.chunks` 是检索输出，`context_chunks` 是预算处理后真正使用的文本，`citations` 是解析后接受的引用。被截短的文本仍沿用原块 ID 与原始行号范围，核对时以实际 `text` 为准，不能仅看行号就认为整段已进入模型。

## 3. 练习一：不用模型，亲眼看到切分边界

**任务与预测：** 比较长段落切分后的块数、重叠和行号。先预测把 420 改成 240 后，块数与重复文字会怎样变化。

**提示：** 这只是直接调用纯文本函数，不创建 `Index`，不会加载 BGE、下载权重或启动 GPU。以下内容是临时构造的教学文本，不会写入真实知识库。

```bash
python3 - <<'PY'
from backend.indexing import split_document

text = '# 教学例子\n' + ('每次操作前先检查当前资源。' * 55) + '\n## 退出\n等待进程结束。\n'
for size in (420, 240):
    chunks = split_document('teaching.md', text, max_chars=size, overlap=60)
    print('\nwindow_chars=', size, 'chunks=', len(chunks))
    for chunk in chunks:
        print(chunk['id'], chunk['title'], len(chunk['text']),
              chunk['start_line'], chunk['end_line'])
    print('first_overlap_matches=', chunks[0]['text'][-60:] == chunks[1]['text'][:60])
    assert all(len(chunk['text']) <= size for chunk in chunks)
PY
```

**验收：** 能找到窗口长度变化后的块数变化，并解释为什么不同的块可能具有相同的原文行号。截图之外，还保留你对“字符窗口”和“原文行”的一句区分。

<details>
<summary>完成预测后再看解释</summary>

长文本重复在一行内，同一行可以被切成多块，所以行号相同不代表片段重复错误。相邻窗口有意保留 60 个字符的重叠。更小的窗口让证据更集中，也可能把条件和结论拆散；是否更好，需要之后按具体问题检查。

</details>

## 4. 练习二：先比较检索，再让模型回答

**任务与预测：** 固定一个问题，比较 BM25、dense、hybrid，再对照 hybrid 开启重排。预先写出你认为应该出现的原文事实，不填写期待的模型措辞。

**提示：** 只调用 `/api/retrieve` 不执行生成。已运行的应用会使用 CPU 检索模型；模型实例本身是否常驻显存是另一件事。

在同一个终端准备独立记录目录，后文命令沿用 `RAG_RUN`：

```bash
mkdir -p evidence
RAG_RUN=$(mktemp -d evidence/rag-study.XXXXXX)
export RAG_RUN
printf '%s\n' "$RAG_RUN"
curl -fsS http://127.0.0.1:18300/api/status -o "$RAG_RUN/status-before.json"
```

下面固定执行四次检索，保存完整 JSON，并打印前五块。每次请求顺序执行，不做并发压测：

```bash
python3 - <<'PY'
import json, os
from pathlib import Path
from urllib.request import Request, urlopen

output = Path(os.environ['RAG_RUN'])
question = '知识库片段为什么要保留来源位置？'
for mode, rerank in [('bm25', False), ('dense', False), ('hybrid', False), ('hybrid', True)]:
    payload = {'question': question, 'mode': mode, 'top_k': 5, 'rerank': rerank}
    request = Request('http://127.0.0.1:18300/api/retrieve',
        data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=120) as response:
        result = json.load(response)
    name = f'{mode}-rerank-{str(rerank).lower()}.json'
    (output / name).write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print('\n', name, result['index_version'], result['timings'])
    for rank, chunk in enumerate(result['chunks'], 1):
        print(rank, chunk['source'], chunk['id'], chunk['score'])
        print(chunk['text'])
PY
```

若某次请求报错，先记录完整报错并检查已有文件，不能把缺失项填成耗时 0 或“没有相关资料”。这段脚本遇到错误会停止，不会偷偷重试成成功。

| 配置 | 必要事实是否完整出现 | 最高排名 | 返回块数 | 总检索耗时 | 主要错误或缺失 |
|---|---|---|---|---|---|
| BM25 | 待人工核对 | 待填 | 待填 | 待填 | 待填 |
| dense | 待人工核对 | 待填 | 待填 | 待填 | 待填 |
| hybrid，无重排 | 待人工核对 | 待填 | 待填 | 待填 | 待填 |
| hybrid，扩大候选后重排 | 待人工核对 | 待填 | 待填 | 待填 | 待填 |

**验收：** 四次记录的 `index_version` 相同，能逐字指出支持问题的文本，并解释一个检索差异。只有一个问题、一次耗时，不能据此宣布某算法在整个知识库上最好；下一步应在开发集多题复查。

<details>
<summary>完成后查看计时与排序提示</summary>

`embedding_seconds` 对 dense/hybrid 包含问题向量编码；BM25 也可能有极小的准备耗时，不要求严格为零。`retrieval_seconds` 是管线执行，`rerank_seconds` 是可选重排阶段。它们都不是 GPU 生成时间。计时在取得索引锁后开始，等待锁的时间不包含在这些检索指标里。

</details>

## 5. 练习三：读懂一条完整问答，而不只看 answer

**任务与预测：** 沿用上一节的问题，预测哪些片段会进入提示、模型应引用哪块。然后只执行一次问答，检查三个片段数组是否相同。

```bash
curl -fsS --max-time 180 http://127.0.0.1:18300/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"知识库片段为什么要保留来源位置？","mode":"hybrid","top_k":5,"rerank":false,"structured":true}' \
  -o "$RAG_RUN/ask.json"
python3 -m json.tool "$RAG_RUN/ask.json"
```

输入范围以 `AskQuery` 为准：问题长度 1–600，`top_k` 为 1–8，模式为三选一。`structured=true` 请求 JSON Schema 约束，还在系统提示中增加 supported 的定义，说明“资料支持的否定结论也属于有依据”；`false` 仍在基础提示里要求 JSON，但不增加这段定义，也不发送 Schema。因此这个开关同时改变生成约束与提示内容，不能作为仅改变Schema的严格对照。本接口的生成上限在业务代码固定为 384，不能通过随意添加 `max_tokens` 字段来控制。

| 响应字段 | 该怎样理解 | 不代表什么 |
|---|---|---|
| `id`、`created_at`、`kind` | 这次持久化记录的身份；问答类型为 ask | 不是模型训练样本编号 |
| `answer` | 服务解析后的展示文字 | 不是人工验收结论 |
| `raw_model_answer` | 模型实际返回的原始文字 | 不能省略它来隐藏错误格式 |
| `model_supported` / `raw_support` | 正常解析路径中保留的模型原始判断 | 模型说有依据仍可能错 |
| `supported` | 经引用编号和有限冲突规则处理后的结果 | 不保证每句话被证据支持 |
| `retrieval.chunks` / `context_chunks` | 找到的候选 / 实际放进提示的文本 | 两者不保证数量相同 |
| `citations`、`invalid_citations` | 接受的引用、模型编出的未知编号 | 合法编号不等于语义正确 |
| `generation.model`、`generation.input_tokens`、`generation.output_tokens` | 实际返回的模型身份及用量信息 | 不能用字符数替代 token 数 |
| `generation.finish_reason` | 模型服务报告的停止原因 | 输出截断后仍要检查 JSON 是否完整 |
| `generation.elapsed_seconds` | 从提交上游模型请求到响应解析完成 | 不是纯 GPU 运算时长或首 token 延迟 |
| 顶层 `elapsed_seconds` | 本次问答编排耗时，包含检索和生成 | 计时结束在历史记录写入前，不包含完整客户端网络往返 |
| `index_version`、`human_verified` | 该次索引版本、是否有人工核验标记 | 本实现不会自动替你完成人工核验 |

正常解析时，`supported=true` 至少要求：模型原始值真的是布尔值 `true`、有可接受引用、没有未知引用编号，也没有命中特定明确拒答前缀冲突。`sources` 是本次上下文的 `S1`、`S2` 等标签，不是全库永久片段 ID。

当前拒答冲突规则只识别以“无法回答”或“资料不足”起始并满足指定边界的情况，不是通用语义分类器。模型可能先说“根据资料”再编造事实，此时规则未必能发现。

非法 JSON（包括原始响应为空字符串）会保留原文并给出 `parse_warning`；合法 JSON 中的 `answer` 为空字符串或特定占位符时才触发 `response_fallback`，展示提示由服务补充。早期失败分支未必具有 `model_supported` 等字段，因此读取记录要用“字段不存在/未知”，不能擅自补成模型拒答。结构化输出约束也不能保证事实正确。

问答成功后进入 `data/history.sqlite3`；上游请求失败会保存 `ask_error`。`GET /api/history` 返回最近记录，默认最多 500 条；不是永久完整历史的分页接口。保存了 JSON 和失败记录，才方便之后解释一次“看起来答对”的请求。

**验收：** 指出答案中的每项事实对应哪一块实际上下文；对没有对应关系的句子标“待核对”。回答否定结论但资料明确支持时，仍可属于有依据的回答。

## 6. 练习四：从五道开发题开始评测

**任务与预测：** 先运行结构审计，再启动最多五题的开发集任务，读懂完成数、失败数和待人工审阅数。这是流程练习，不是全量模型成绩。

```bash
python3 evaluation/validate_dataset.py --output "$RAG_RUN/dataset-validation.json"
python3 -m unittest discover -s evaluation -p 'test_validate_dataset.py' -v
curl -fsS --max-time 15 http://127.0.0.1:18300/api/evaluation/start \
  -H 'Content-Type: application/json' \
  -d '{"split":"dev","limit":5,"mode":"hybrid","rerank":false}' \
  -o "$RAG_RUN/evaluation-start.json"
```

启动响应是 HTTP 202 和任务 ID，表示任务已创建，不是五题全部答对。当前实现按题库顺序取前五道 dev 题，不随机抽样，也不保证这五题覆盖全部题型；每题固定 `top_k=5`，任务串行发请求。

下面最多轮询 30 次。若仍在运行，会请求取消后续题目；当前题需完成或报错后才停止，不会强行中断其他进程：

```bash
python3 - <<'PY'
import json, os, time
from pathlib import Path
from urllib.request import Request, urlopen

output = Path(os.environ['RAG_RUN'])
job_id = json.loads((output / 'evaluation-start.json').read_text())['id']
url = 'http://127.0.0.1:18300/api/evaluation/jobs/' + job_id
for attempt in range(30):
    with urlopen(url, timeout=10) as response:
        job = json.load(response)
    (output / 'evaluation-latest.json').write_text(json.dumps(job, ensure_ascii=False, indent=2))
    print(job['status'], job['completed'], '/', job['total'], flush=True)
    if job['status'] != 'running':
        print(json.dumps(job.get('summary', {}), ensure_ascii=False, indent=2))
        break
    time.sleep(2)
else:
    with urlopen(Request(url + '/cancel', data=b'', method='POST'), timeout=10) as response:
        print(response.read().decode())
    print('已请求取消；本脚本结束不等于当前题已停止，请稍后再次查询任务。')
PY
```

如果轮询已经结束而任务仍在运行，可在保留 `RAG_RUN` 的同一个服务器终端执行下面两步。若要提前取消，可先用 Ctrl+C 退出轮询脚本，再执行取消请求；退出轮询本身不会停止后台评测：

```bash
RAG_JOB_ID=$(python3 -c 'import json,os; from pathlib import Path; print(json.loads((Path(os.environ["RAG_RUN"])/"evaluation-start.json").read_text())["id"])')
curl -fsS --max-time 15 -X POST "http://127.0.0.1:18300/api/evaluation/jobs/$RAG_JOB_ID/cancel"
curl -fsS --max-time 15 "http://127.0.0.1:18300/api/evaluation/jobs/$RAG_JOB_ID" \
  -o "$RAG_RUN/evaluation-latest.json"
python3 -m json.tool "$RAG_RUN/evaluation-latest.json"
```

`cancelled` 表示按取消请求停止了后续题目；`failed` 是任务级失败；服务重启后的未完成历史可能显示 `interrupted`。**`completed` 只表示题目循环执行完，不保证每题请求成功**，还要读 `requests_failed` 与每项 `error`。取消接口返回 `cancelling` 只是受理取消，不是最终停止状态。

评测期间 API 会阻止新增资料或重建索引，任务也核对模型配置与索引版本。不要绕过 API 手工改运行目录。网络中断后，先查同一任务 ID，避免重复启动；轮询脚本报错也不等于服务器任务自动取消。

## 7. 指标的分母，比漂亮的百分比更重要

题库当前共 50 题：30 道 dev、20 道 test；普通题 26、多文档题 10、无答案题 10、版本冲突题 4。开发集用来调参数；测试集看过以后若继续据此改方案，它就已参与开发。两组共享同一个语料库，不代表跨领域泛化。

| 检查项 | 它实际计算什么 | 需要保留的限制 |
|---|---|---|
| `retrieved_all_expected_sources` | 期望来源文件集合是否全部在检索结果中 | 命中同文件的无关段落也可能通过；无期望来源时为 null |
| `*_evidence_covered` | 有多少期望引文在对应阶段的某一块中逐字完整出现 | 长引文跨两块或预算截断时可能不命中；也不是语义裁判 |
| `citation_ids_valid` | 引用编号检查没有未知项且无解析警告 | 合法引用仍可能支持不了回答 |
| `answerability_matches` | 最终 supported 是否与题库 answerable 相同 | 不核对答案中的具体数值、条件和步骤 |
| `model_answerability_matches` | 模型原始布尔判断与题库是否相同 | 无有效原始布尔值时为 null，要单列适用分母 |
| `semantic_accuracy` | 当前汇总保持 null | 必须经过明确的人工审阅流程才能另算语义成绩 |

`retrieval_all_sources_hits / retrieval_applicable_questions` 的分母是有有效评测检查、且来源指标适用的问题。它不包含无答案题，也不会把请求失败包装成“检索没有命中”。报告时同时写请求总数、完成数、成功数、失败数和该指标的适用数。

**教学算例，非项目实测：** 某次五题中有一题请求失败，另外四题有三题的最终依据标志与参考一致。可以写“成功响应 4/5，成功响应中依据标志匹配 3/4”；不能写“回答准确率 75%”。后者还缺少逐句的人工事实判断，也隐藏了一题请求失败。

17 份当前语料包含历史 Qwen 基线说明与现行 Hunyuan 部署说明。先识别问题是在问“当前状态”还是“历史快照”，再检查日期与来源。`case-policy-v1/v2` 是虚构教学规则，不是实验室真实制度。历史 16 份语料冻结版本的评测成绩，不能直接归到当前 17 份语料；公开包也不附带那批原始问答报告。

人工核对至少回答五个问题：请求完成了吗；必要证据找到了吗；答案的事实与条件正确吗；每条引用支持对应断言吗；资料不足时是否明确拒答且没有补造事实。建议将每题记录成下面的结构，`null` 保持“尚未判断”：

```json
{
  "question_id": "待填真实题号",
  "record_id": "待填真实问答记录ID",
  "index_version": "待填真实索引版本",
  "reviewer": "待填实际审阅者",
  "request_succeeded": null,
  "evidence_found": null,
  "answer_correct": null,
  "citations_supported": null,
  "abstention_correct": null,
  "not_applicable": {},
  "notes": "逐句写出支持依据；不能确认的地方保持待审。"
}
```

这个模板只是记录格式，不向 API 提交，也不是已完成的评测证据。把参考答案、评分表或审阅结果导入检索库，会让系统在评测时检索到“标准答案”，破坏原来的测量目的。

## 8. 按证据定位错误，再决定改哪里

| 现象 | 优先核对 | 这一轮可验证的动作 |
|---|---|---|
| 文档已改，回答还是旧的 | `/api/documents` 是否还是旧文本；索引是否已重建 | 先保存实际文本与版本，再走资料更新流程 |
| 命中文件却没有关键条件 | 候选 `text`，标题段与窗口边界 | 在离线副本比较切分，查看条件与结论是否被拆开 |
| 检索正确，回答仍缺条件 | `context_chunks` 是否删除/截短了必要片段 | 对照实际提示内容，而不是仅增加 top_k |
| 开重排以后变差 | 扩大候选后关键块的位置；CPU重排耗时 | 同题保留开/关两份完整结果，不隐藏退化 |
| supported 为 true 却答错 | 原始输出、实际引用与具体事实 | 记为人工事实错误，不修改标准答案迎合它 |
| supported 为 false 但看似答对 | 原始 supported、解析警告、未知引用、拒答冲突 | 区分输出格式失败、引用失败和真的无依据 |
| 来源指标满分而答案错误 | 是否命中同文件无关段；答案有没有资料外断言 | 增加逐字证据与逐句语义审阅 |
| 版本问题引用旧规则 | 生效日期、作废标记、问的是哪个时间 | 将日期与适用范围写进判断，不简单删除历史资料 |
| 400 / 422 | 业务错误说明 / 字段范围或类型 | 读响应 detail，不默认认为显存不足 |
| 502 | 上游模型请求、超时、服务日志 | 先核对18301服务；不要把上游失败计为正确拒答 |

最后保存两栏总结：**实现证据**写配置、版本、原始请求、输出与失败；**学习掌握证据**写你事先的预测、自己的解释、独立重做结果与仍不确定的地方。能解释一个失败，比只截取一次流畅回答更能证明你理解了整条链路。

本章编写时核对了当前源码与 Haystack 3.5.0 官方实现。文档中的网络请求和五题评测是供你执行的练习，没有在编写文档时代你运行；不包含新生成的模型成绩。
