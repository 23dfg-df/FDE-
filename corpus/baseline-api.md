# 已有 3B 基线服务的接口

文档 ID：d03

资料状态：已核对的历史实现

依据与范围：2026-11-15 核对本地 labs/inference_demo/api.py；运行验收记录来自 2026-11-11 的 inference-workbench/evidence。

## 路径与端口

已有基线服务使用 Qwen/Qwen2.5-3B-Instruct，服务器工作目录为 /home/learner/test/inference-demo。

该基线服务监听服务器的 127.0.0.1:18123，普通生成接口为 POST /generate。


## 请求参数

基线接口的 prompt 长度范围是 1 到 2000 个字符。

基线接口的 max_new_tokens 默认值为 128，允许范围为 1 到 256。


## 响应与错误

基线普通响应包含 answer、model、device、input_tokens、output_tokens、elapsed_seconds 和 peak_allocated_gib。

基线接口参数校验失败返回 HTTP 422；生成实例忙时返回 HTTP 429。
