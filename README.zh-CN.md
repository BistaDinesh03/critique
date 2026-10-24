<p align="center">
  <img src="docs/logo-readme.svg#svgView(viewBox(0,0,64,47.5))" alt="Critique" width="72" />
</p>

<h1 align="center">Critique</h1>

<p align="center">
  <strong>问一个问题。得到真实的回答。</strong>
</p>

<p align="center">
  Critique 是一个开源平台，用于围绕你的项目开展专注、结构化的人工反馈。
  分享你正在构建的东西，提出一个具体的问题，收集那些真正看过你项目的人的回应。
</p>

<p align="center">
  <a href="https://github.com/BistaDinesh03/critique/actions/workflows/tests.yml"><img src="https://github.com/BistaDinesh03/critique/actions/workflows/tests.yml/badge.svg" alt="Tests" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/BistaDinesh03/critique" alt="License: MIT" /></a>
</p>

<p align="center">
  <a href="https://critique.page/">试用 Critique</a> ·
  <a href="https://critique.page/discover">浏览项目</a> ·
  <a href="https://github.com/BistaDinesh03/critique">源代码</a> ·
  <a href="https://github.com/BistaDinesh03/critique/issues">Issues</a> ·
  <a href="CONTRIBUTING.zh-CN.md">贡献指南</a>
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <strong>简体中文</strong> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.es.md">Español</a>
</p>

> 本文档是 Critique 的简体中文翻译。**英文版 [README.md](README.md) 是权威版本**；
> 如两者存在差异，以英文版为准。

## 了解 Critique

一段 62 秒的产品实拍演示——涵盖主页、Discover 信息流、一个项目页面，
以及创建者最终收到的反馈结果。

![Critique 演示动画 GIF：主页标题“Stop getting 'Looks good.'”以及 Get feedback on my project 与 Give feedback to a builder 两个按钮，随后是 Discover 信息流中的项目卡片](docs/videos/critique-overview-preview.gif)

**想看完整演示？[观看 62 秒视频。](https://dineshbista.com.np/critique/watch.html)**

上面的 GIF 是 12 秒预览；完整演示时长 62 秒、无音频，观看页面上的播放器
只有在你按下播放后才会开始。想看原始文件？请使用[直接 MP4 链接](https://dineshbista.com.np/critique/videos/critique-overview.mp4)
（46.8 MB）。<br />
原始文件：[docs/videos/critique-overview.mp4](docs/videos/critique-overview.mp4)
—— 1854×902，30 fps，62 s，H.264 MP4，46.8 MB，已提交到本仓库，
因此每次克隆都会包含它，并通过 GitHub Pages 观看页面播放。

## 问题所在

你可能花了数小时构建某个东西，却依然不知道别人是否明白它是什么、
它做什么，或者它为什么重要。发出一句“你觉得怎么样？”通常只会换来一句
“看起来不错！”——礼貌，但没有可操作性。

构建者只能靠猜：用户理解这个项目了吗？他们真的会用吗？应该改进什么？
模糊的反馈回答不了这些问题。

## 解决方案

Critique 用一个清晰的信号取代猜测。分享你的项目，提出**一个专注的问题**——
例如，*"你能在 10 秒内看懂这是做什么的吗？"*——并从真实的人那里获得结构化反馈。

一个问题让回答具有可比性，而每一个回答都是你可以付诸行动的信号。
所有反馈都来自使用该网站的真实用户；Critique 不包含任何 AI 生成的回复。

> 一个项目。一个专注的问题。真实的人类反馈。

## 工作原理

<table>
  <tr>
    <td align="center"><strong>1. 创建项目</strong><br>添加你构建了什么以及它的作用。</td>
    <td align="center"><strong>2. 提出一个专注的问题</strong><br>你最想知道的那一件事。</td>
    <td align="center"><strong>3. 与他人分享</strong><br>把链接发送到你的受众所在的任何地方。</td>
    <td align="center"><strong>4. 从结构化反馈中学习</strong><br>每个回复都有评分，另可附上文字建议。</td>
  </tr>
</table>

## 功能特性

- **Discover** —— 一个公开的、寻求反馈的项目信息流，按确定性规则排序
  （需求程度、新鲜度、问题质量等）
- **My Projects** —— 管理你的提交并回顾结果
- **Results 仪表盘** —— 每个项目的总计、分布柱状图和文字反馈
- **一个专注的问题** —— 每个项目只问一个问题，另有两个固定的评分问题，
  让回复易于浏览和比较
- **私密的文字建议** —— 附在项目上，仅项目所有者可见
- **简单分享** —— 提交之后或从 My Projects，一键发布到 X 或 Reddit，或复制链接
- **动态徽章** —— 一个实时显示回复数量的 SVG，可嵌入你的 README（见下文）
- **登录方式** —— GitHub OAuth 或无密码邮箱魔术链接
- **注重隐私** —— 不存储原始 IP 地址，无第三方跟踪脚本，分析数据极简
- **开源** —— 完整实现以 MIT 许可证公开发布，应用可开箱本地运行
- **SEO 支持** —— `robots.txt`、动态 `sitemap.xml`，以及主页社交预览元数据

## 反馈模型

每个回复都回答两个核心问题。

<table>
  <tr>
    <th align="center">这个项目清晰吗？</th>
    <th align="center">你会使用它吗？</th>
  </tr>
  <tr>
    <td align="center">非常清晰<br>基本清晰<br>令人困惑</td>
    <td align="center">会<br>也许<br>不会</td>
  </tr>
</table>

> 项目所有者还可以收到可选的文字建议 —— 仅对所有者可见。

## 反馈徽章

每个项目都有一个可嵌入的 SVG 徽章，显示其实时回复数量：

- **徽章端点：** `GET /badge/{project_id}.svg` ——
  `https://critique.page/badge/PROJECT_ID.svg`
- **链接到：** 项目页面 —— `https://critique.page/project/PROJECT_ID`

```markdown
[![Critique](https://critique.page/badge/PROJECT_ID.svg)](https://critique.page/project/PROJECT_ID)
```

把 `PROJECT_ID` 替换为你的项目 ID —— 即 Critique 网址中的那个数字。
计数在每次请求时从数据库渲染，1000 以上显示为 `1k+`。

## 试用 Critique

> 有一个你不太确定的项目？提出一个专注的问题，看看真实的人怎么想。

<p align="center">
  <a href="https://critique.page/">
    <img src="static/og-image.png" alt='Stop getting "Looks good." — Ask one question. Get real answers. — critique.page' width="600" />
  </a>
</p>

[打开 Critique](https://critique.page/) ·
[浏览项目](https://critique.page/discover)

## 技术栈

| 层 | 技术 |
|---|---|
| Web 框架 | FastAPI（Python 3.11+） |
| 数据访问 | SQLAlchemy 2.x |
| 数据存储 | SQLite（开发环境）、PostgreSQL（生产环境） |
| 前端 | 原生 HTML/CSS/JavaScript —— 无构建步骤 |
| 身份验证 | GitHub OAuth 与无密码邮箱（Resend） |
| 部署 | Render（`render.yaml`） |

## 架构

```text
Browser — vanilla HTML/CSS/JavaScript
   │
   │  HTML pages + JSON API calls
   ▼
FastAPI — routes, auth, CSRF, rate limiting
   │
   │  SQLAlchemy ORM queries
   ▼
SQLAlchemy — models, validation, migrations
   │
   ▼
SQLite (development)  /  PostgreSQL (production)
```

服务器直接提供 `frontend/` 中的页面，并在 `/api/*` 下暴露 JSON API。
前端没有构建步骤，除 SQLAlchemy 之外也没有额外的 ORM 层。

<details>
<summary>仓库结构</summary>

```text
backend/
  app/
    main.py                   App setup, page routes, /health, cache headers
    auth.py                   GitHub OAuth, email magic links, sessions
    csrf.py                   Double-submit-cookie CSRF protection
    config.py                 Environment-based settings
    database.py               Engine, table creation, additive migrations
    models.py                 SQLAlchemy models
    schemas.py                Pydantic request/response validation
    ranking.py                Deterministic Discover ranking
    rate_limit.py             In-memory per-endpoint rate limiting
    analytics.py              Event storage and visitor cookie
    email.py                  Magic-link email delivery (Resend)
    routes_projects.py        Project CRUD and Discover feed
    routes_responses.py       Feedback submission and listing
    routes_results.py         Aggregated results for owners
    stats.py                  Aggregate feedback statistics
    routes_badge.py           GET /badge/{id}.svg
    routes_stats.py           GET /api/stats
    routes_analytics.py       Event allowlist, /api/analytics/track
    routes_analytics_dashboard.py  Owner analytics endpoint
    routes_seo.py             robots.txt and sitemap.xml
  tests/                      pytest suite (API, security, frontend render)
frontend/                     HTML pages (vanilla JS, no build step)
static/                       CSS, JS, logos, favicon
docs/                         Setup guides and API reference
render.yaml                   Deployment config
```

</details>

## 快速开始

**环境要求：** Python 3.11+、Git。Node.js（任意近期版本）仅在运行前端渲染
测试时需要 —— 当 `node` 不在 PATH 中时这些测试会被跳过。

```bash
git clone https://github.com/BistaDinesh03/critique.git
cd critique
python -m venv .venv
```

激活虚拟环境：

```bash
# macOS / Linux
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

安装依赖、创建环境文件并启动服务器：

```bash
pip install -r requirements.txt
cp .env.example .env    # Windows: copy .env.example .env
cd backend
uvicorn app.main:app --reload
```

打开 http://127.0.0.1:8000。SQLite 数据表会在启动时自动创建 —— 无需单独的迁移步骤。

本地浏览无需登录；只有提交或管理项目时才需要登录。GitHub OAuth 与邮箱魔术链接
（包括邮箱登录所需的 `RESEND_API_KEY` 和 `EMAIL_FROM` 值）的配置方法见
[docs/github-oauth-setup.md](docs/github-oauth-setup.md)。

## 环境变量

把 `.env.example` 复制为 `.env`，并按需设置。`.env` 已被 gitignore ——
切勿提交真实凭据。

| 变量 | 用途 | 默认值 / 备注 |
|---|---|---|
| `APP_ENV` | `development` 或 `production` | `development` |
| `APP_URL` | 公开的基础 URL | `http://127.0.0.1:8000` |
| `SECRET_KEY` | 为会话令牌和 OAuth state 签名 | 无默认值 —— 生成：`python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | 数据库连接字符串 | `sqlite:///./critique.db`；生产环境使用 PostgreSQL |
| `GITHUB_CLIENT_ID` | GitHub OAuth 应用客户端 ID | 可选 —— 启用 GitHub 登录 |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth 应用密钥 | 可选 |
| `GITHUB_REDIRECT_URI` | OAuth 回调 URL | `http://127.0.0.1:8000/auth/callback` |
| `SESSION_COOKIE_SECURE` | 在 HTTPS 之后设为 `true` | `false` |
| `SESSION_COOKIE_MAX_AGE` | 会话有效期（秒） | 可选；`604800`（7 天） |
| `RESEND_API_KEY` | 用于魔术链接邮件的 Resend API 密钥 | 可选 —— 启用邮箱登录 |
| `EMAIL_FROM` | 魔术链接的发件地址 | 可选；需在 Resend 中验证 |

## 数据库

开发环境使用 SQLite（`critique.db`，已被 gitignore）—— 即未设置 `DATABASE_URL` 时的默认值。
启动时应用会运行 `init_db()`，它会创建数据表并为 SQLite 和 PostgreSQL
应用轻量的增量迁移，因此无需单独的迁移步骤。生产环境使用 PostgreSQL，
由托管环境提供 `DATABASE_URL`，并保存在仓库之外。

## 测试

```bash
cd backend
python -m pytest tests/ -q
```

目前有 501 个测试通过。测试套件覆盖 API 行为、CSRF、限流、所有权检查、
隐私规则、排序、XSS、分析校验、身份验证流程、SEO 端点，以及通过基于 Node 的
DOM 测试装置进行的前端渲染测试（无 Node.js 时跳过）。

## API

JSON API 的文档见 [docs/api.md](docs/api.md)。主要分类：

- **身份验证** —— `/auth/*`：GitHub OAuth、邮箱魔术链接、会话检查、CSRF 令牌
- **项目** —— `/api/projects/`：创建、Discover 信息流、所有者列表、详情、删除
- **反馈** —— `/api/projects/{id}/responses`：提交并读取回复
- **结果** —— `/api/projects/{id}/results`：面向所有人的聚合，面向所有者的文字建议
- **徽章** —— `/badge/{id}.svg`：实时回复数量
- **统计与分析** —— `/api/stats`、`/api/analytics/track`
- **SEO** —— `robots.txt`、`sitemap.xml`

应用运行期间，交互式文档位于 `/docs`（Swagger UI）和 `/redoc`，
健康检查位于 `GET /health`。

示例 —— 列出当前正在寻求反馈的项目（公开，无需身份验证）：

```bash
curl -s https://critique.page/api/projects/
```

响应是分页的（`items`、`total`、`page`、`page_size`、`total_pages`），
每一项包含项目的 `title`、其 `question_text`，以及实时的 `response_count`。

## 安全与隐私

Critique 在设计上充分考虑了安全与隐私：

| 防护措施 | 行为 |
|---|---|
| **CSRF 防护** | 所有改变状态的请求都使用双提交 Cookie 并附带 `X-CSRF-Token` 头；会话存放于 `HttpOnly`、`SameSite=Lax` 的 Cookie 中，当 `SESSION_COOKIE_SECURE=true` 时附加 `Secure`（Render 会设置该值） |
| **限流** | 覆盖身份验证与邮箱登录、项目创建与删除、反馈提交以及分析接口 |
| **输入校验** | 每个请求体都经过 Pydantic 校验，反馈字段有严格的模式约束 |
| **XSS 防护** | 用户可控输出在前端会被转义，并有 XSS 回归测试覆盖 |
| **身份验证与所有权检查** | 项目所有权在服务端基于会话校验，绝不信任客户端提交的请求头 |
| **私密文字反馈** | 建议仅返回给项目所有者 |
| **安全的重定向处理** | 登录的 `return_to` 值会针对本地路径白名单进行校验 |
| **基于环境的密钥** | 凭据来自环境变量，绝不存放在仓库中 |
| **极简分析** | 事件按服务端白名单校验；无第三方跟踪脚本；不存储原始 IP 地址（仅存储用于去重的 SHA-256 哈希） |

[SECURITY.md](SECURITY.md) 列出了完整行为，并说明如何报告漏洞。

## 部署

部署在 `render.yaml` 中配置：一个 Render 网络服务加一个 PostgreSQL 数据库。
`APP_ENV=production` 和 `SESSION_COOKIE_SECURE=true` 在此设置；
密钥 —— `DATABASE_URL`、`SECRET_KEY`、OAuth 凭据和邮件密钥 —— 均标记为
`sync: false`，并在 Render 控制台手动输入，绝不存放在仓库中。完整的变量清单见
`render.yaml`。

## 产品分析

> **分析快照** —— 某一时间点的事件总计。未提供报表周期。

**概览：** 1,443 次页面浏览 · 263 位独立访客 · 232 次项目浏览 ·
20 次反馈提交。

**转化漏斗：** 232 次项目浏览 → 92 次反馈开始 → 65 次提交尝试 →
20 次成功提交。

![Critique 产品分析快照](docs/analytics-snapshot.svg)

这些总计是记录下来的单一快照 —— **并非实时分析**；数字不会自动更新。
所有百分比都是**事件比率**（一个事件计数除以另一个），而非独立用户转化率，
单个访客可以产生多个事件。

> **存在两份快照，且并不一致。** 本图与
> [HTML 分析报告](docs/analytics-snapshot.html)是在不同时间提供的，
> 总计并不相同（页面浏览为 1,443 vs. 1,582）。两者都未提供报表周期，
> 因此无法在此确定日期或进行对账。两份数据都按原样保留 ——
> 这一点记录在 [issue #23](https://github.com/BistaDinesh03/critique/issues/23)
> 中，等待妥善解决。

## 贡献

欢迎提交贡献、错误报告、文档改进以及深思熟虑的产品反馈。
一个不错的起点是带有 [`good first issue`](https://github.com/BistaDinesh03/critique/labels/good%20first%20issue) 标签的 issue。

1. Fork 本仓库
2. 为你的改动创建一个分支
3. 完成改动并添加测试
4. 运行测试套件
5. 提交 pull request

完整指南见 [CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md)（英文权威版为
[CONTRIBUTING.md](CONTRIBUTING.md)），如何报告漏洞见
[SECURITY.md](SECURITY.md)。

**想找点事情做？** 可以从精心整理的计划
[docs/issue-roadmap.md](docs/issue-roadmap.md) 开始 —— 其中 50 个经过评审的 issue，
每个都写明了问题、范围、验收标准、难度和相关文件。issue 也按领域打了标签
（`frontend`、`backend`、`tests`、`accessibility`、`security`、`performance`），
开始之前也欢迎在 [issue #1](https://github.com/BistaDinesh03/critique/issues/1) 提问。

我们也鼓励贡献者在提交第一个 pull request 之前，花一点时间亲自使用 Critique
—— 提交一个项目或给出反馈。[CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md)
解释了这条准则及其例外情况；这是理解产品的一种方式，而不是贡献的门槛。

## 开源

Critique 以 MIT 许可证开源。完整实现 —— 后端、前端、测试和部署配置 ——
位于 [github.com/BistaDinesh03/critique](https://github.com/BistaDinesh03/critique)。
欢迎提交 issue 和 pull request。

## 许可证

MIT —— 详见 [LICENSE](LICENSE)。
