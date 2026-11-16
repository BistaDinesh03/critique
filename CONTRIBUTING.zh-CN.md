# 参与贡献 Critique

感谢你有意贡献！Critique 刻求简单、易于维护。

> 本文档是 Critique 贡献指南的简体中文翻译。**英文权威版本是
> [CONTRIBUTING.md](CONTRIBUTING.md)**；如两者存在差异，以英文版为准。
> 其中面向维护者的自动化脚本说明（`scripts/review_pr.py`、`scripts/contributor.py`）
> 等更深入的内容请参阅英文版。

## 入门

1. Fork 本仓库
2. 克隆你的 fork
3. 为你的改动创建一个分支
4. 完成改动
5. 运行测试
6. 提交 pull request

### 搭建开发环境

```bash
git clone https://github.com/YOUR_USERNAME/critique.git
cd critique
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
cd backend
uvicorn app.main:app --reload
```

打开 http://127.0.0.1:8000。本地浏览无需配置身份验证提供方 —— 如果你的改动
涉及登录后的流程，请参阅 [docs/github-oauth-setup.md](docs/github-oauth-setup.md)。

### 运行测试

添加新的前端渲染测试模块时，请复制以下模块级 `pytestmark`：

```python
pytestmark = [
    pytest.mark.frontend_render,
    pytest.mark.skipif(
        shutil.which("node") is None,
        reason="node is required to run the frontend rendering harness",
    ),
]
```

`frontend_render` 标记用于让 CI 的 collection guard 识别前端渲染测试。如果 CI 中缺少 `node`，并且标记的渲染测试因此会被跳过，CI 会失败；目前，如果测试模块缺少该标记，还不会被自动检测到（请参阅 issue #154）。

要在本地只运行前端渲染测试：

```bash
python -m pytest tests/ -m frontend_render -q
```

```bash
cd backend
python -m pytest tests/ -q
```

预期：**pytest passes**。请先安装 [Node.js](https://nodejs.org) —— 前端渲染测试需要
`node` 在 PATH 中，否则这些测试会被跳过。

想获得更快的反馈循环，可以只运行单个测试文件、某个测试函数，或按关键字匹配：

```bash
python -m pytest tests/test_main.py -q
python -m pytest tests/test_main.py::test_health_check -q
python -m pytest tests/ -q -k health_check
```

## 开发准则

### 保持简单

Critique 刻意避免复杂性。在添加任何东西之前，先问自己：

- 这解决了真实的问题吗？
- 能不能用更少的依赖做到？
- V1 真的需要它吗？

### 代码风格

- 遵循现有模式
- 使用有意义的命名
- 保持函数小巧
- 只在有价值处注释
- 不留死代码

### 测试

- 提交前运行全部测试
- 为新功能添加测试
- 测试必须 0 失败通过

### Pull request

- 保持 PR 聚焦且小步
- 说明你改了什么、为什么改
- 关联相关 issue
- 保持尊重与耐心

## 欢迎新贡献者

感谢你对为 Critique 做出贡献的兴趣！

在开始之前，请在 issue 下发表评论，以便我们确认该任务仍然可用。我们将帮助你理解实现并审查你的贡献。

无论是代码、测试、文档还是反馈，我们都由衷感谢每一份有意义的贡献。

### 首次贡献检查清单

1. 阅读 [README.zh-CN.md](README.zh-CN.md) 并浏览 [docs/first-contributors.md](docs/first-contributors.md)。
2. 从 [适合贡献的 issue](README.zh-CN.md#good-issues-to-contribute) 列表中挑选一个任务。
3. 在 issue 下评论认领（维护者将确认是否可用）。
4. Fork 仓库、新建分支、实现功能并添加测试。
5. 运行相关测试套件和 `git diff --check`。
6. 提交 Pull Request，关联对应 issue 并说明修改内容及原因。

### 维护者欢迎回复模板

当新贡献者提交第一个 issue 或 PR 时，请回复：

> 感谢你对为 Critique 做出贡献的兴趣！
>
> 在开始之前，请在 issue 下发表评论，以便我们确认该任务仍然可用。我们将帮助你理解实现并审查你的贡献。
>
> 无论是代码、测试、文档还是反馈，我们都由衷感谢每一份有意义的贡献。

请勿承诺即时审查或不切实际的响应时间。

## 找点事情做

带有 [`good first issue`](https://github.com/BistaDinesh03/critique/labels/good%20first%20issue)
标签的开放 issue 是不错的起点。对代码库或某种做法有疑问？开始之前先在
[issue #1](https://github.com/BistaDinesh03/critique/issues/1) 提问 —— 没有太小的问题。

issue 也按领域打了标签 —— `frontend`、`backend`、`tests`、`accessibility`、
`security`、`performance` —— 你可以筛选与你熟悉领域匹配的工作，或刻意挑战新领域。

一份经过整理和评审的 50 个 issue 计划位于
[docs/issue-roadmap.md](docs/issue-roadmap.md)。每条都写明了难度、要解决的问题
以及涉及哪些文件。想找具体的事情做，从那里开始。

## 我们如何协作

Critique 是一个由构建者提出一个专注问题、其他人来回答的网站。我们请贡献者以
同样的方式使用这个产品 —— 这是理解项目用途的最快方式。

对于典型的代码贡献：

1. **认领 issue。** 在 issue 下评论说明你打算做它。这能避免两人做同样的工作，
   也能让维护者在方案需要调整时及早给你指引。
2. **用一次 Critique。** 提交一个带专注问题的项目，或在他人的项目上给出有用的
   反馈。这不是审查 —— 而是为了让你的第一个 pull request 来自对产品的理解，
   而不仅仅是代码。
3. **Fork 并建分支。** Fork 仓库，创建分支，实现该 issue。
4. **测试，并在适用时亲自试用。** 运行相关测试。如果你的改动会影响访客所见，
   在 Critique 上亲自试一试，并问问其他构建者是否好用。
5. **提交 pull request。** 说明你改了什么、为什么，以及你运行了哪些测试。

### 例外，明说

这条准则是刻意轻量的，它**不是**一道关卡。它不适用于：

- **文档、可访问性与安全修复** —— 这些帮助的正是未必能像他人一样使用网站的人，
   先要求产品参与反而是把门槛设在了错误的地方。
- **你的第一次贡献** —— 一次贡献就足够。没有人需要反复参与才被欢迎。
- **错误报告与 issue 分类** —— 它们本身就是贡献。

参与没有费用，从不要求付费，除 GitHub 账号外也不需要任何个人信息。GitHub 上
没有任何东西能验证你是否用过该网站，我们也不会要求你证明 —— 这一步是为了帮助你，
而不是审查你。

## 维护者指引：评审 Pull Request

在本地克隆的仓库中，只需一条命令即可运行评审：

```bash
python scripts/review_pr.py 123                      # 仅评审与报告
python scripts/review_pr.py 123 --request-changes    # 同时发布评审意见
python scripts/review_pr.py 123 --merge              # 仅在所有关卡通过后合并
```

默认行为是非破坏性的：它读取 pull request、分析 diff、在剥离环境变量的临时克隆中运行测试套件，并输出报告。它绝不会向贡献者的分支推送代码，绝不修改 fork，并且没有 `--merge` 参数时绝不执行合并。该参数不会强行绕过未通过的检查 —— 存在失败检查、未解决阻塞项或缺少批准的 PR 都会被拒绝，并在报告中指明原因。

每份报告以 `READY`、`CHANGES_REQUESTED` 或 `BLOCKED` 结尾，随后以检查清单形式列出合并关卡。持续集成与默认分支（`main`）保护已在仓库中配置生效：每个 PR 均通过 GitHub Actions 运行必需的 `test` 检查，且 `main` 分支要求通过状态检查、保持分支最新、至少 1 个批准以及解决所有会话讨论。`--merge` 严格执行这些关卡，在任何要求未满足时均拒绝合并。

完整用法、各检查含义及局限性请参阅：
[docs/pull-request-review.md](docs/pull-request-review.md)。

周边工作流程 —— 寻找未认领的任务、将 issue 分配给提出申请的用户、检查 PR 关联的 issue，并在确认合并后关闭 issue 并致谢 —— 均由 `scripts/contributor.py` 处理：

```
python scripts/contributor.py triage                    # 查看可处理的任务
python scripts/contributor.py assign 30 --user USERNAME # 仅在用户申请后分配
python scripts/contributor.py review 57                 # 只读，补充 issue 背景
python scripts/contributor.py finalize 57 --merge       # 合并、关闭并致谢
```

完整工作流程说明请参阅：
[docs/contributor-workflow.md](docs/contributor-workflow.md)。

有关特定于本项目的评审检查清单，请参阅 [Maintainer Pull Request Review Checklist](docs/maintainer-guide.md)。

## 沟通

- 友善且有建设性
- 假设对方用意良好
- 聚焦于工作本身，而非个人

## 报告安全问题

请不要为漏洞开设公开 issue。请遵循 [SECURITY.md](SECURITY.md) 中描述的私下流程，
该文档也说明了项目与安全相关的行为。对于任何非漏洞的问题，
[issue #1](https://github.com/BistaDinesh03/critique/issues/1) 是个好去处。

## 许可证

贡献即表示你同意你的作品以 MIT 许可证授权。
