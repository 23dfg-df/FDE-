# Kubernetes对象、滚动更新与扩缩

编号：ops-08 · 进阶实践 · 学习预算 8 小时

用一个无状态应用理解编排和回退边界。

## 学习目标

- 推演无状态应用的更新与失败回退
- 根据实际输入、结果与限制解释结论，区分实现证据与学习掌握证据

建议先修：[ops-06](ops-06.md)、[ops-03](ops-03.md)

## 声明期望状态，再观察实际收敛

Kubernetes保存期望对象，控制器比较实际状态并尝试调整。Pod承载容器，Deployment管理无状态副本和版本，Service提供稳定访问入口。删除受管理Pod可能被重建，却不说明数据恢复或高可用自动成立。先理解创建、调度、启动、就绪各阶段，再学复杂编排。官方examples先选当前维护的web例子，固定提交与API版本；归档目录仅作历史参考。不要直接对共享集群执行未经确认的示例清单。

## 配置和数据的生命周期各自设计

ConfigMap适合非敏感配置，Secret提供敏感值管理接口，但Base64不是加密保证。存储加密、访问控制和审计依平台实际配置。容器临时文件不承担持久化责任，持久卷也不自动提供备份与跨故障域复制。配置更新是否立即生效取决于注入和读取方式，可能要重启。学习用虚构值与个人命名空间，不将真实凭据写仓库。对象存在只证明控制面收到了配置，还须验证应用实际读取的内容。

## 资源与探针影响调度及流量

request参与调度，limit约束某些资源，不是越大越快。容量不足Pod可Pending，镜像拉取失败在另一个阶段。启动、存活、就绪探针有不同目的：加载很慢的模型若过早判定存活失败，会反复重启；依赖暂不可用可用就绪状态控制接流量。GPU还涉及设备插件和分配，不能把普通CPU示例当GPU隔离方案。先读事件与退出原因，再调整参数；单纯增加探针超时可能只是隐藏启动错误。

## 滚动替换不等于完成业务灰度

Deployment逐步替换副本，maxUnavailable和maxSurge影响可用副本与额外资源。它控制替换节奏，但按用户比例路由、根据业务指标停止仍需具体流程。保留低成本业务验收，看新版本就绪后的错误和延迟。回退主要恢复Pod模板，不撤销数据库写入与外部副作用。新旧同时运行时需接口和数据兼容，否则渐进替换也可能扩大故障窗口。记录旧版产物和触发条件，使回退能被验证。

## 扩容前找到下游瓶颈

加应用副本可缓解该层压力，但同一模型或数据库已满时会制造更多队列。自动扩缩要明确指标、范围、冷启动和资源上限，权重大、加载慢的实例不会瞬间吸收突发。队列、拒绝或降级仍必要。先在个人CPU测试环境理解对象状态，本课只提供阅读和推演任务，不声称已有集群。验收是能根据事件解释Pod为何没就绪、Service为何没有可用端点，而不是背出几十条kubectl命令。

## 一个就绪副本也可能承受过多流量

假设原来有两个副本，更新时一个旧副本退出，新副本尚未就绪，剩下副本可能继续接收全部流量。即使更新策略允许这个状态，业务延迟也可能超过目标。额外副本需要真实资源，如果集群没有余量，配置了surge也不意味着一定能调度。推演时同时写副本数量、就绪数量、实际资源和用户负载。它说明发布参数必须结合容量，而不能只复制官方示例数值。先练一个CPU应用的状态变化，再考虑启动更慢的模型实例。

## 只读观察测试命名空间

```bash
kubectl get deployment,service,pods -n YOUR_TEST_NAMESPACE --request-timeout=10s
kubectl describe deployment YOUR_DEPLOYMENT -n YOUR_TEST_NAMESPACE --request-timeout=10s
kubectl rollout status deployment/YOUR_DEPLOYMENT -n YOUR_TEST_NAMESPACE --timeout=60s --request-timeout=10s
```

要求已有授权测试集群，本轮未执行。查询的--request-timeout=10s限制单次API请求；rollout的--timeout=60s限制本次等待更新完成的时间。超时返回失败只表示本次观察未等到成功，不会自动停止Deployment更新或回滚，需保留状态与事件并按发布方案决定后续动作。

## 本课只做一个任务

推演无状态应用的更新与失败回退

1. 说明三个核心对象职责。
2. 预测新Pod加载慢时的副本变化。
3. 写停止发布和回退验证。

<details><summary>需要帮助时查看提示</summary>

- 区分启动与就绪。
- 数据不包含在Pod模板回退中。

</details>

<details><summary>已经尝试或求助后查看参考解释</summary>

描述旧版保留、新版启动、就绪接流量与旧版退出。新版本不就绪时停止继续替换并调查；回退后仍发业务请求确认。

</details>

### 验收

- 探针职责准确。
- 区分滚动更新与业务灰度。

需要保存：推演无状态应用的更新与失败回退的实际产物、验证结果与未解决问题

## 失败时检查

### 模型反复重启

可能原因：探针早于加载完成

检查：读原因与启动日志。

### 扩容更慢

可能原因：共享下游饱和

检查：看模型与数据库队列。

## 自测

### 1. Secret Base64证明加密存储？

- A. 证明
- B. 不证明
- C. 字段名证明

<details><summary>提交自己的选择后查看解释</summary>

参考选项：B。编码和加密不同。

</details>

### 2. Deployment回退恢复数据库？

- A. 会
- B. 不会，另行设计
- C. 两副本就会

<details><summary>提交自己的选择后查看解释</summary>

参考选项：B。模板与数据生命周期不同。

</details>

## 证据记录

- 实现证据：命令、输入、预期、实际结果、失败与未执行项。
- 学习掌握证据：自己能够解释、独立重做或定位的问题；不能用助手完成替代。

## 官方来源与延伸阅读

- [Kubernetes Examples](https://github.com/kubernetes/examples)：通过一个实例学习声明式部署 建议先读：先看README，选择web目录一个例子；_archived仅作历史参考。（核对 2026-11-16）
- [Kubernetes：Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)：理解副本、更新与回退 建议先读：Creating、Updating、Rolling Back。（核对 2026-11-16）
- [Kubernetes：Secret](https://kubernetes.io/docs/concepts/configuration/secret/)：配置与敏感值管理边界 建议先读：使用方式与存储保护说明。（核对 2026-11-16）
- [Kubernetes：kubectl rollout status](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_rollout/kubectl_rollout_status/)：核对等待与API请求超时参数 建议先读：查看--timeout及继承的--request-timeout说明。（核对 2026-11-16）
