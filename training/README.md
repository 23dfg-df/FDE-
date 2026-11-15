# 历史 Qwen QLoRA：故障工单分类与结构化输出

本目录是 Qwen2.5-3B 专用的历史实验源码，不是混元微调入口。公开包不提供原始成绩或适配器。需要自行准备匹配基座与独立 .venv-training 环境；不能直接使用当前混元模型目录。

这个实验把工单映射到四类故障及固定的下一项检查。数据是虚构教学案例，不代表真实事故或业务泛化能力。
完整链路是：数据审计 → 同精度基线评测 → 参数更新 → 验证损失 → 保存适配器 → 训练进程退出 → 独立进程重载 → 再次评测。

## 任务与数据

模型只输出 JSON，字段为 `category` 和 `next_check`。

| 类别 | 固定检查动作 |
| --- | --- |
| port_conflict | inspect_listening_port |
| gpu_oom | inspect_gpu_memory |
| connection_failed | check_service_and_tunnel |
| model_files_missing | verify_model_path |

`data/` 中有 80 条训练、16 条验证、20 条测试。四类在各划分中均衡。
叙述模板家庭不跨划分，问题与 ID 不重复；底层故障信号和标签映射仍然共享，因此这是有限的模板迁移教学实验。
`build_dataset.py` 可重建原始数据；不要为迎合模型输出而改参考标签。

## 先做一个练习

先阅读一条工单，自己写出两个字段。再预测：基线是否会输出 Markdown、额外解释，或把类别选对但检查动作选错？
先运行数据预检，暂不启动 GPU。服务器项目目录：`/home/learner/test/fde-capstone`。

```bash
.venv-training/bin/python training/experiment.py --check-data
python3 -m unittest discover -s training -p 'test_training.py' -v
```

数据预检使用真实 Qwen 聊天模板，确保完整提示和目标答案都放得下；超过 256 token 会报错，不能默默截断标签。
单元测试不加载模型，也不调用 GPU。

## 参数与隔离

- 基座：本地 `Qwen/Qwen2.5-3B-Instruct`，默认路径 `/home/learner/test/inference-demo/model`。
- 量化：NF4 4-bit、双重量化、BF16 计算。
- LoRA：仅 `q_proj`、`v_proj`，rank 8、alpha 16、dropout 0。
- batch size 1、梯度累积 4、学习率 0.0002、80 次优化器更新、固定种子 42。
- 输入加完整标签上限 256 token；生成上限 64 token，贪心生成。
- 每 10 次优化器更新测验证损失，其余曲线点为 null，不能绘成 0。
- 基线在相同 k-bit 准备和零增量 LoRA 初始化后测量，保证前后精度准备一致。
- GPU 由 `CUDA_VISIBLE_DEVICES` 限制到一张卡，脚本内部 `cuda:0` 是该物理卡的逻辑编号。

默认物理 GPU 0。加载前要求至少 10 GiB 空闲显存，后续共享资源仍可能变化。
本实验不停止基线服务、不终止他人任务、不修改全局环境。vLLM 在另一张卡上的负载可能影响共享 CPU，因此训练时不要同时做严谨的推理速度对照。

## 运行完整实验

先记录自己的 GPU 资源窗口，之后执行：

```bash
nvidia-smi --query-gpu=index,name,memory.free,memory.used,utilization.gpu --format=csv
.venv-training/bin/python -u training/experiment.py --physical-gpu 0 --steps 80
```

默认每次创建独立的 `evidence/training/run-日期时间/`，不覆盖前一实验。也可通过 `--output-dir` 指定尚不存在的目录。
调整模型存放位置时传 `--model-path`。该脚本不会自动下载基础权重。
训练子进程最多运行 30 分钟，重载子进程最多运行 10 分钟；超时会终止自己的进程组并保留失败记录。
在正在运行命令的服务器终端按 Ctrl+C，父进程会清理自己的子进程组并记录中断；不能把仅关闭浏览器当作已取消训练。

经过本次环境检查的依赖为：PyTorch 2.9.1+cu128、Transformers 4.57.1、PEFT 0.17.1、bitsandbytes 0.48.1。
请在自己的 .venv-training 安装上述依赖，并显式传入 --model-path 指向 Qwen 权重。迁移机器时需要按相应 GPU/驱动重新验证依赖兼容，不能仅凭版本号保证启动。

## 读产物和指标

| 文件 | 内容 |
| --- | --- |
| config.json | 超参数、模型路径、设备及种子 |
| progress.json | 当前阶段、优化器步数、训练与验证曲线 |
| before.json | 训练前 20 道测试题的实际输出与规则分数 |
| training-result.json | 前后逐题输出、验证损失、曲线、参数量与显存 |
| adapter/ | PEFT 配置和 safetensors 适配器权重 |
| reload-result.json | 独立进程重载后的 20 道测试与逐题一致性 |
| summary.json | 实际汇总、数据范围和限制 |
| ticket-adapter.zip | 适配器与实验摘要，不含完整基座 |
| train.log / reload.log | 两个阶段的真实日志 |
| failure.json | 只有运行失败或中断时才产生的错误记录 |

四个分数分别表示严格 JSON 结构、类别、动作和三者联合通过率。错误格式的样本也在分母中。
这些分数只衡量这个四分类教学任务，不能替代自然语言质量或复杂故障排查能力。
验证损失按有效答案 token 数加权，不包含被屏蔽的系统和用户提示标签。
张量显存峰值只反映本进程 PyTorch 的分配，不是整卡总占用。
前后都是 100%、没有提升或发生退化时，应如实保存；不要换题制造改善。

<details><summary>需要时展开结果解释提示</summary>

格式改善但类别没变：模型可能主要学会了按约定输出。类别改善：检查是否只是有限故障词的映射。
验证损失下降但测试分数不变：更偏好参考 token 不一定改变最终选择。
重载答案完全一致：说明保存及加载路径复现了这批输出；这不证明它处理新故障一定正确。
基线与训练后采用同一份测试集，但训练循环不依据测试分数选步数；若之后根据测试表现调参，应将这批题视为已参与开发。

</details>

## 你需要交出的学习证据

先写预测，再自己重跑一次，并用一个新工单测试保存后的模型。
记录实验目录、参数、实际答案、验证损失和一个未达到预期的地方。
解释为什么 LoRA ZIP 仍然需要基础权重、为什么不能把测试答案加入训练、为什么模型能输出 JSON 不等于建议一定正确。
助手完成运行属于实现证据；你独立完成这些操作和解释才构成学习掌握证据。
