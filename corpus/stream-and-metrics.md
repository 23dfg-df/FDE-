# 流式输出与指标口径

文档 ID：d04

资料状态：已有实现说明与本实验测量规则

依据与范围：参考 labs/inference_demo/api.py、projects/inference-workbench/docs/项目总览与使用顺序.md；计时比较规则为本实验约定。

## 流式协议

已有基线服务的流式接口为 POST /generate/stream，响应类型为 text/event-stream。

基线流式事件包括 token、done 和 error；普通 JSON 响应不能当作逐 token 流式输出。


## 时间口径

客户端首 token 时间从发出请求计时，到收到第一个有效文本增量为止，包含网络和排队等待。

模型内部计时和客户端计时的起点不同，对照报告应分别标注。


## 成功与性能

总响应时间是请求开始到响应结束的时间；首 token 时间只描述第一次可见文本出现的等待。

吞吐、延迟、错误率和答案质量应分别记录，单独一个速度数字不能代表完整效果。
