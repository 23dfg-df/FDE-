# 将发布包放入你的 GitHub 仓库

目标仓库：[23dfg-df/FDE-](https://github.com/23dfg-df/FDE-)。这个交付包尚未上传，也没有启用网站。解压后先打开 `site/index.html` 预览；不需要登录账号或启动服务器。

## 上传源码

上传的是解压目录里的源码文件，不是把 ZIP 作为唯一文件放入仓库。`.github/` 是隐藏目录，也需要复制；它包含自动检查与 Pages 发布配置。

先把现有仓库克隆到一个新目录，保留 GitHub 上已有的历史：

```bash
git clone https://github.com/23dfg-df/FDE-.git FDE-publish
cd FDE-publish
git switch -c codex/github-release
```

将本发布包根目录里的文件复制到 `FDE-publish` 中，保留 `.git` 目录。替换初始 README 为本项目 README，包含 `.github/`、`backend/`、`web/`、`examples/`、`tests/` 等目录。不要复制自己服务器的 `data/`、模型或凭据。

然后在 `FDE-publish` 执行：

```bash
git status --short
git add .
git diff --cached --stat
git commit -m "Add Hunyuan FDE learning lab and CPU checks"
git push -u origin codex/github-release
```

提交前按 Git 提示设置自己的姓名与提交邮箱，推送时使用自己的 GitHub 身份完成认证。不要直接推送整个个人学习工作区。若出现文件冲突，先核对差异，不使用强制推送。

在 GitHub 仓库创建 `codex/github-release` 到 `main` 的 Pull Request，检查改动并等待 **CPU checks** 通过，再合并。生成的 `site/` 在 Git 中被忽略，工作流会从源码重新构建；交付 ZIP 中仍附带可双击的 HTML。

## 发布静态网站

1. 打开仓库 Settings → Pages，将 Source 设为 GitHub Actions。
2. 确认 `main` 上的 CPU checks 通过。
3. Actions → Publish learning page → Run workflow，选择 `main`。
4. 等待发布完成，通过工作流环境链接或 Settings → Pages 打开网站。

这是手动发布流程，普通推送只触发软件检查。部署依据：[GitHub Pages 自定义工作流](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)。实际网址和发布状态以 GitHub 返回结果为准。

## 发布后分别验收

- 源码：仓库有项目 README、源码、测试和 `.github/workflows/`。
- 自动检查：对应提交的 CPU checks 成功；失败时查看具体日志。
- 展示页：页面明确提示公开教学演示，能阅读资料和记录学习笔记。
- 真实实验：仍在自己的服务器执行，按 [服务器部署](服务器部署.md) 单独验证。

GitHub Pages 不运行 Python 后端或 GPU 推理。页面不自动连接私人服务器，也不会同步不同设备的浏览器学习笔记。
