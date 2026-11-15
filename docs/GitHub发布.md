# 将发布包放入你的 GitHub 仓库

目标仓库：[23dfg-df/FDE-](https://github.com/23dfg-df/FDE-)；公开学习页已发布到 [FDE 学习网站](https://23dfg-df.github.io/FDE-/)。下面的流程用于理解这次交付、复现到自己的仓库或发布后续修改。阅读教程无需重新创建仓库。

## 先分清四类内容

| 内容 | 本项目位置 | 更新后意味着什么 |
|---|---|---|
| 源码与教程 | `backend/`、`web/`、`docs/` | Git记录实现与文档版本，不会自动启动实验室进程 |
| 公开教学快照 | `examples/public-snapshot.json` | 决定静态网页保存的教学内容，不是实时数据库 |
| 构建产物 | `site/index.html` | 从页面源码和指定快照组合而成，可离线阅读 |
| 私人运行资料 | `data/`、`evidence/`、外置模型目录 | 由自己的实验产生，不随公开源码自动上传 |

`docs/` 是给学习者阅读的教程；`corpus/` 是供知识库检索的语料。扩写教程并不会自动扩大RAG语料，避免把题库答案或训练说明不加区分地塞进评测上下文。

一次文档更新推送到 GitHub 后，可以直接在仓库中阅读。静态网站使用的是发布工作流生成的产物，需要重新运行发布工作流才会更新页面；网站也不会自动加载仓库中新增的任意Markdown文件。

## 一次发布经过哪些状态

```mermaid
flowchart LR
    E[本地修改] --> B[提交到功能分支]
    B --> P[Pull Request]
    P --> C[CPU自动检查]
    C --> M[合并main]
    M --> W[手动运行Pages工作流]
    W --> A[上传静态产物]
    A --> D[部署到公开网址]
```

先做练习：如果你已经把文档上传到功能分支，但没有合并，默认分支的读者会看到它吗？如果合并完成，却没有重新发布 Pages，网站会自动变化吗？提示：分别检查 Git 分支、工作流提交 SHA 和网站产物，而不是只看其中一个页面。

## 上传源码

上传的是解压目录里的源码文件，不是把 ZIP 作为唯一文件放入仓库。`.github/` 是隐藏目录，也需要复制；它包含自动检查与 Pages 发布配置。

如果克隆的是现在这个已包含完整项目的仓库，直接在分支中修改文件即可；下面的“复制发布包”只用于把发布包导入初始仓库，不要求每次更新都用旧ZIP覆盖源码。

先把现有仓库克隆到一个新目录，保留 GitHub 上已有的历史。每轮修改使用一个未占用的功能分支名，下面以 `codex/learning-update` 为例：

```bash
git clone https://github.com/23dfg-df/FDE-.git FDE-publish
cd FDE-publish
git switch -c codex/learning-update
```

将本发布包根目录里的文件复制到 `FDE-publish` 中，保留 `.git` 目录。替换初始 README 为本项目 README，包含 `.github/`、`backend/`、`web/`、`examples/`、`tests/` 等目录。不要复制自己服务器的 `data/`、模型或凭据。

然后在 `FDE-publish` 执行：

```bash
git status --short
git add .
git diff --cached --stat
git commit -m "Add Hunyuan FDE learning lab and CPU checks"
git push -u origin codex/learning-update
```

提交前按 Git 提示设置自己的姓名与提交邮箱，推送时使用自己的 GitHub 身份完成认证。不要直接推送整个个人学习工作区。若出现文件冲突，先核对差异，不使用强制推送。

在 GitHub 仓库创建 `codex/learning-update` 到 `main` 的 Pull Request，检查改动并等待 **CPU checks** 通过，再合并。生成的 `site/` 在 Git 中被忽略，工作流会从源码重新构建；交付 ZIP 中仍附带可双击的 HTML。

## 怎样读自动检查，而不只看绿色图标

当前 `ci.yml` 做三类检查：

1. 用独立 Python 环境运行接口、索引、数据、输出规则与发布约束测试。
2. 检查浏览器脚本的语法是否可以解析。
3. 从公开快照重新构建单文件学习页。

它们能发现对应的软件问题，但没有实际下载GPU模型或验证所有自然语言答案。`tests/` 使用假的模型和模拟HTTP响应来检查边界，所以安装清单不包含完整GPU运行栈。运行记录还要核对提交SHA，别把旧提交的绿色结果当成新改动已经通过。

| 工作流停在哪一步 | 先看什么 |
|---|---|
| Checkout失败 | 仓库、分支、权限和目标提交是否存在 |
| 安装依赖失败 | Python版本、锁文件、包是否可下载及平台兼容 |
| Python测试失败 | 具体失败测试与断言，不先删掉测试 |
| JS语法失败 | 报错文件和行号，是否出现引号或括号错误 |
| 离线页构建失败 | 公开快照JSON、页面引用和构建脚本异常 |
| Pages配置失败 | Settings中的Source、仓库Pages设置 |
| Pages部署失败 | build产物、pages与id-token权限、部署环境要求 |

一次失败也要保存对应提交和日志。修复后验证新的提交，才能解释是什么改动解决了问题。

## 发布静态网站

1. 打开仓库 Settings → Pages，将 Source 设为 GitHub Actions。
2. 确认 `main` 上的 CPU checks 通过。
3. Actions → Publish learning page → Run workflow，选择 `main`。
4. 等待发布完成，通过工作流环境链接或 Settings → Pages 打开网站。

这是手动发布流程，普通推送只触发软件检查。部署依据：[GitHub Pages 自定义工作流](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)。实际网址和发布状态以 GitHub 返回结果为准。

完整知识库增加了一个明确的发布入口：准备好公开内容后，可在主分支提交消息中加入 `[publish-learning]`。工作流只在该仓库主分支的这次推送通过 `CPU checks` 后，检出并发布相同提交；没有这个标记的普通提交仍不发布。这个入口和手动按钮都构建原展示页及 `academy/`，并生成离线课程包。它不接受来自PR或其他仓库的成功检查作为发布条件。

## 发布后分别验收

- 源码：仓库有项目 README、源码、测试和 `.github/workflows/`。
- 自动检查：对应提交的 CPU checks 成功；失败时查看具体日志。
- 展示页：页面明确提示公开教学演示，能阅读资料和记录学习笔记。
- 真实实验：仍在自己的服务器执行，按 [服务器部署](服务器部署.md) 单独验证。

GitHub Pages 不运行 Python 后端或 GPU 推理。页面不自动连接私人服务器，也不会同步不同设备的浏览器学习笔记。

## 检查公开页面与产物是否一致

在本地构建一次后，可以用文件哈希核对真正发布的HTML。下面只下载公开页面，不连接实验室服务器；在仓库根目录执行。网络受限时先记录访问失败，不把请求失败等同于页面源码损坏。

```bash
python3 scripts/build_offline.py --snapshot examples/public-snapshot.json --output site/index.html
python3 - <<'PY'
from pathlib import Path
from urllib.request import urlopen
import hashlib
local = Path("site/index.html").read_bytes()
with urlopen("https://23dfg-df.github.io/FDE-/", timeout=20) as response:
    remote = response.read()
    print("HTTP:", response.status)
print("local SHA256:", hashlib.sha256(local).hexdigest())
print("remote SHA256:", hashlib.sha256(remote).hexdigest())
print("same bytes:", local == remote)
PY
```

如果刚改过源码但尚未发布，字节不一致可能正是预期结果。哈希一致说明下载到的内容与本地构建产物相同，不证明页面所有交互、视觉布局或学习内容已经正确，仍应分别检查。

<details>
<summary>核对本章开头的两个预测</summary>

功能分支上的新文档可通过该分支链接阅读，但默认分支仍显示合并前内容。合并代码与重新发布网站是两件事；普通main更新不会自动发布。需要手动运行工作流，或在明确要发布的主分支提交中使用 `[publish-learning]` 并等待CPU检查成功。最后仍要确认实际部署的提交与预期一致。

</details>

## 本章交付清单

- [ ] 能找到自己的修改提交，并解释哪些文件发生了变化。
- [ ] 能读出CI对应的提交、成功或失败步骤与未覆盖的验证范围。
- [ ] 能解释为什么仓库源码、公开快照、构建产物、实时服务是不同对象。
- [ ] 能从实际网址读取页面，并确认公开演示的身份与限制。
- [ ] 学习记录中分别写明“我执行了哪些操作”和“我能解释哪些原理”。
