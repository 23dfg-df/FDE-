# FDE Lab：知识库问答与模型部署学习项目

用一个可检查、可复现的知识库助手，学习 API、检索、模型推理、评测和交付。主线是 **Haystack + FastAPI + vLLM + Hunyuan-1.8B-Instruct**；页面提供知识库问答、检索对照、资料、评测和训练学习入口。

本仓库是公开展示与复现版本，地址为 [23dfg-df/FDE-](https://github.com/23dfg-df/FDE-)。它不包含模型权重、原始问答历史、服务器凭据或可直接连接私人服务器的配置。`examples/public-snapshot.json` 包含脱敏后的 17 份文档、50 道题和 1 条明确标记为**教学构造**的问答，不包含真实运行报告、训练曲线或 GPU 采样。教学问答不代表任何模型的实测表现；性能页没有报告时保留空状态。

## 先区分三个运行场景

| 场景 | 可以做什么 | 需要什么 |
|---|---|---|
| GitHub Pages / 离线 HTML | 阅读课程、公开资料和教学问答；在浏览器保存学习笔记 | 浏览器 |
| CPU CI / 本地测试 | 检查数据、引用规则、索引、接口契约和静态页面构建 | Python 3.11、Node.js 22、测试依赖 |
| 自己的实验服务器 | 运行真实模型、知识库问答、GPU 推理和训练实验 | 独立运行环境、外置模型和可用 GPU |

**Pages 是静态展示，不运行 FastAPI、vLLM 或 GPU 任务。** 静态页面不会连接原作者的实验服务器。浏览器学习笔记保存在当前浏览器，换设备前请导出；它们不会通过 GitHub 自动同步。

## 在本地打开学习页

在仓库根目录执行，构建过程不需要 GPU、模型或运行中的 API：

```bash
python3 scripts/build_offline.py \
  --snapshot examples/public-snapshot.json \
  --output site/index.html
```

双击 `site/index.html`，或运行下面的命令后打开 `http://127.0.0.1:8080`：

```bash
python3 -m http.server 8080 --bind 127.0.0.1 --directory site
```

完整的源码上传步骤见 [GitHub 发布说明](docs/GitHub发布.md)。

## 在自己的 GitHub 仓库启用 Pages

1. 将公开版源码上传到自己的 GitHub 仓库；确认默认分支包含 `.github/workflows/pages.yml` 和公开快照。
2. 打开仓库 **Settings → Pages → Build and deployment**，将 **Source** 设为 **GitHub Actions**。
3. 等待 **CPU checks** 工作流通过。它只测试和构建，不会发布网站。
4. 打开 **Actions → Publish learning page → Run workflow**，选择默认分支并手动运行。
5. 发布完成后，在工作流的 `github-pages` 环境链接或 Settings → Pages 查看实际访问地址。若设置了环境保护规则，按自己的仓库规则完成部署审核。

Pages 工作流仅接受 `workflow_dispatch`，推送代码不会自动发布。发布前检查公开快照内容；后续更新页面也通过同一手动入口。配置依据见 [GitHub Pages 自定义工作流](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) 和 [发布来源设置](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)。

## 运行 CPU 检查

```bash
python3 -m venv .venv-ci
source .venv-ci/bin/activate
python -m pip install -r requirements-ci.lock.txt
PYTHONPATH=.:evaluation:training:inference python -m pytest -q \
  tests evaluation/test_validate_dataset.py training/test_training.py \
  inference/test_benchmark.py inference/test_lora.py
node --check web/app.js
node --check web/lessons.js
```

这些测试使用假模型、模拟 HTTP 响应和临时目录，不下载模型、不占用实验服务器。通过说明对应软件契约成立，不能替代真实 GPU 运行、答案语义审阅或容量验收。推理环境的 CUDA 依赖不要装入这套轻量 CI 环境。

## 继续到真实服务器实验

模型权重外置，按自己的机器准备生成模型、tokenizer、BGE 向量模型和重排模型，并分别准备 `.venv-vllm` 与 `.venv-app`。先查看并按自己的目录修改 `config.example.sh`，再载入配置。示例配置将模型放在仓库旁的 `../models/`；它会覆盖应用原有的 BGE 默认目录。

```bash
source config.example.sh
bash inference/start-hunyuan.sh
```

模型启动后，在另一个终端进入同一仓库并启动应用：

```bash
source config.example.sh
bash start.sh
```

模型服务默认使用服务器回环地址的 18301 端口，应用使用 18300。`FDE_MODEL_PATH` 指定外置模型；`FDE_PHYSICAL_GPU` 与 `FDE_GPU_MEMORY_UTILIZATION` 指定设备和显存规划比例，示例值分别为 `0` 与 `0.28`，需要按实际共享资源核对。应用配置使用 `CAPSTONE_EMBEDDING`、`CAPSTONE_RERANKER`、`CAPSTONE_TOKENIZER`、`CAPSTONE_MODEL_URL` 和 `CAPSTONE_MODEL_NAME`；模型名与 tokenizer 必须匹配实际服务。显存规划比例不是算力配额。

首次部署请按 [服务器部署](docs/服务器部署.md) 创建环境、下载外置模型并验证请求；练习任务见 [学习与复现](docs/学习与复现.md)。需要核对上游兼容要求时参考 [Haystack 安装文档](https://docs.haystack.deepset.ai/docs/installation)、[vLLM 0.11.2 GPU 安装文档](https://docs.vllm.ai/en/v0.11.2/getting_started/installation/gpu/) 和 [腾讯 Hunyuan-1.8B-Instruct 模型卡](https://huggingface.co/tencent/Hunyuan-1.8B-Instruct) 准备独立环境。GitHub Actions 不负责启动或管理你的 GPU 服务。

保留的 Qwen 训练与对照源码属于历史实验用途，公开包没有附带它们的真实报告、曲线或适配器。**基于 Qwen 训练的 `incident-triage` LoRA 不兼容 Hunyuan；本项目没有完成混元微调。** 自己重做旧模型与新模型实验时，应分别标注模型、参数、计时口径和语料版本。

## 从源码理解链路

| 位置 | 关注的问题 |
|---|---|
| `backend/main.py` | 输入怎样校验，错误怎样返回？ |
| `backend/services.py` | 检索结果怎样进入模型，引用怎样检查？ |
| `backend/indexing.py` | 原文怎样切分，BM25、向量和混合检索怎样协作？ |
| `backend/repository.py` | 实验历史怎样保存与备份？ |
| `evaluation/` | 参考答案、原句证据和开发/测试划分是否一致？ |
| `training/` | 合成工单任务怎样划分数据、评分和保存适配器？ |
| `web/` | 真实状态与保存记录怎样区分？ |
| `examples/public-snapshot.json` | 公开页面具体展示了哪些经过筛选的内容？ |

`supported`、HTTP 200、引用文件名或测试通过都不等于答案事实正确。助手已经实现的功能也不等于学习者已经掌握：每次练习请分别记录“程序运行的证据”和“自己能解释、复做、排障的证据”。

## 来源与许可状态

本项目使用上游框架的依赖接口，没有将上游实现宣称为原创。第三方来源和模型许可入口见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。**本项目原创源码的许可证尚未选择，本次没有添加 MIT 或其他源码许可证。** 模型与第三方组件分别适用各自的许可，公开仓库不分发它们的权重。
