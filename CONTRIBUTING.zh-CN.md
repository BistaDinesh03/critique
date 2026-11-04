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
