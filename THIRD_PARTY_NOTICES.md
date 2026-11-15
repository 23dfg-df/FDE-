# 第三方来源与许可说明

本文件记录主要上游来源，不替代它们的完整许可证，也不为本项目原创源码指定许可证。**原创源码的许可证尚未选择；未添加 MIT、Apache-2.0 等项目级授权。**

## 检索与推理框架

| 组件 | 本项目用途 | 官方来源与许可入口 |
|---|---|---|
| Haystack | Document、检索管线、BM25、融合等组件 | [项目仓库](https://github.com/deepset-ai/haystack)、[Apache-2.0 许可证](https://github.com/deepset-ai/haystack/blob/main/LICENSE)、[安装文档](https://docs.haystack.deepset.ai/docs/installation) |
| vLLM | 独立模型推理服务；不属于 CPU CI 安装项 | [项目仓库](https://github.com/vllm-project/vllm)、[Apache-2.0 许可证](https://github.com/vllm-project/vllm/blob/main/LICENSE)、[本实验参考的 0.11.2 GPU 文档](https://docs.vllm.ai/en/v0.11.2/getting_started/installation/gpu/) |

FastAPI、HTTPX、pytest 等依赖通过包管理器安装；各发行包保留其各自许可与版权信息。本仓库没有重新分发这些上游仓库的完整源码，也不声称拥有其实现。

## 模型与历史适配器

- 当前生成模型来源为 [腾讯 Hunyuan-1.8B-Instruct](https://huggingface.co/tencent/Hunyuan-1.8B-Instruct)。它使用腾讯混元社区许可，具体以模型仓库的 [LICENSE](https://huggingface.co/tencent/Hunyuan-1.8B-Instruct/blob/main/LICENSE) 与 [Notice.txt](https://huggingface.co/tencent/Hunyuan-1.8B-Instruct/blob/main/Notice.txt) 为准，不将其称为 MIT 或 Apache-2.0 模型。
- 历史推理与 LoRA 实验来源为 [Qwen2.5-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct)。重做历史实验前应核对该模型版本对应的模型卡和许可；Qwen 适配器不能直接加载到混元。
- 检索模型来源为 [BGE-small-zh-v1.5](https://huggingface.co/BAAI/bge-small-zh-v1.5) 和 [BGE-reranker-base](https://huggingface.co/BAAI/bge-reranker-base)。模型及 tokenizer 应单独取得并按对应版本的许可使用。

公开版不包含上述基础权重、训练检查点、适配器二进制或历史实测曲线与报告。源码中保留的历史模型名称用于说明适配关系，不表示已完成新模型训练，也不对模型许可作重新授权。

## 展示材料与发布工具

公开快照用于展示 17 份脱敏文档、50 道题和 1 条标明教学构造的问答，不包含真实运行报告或历史记录。合成工单数据与示例问答不代表真实客户工单或模型实测能力。原始运行历史、账号、主机连接信息及未筛选资料不属于公开展示内容。

GitHub Actions / Pages 工作流使用官方 Actions，通过 GitHub 获取，不在仓库内复制其实现。发布设置参考 [GitHub Pages 官方文档](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)。
