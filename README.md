# draft-revise — OpenAI Codex skill

[English](#english) · [中文](#中文)

`draft-revise` is a community-maintained **skill for OpenAI Codex**. It turns PDF annotations or a separate review PDF into a traceable revision workflow and an offline HTML review. It is intended for manuscripts, reports, slides and similar documents with embedded comments. This is an independent community project, not an official OpenAI product.

[Releases](https://github.com/Zouyanzh/draft-revise-skill/releases) · [Tests](https://github.com/Zouyanzh/draft-revise-skill/actions) · [Contributing / 维护说明](CONTRIBUTING.md)

## English

### What it provides

- Preserves original PDFs and annotation evidence.
- Links comments to requirements, changes, exact text ranges and page regions.
- Generates a self-contained offline HTML review with a hierarchical contents panel, complete revised document, original/revised edit fragments, complete sentence comparisons, exact highlights and a responsive comment sidebar.
- Keeps native MathML, figures, tables and page evidence when the source can support them.
- Treats completed explicit replacements, insertions and deletions as accepted by default; only unresolved requirements need an opinion.
- Exports **feedback schema 2** for the next revision. Older feedback formats are rejected intentionally.

### Install for Codex

Clone a tagged release, then copy the `draft-revise/` directory into your Codex skills directory. The example below uses `$CODEX_HOME/skills` (or `~/.codex/skills`); use the skills directory configured by your Codex installation if different.

```sh
git clone --branch v0.1.0 --depth 1 https://github.com/Zouyanzh/draft-revise-skill.git
cd draft-revise-skill
python3 tools/install_local.py
```

The installer backs up an existing installation and records the installed release and commit. For a custom directory, pass `--dest /path/to/skills/draft-revise`. From a release archive, you can instead copy the enclosed `draft-revise/` folder into your skills directory. The skill is available on the next Codex turn.

In Codex, invoke it explicitly with `$draft-revise` or let normal skill discovery select it for a comment-based revision task. For example:

> Use $draft-revise to copy main.tex to main2.tex and revise it using comments.pdf. Preserve the original files and deliver an offline HTML review with exact comment links.

### Requirements and limits

Python 3.9+ is needed for the helper scripts. Run `python -m pip install -r requirements.txt` if the PDF libraries are unavailable. Development checks additionally use `requirements-dev.txt`, Node.js 18+ and `npm ci`. Editing or compiling TeX, Word or slide sources requires appropriate tools in the Codex environment. Scans and handwriting may need OCR or human clarification; the extractor does not supply semantic interpretation.

### Typical workflow

```sh
python draft-revise/scripts/draft_revise.py extract comments.pdf inventory.json --images
python draft-revise/scripts/draft_revise.py init inventory.json ledger.json --kind paper
# Populate the ledger after inspecting the source and applying the actual revision.
python draft-revise/scripts/draft_revise.py validate ledger.json
python draft-revise/scripts/draft_revise.py render ledger.json review.html
python draft-revise/scripts/draft_revise.py feedback ledger.json feedback.json
python draft-revise/scripts/draft_revise.py next-plan ledger.json feedback.json next-ledger.json
```

The ledger is authoritative for manuscript state. `render` only creates the review page. `next-plan` creates instructions for the next edition and does not edit the manuscript.

### Feedback contract

The HTML and CLI accept only schema 2. It contains complete `entries` for every change and complete `pending_entries` for every unresolved requirement. An invalid file is rejected atomically, including wrong document identity, missing records, duplicate records, altered links or invalid states.

### Test locally

```sh
python -m pip install -r requirements-dev.txt
python draft-revise/scripts/selftest.py

# Optional DOM checks, with jsdom installed from package.json:
npm ci
NODE_PATH="$PWD/node_modules" node draft-revise/scripts/review_ui_test.cjs review.html
```

### Scope and license

The skill does not publish, contact reviewers, or overwrite source files. It is released under the [MIT License](LICENSE). See [CHANGELOG.md](CHANGELOG.md) and the [v0.1.0 release notes](docs/releases/v0.1.0.md).

## 中文

### 这是什么

`draft-revise` 是一个社区维护的 **OpenAI Codex skill**。它把 PDF 批注或独立审阅 PDF 转换为可追踪的修订流程和离线 HTML 审阅页面，适用于论文、报告、幻灯片及其他带批注的文档。这是独立社区项目，并非 OpenAI 官方产品。

### 主要功能

- 保留原始 PDF 和批注证据。
- 将批注关联到要求、修改、精确文字范围和 PDF 页面区域。
- 生成自包含离线 HTML：分层目录、完整修订正文、原始／修订片段、完整语句对照、精确高亮和响应式批注侧栏。
- 在源文件可靠时保留 MathML 公式、图、表和页面证据。
- 明确的替换、插入、删除默认视为已接受；只有待决要求需要填写审阅意见。
- 导出用于下一轮修订的 **feedback schema 2**，旧反馈格式会被明确拒绝。

### 安装到 Codex

克隆指定发布版本，再安装到 Codex skills 目录。下例使用 `$CODEX_HOME/skills`（未设置时为 `~/.codex/skills`）；如果你的 Codex 配置使用其他目录，请通过 `--dest` 指定。

```sh
git clone --branch v0.1.0 --depth 1 https://github.com/Zouyanzh/draft-revise-skill.git
cd draft-revise-skill
python3 tools/install_local.py
```

安装脚本会备份已有版本，并记录发布版本与 commit。自定义位置可使用 `--dest /path/to/skills/draft-revise`。若从 Release 下载压缩包，也可以直接复制其中的 `draft-revise/` 文件夹。skill 会在下一轮 Codex 对话中可用。

在 Codex 中可以使用 `$draft-revise` 显式调用，也可以让普通 skill 自动发现机制在带批注的修订任务中选择它，例如：

> 使用 $draft-revise，把 main.tex 复制为 main2.tex，根据 comments.pdf 的批注进行修订。保留原始文件，并生成逐条精确关联的离线 HTML 审阅页。

### 依赖与边界

辅助脚本需要 Python 3.9+；缺少 PDF 库时执行 `python -m pip install -r requirements.txt`。开发检查另外需要 `requirements-dev.txt`、Node.js 18+ 和 `npm ci`。TeX、Word 或幻灯片源文件的编辑与编译需要 Codex 环境中的相应工具。扫描件、手写内容可能需要 OCR 或人工确认，提取脚本不负责语义判断。

### 常用流程

```sh
python draft-revise/scripts/draft_revise.py extract comments.pdf inventory.json --images
python draft-revise/scripts/draft_revise.py init inventory.json ledger.json --kind paper
# 检查源文件并完成实际修订后，填写 ledger。
python draft-revise/scripts/draft_revise.py validate ledger.json
python draft-revise/scripts/draft_revise.py render ledger.json review.html
python draft-revise/scripts/draft_revise.py feedback ledger.json feedback.json
python draft-revise/scripts/draft_revise.py next-plan ledger.json feedback.json next-ledger.json
```

ledger 是文档状态的权威记录；`render` 只生成审阅页面；`next-plan` 只生成下一轮说明，不会直接修改正文。

### 反馈格式

HTML 和 CLI 只接受 schema 2。它要求为每一条修改提供完整 `entries`，为每一个待决要求提供完整 `pending_entries`。文档身份、缺失记录、重复记录、关联关系或状态不正确时，整个文件会原子拒绝。

### 本地测试

```sh
python -m pip install -r requirements-dev.txt
python draft-revise/scripts/selftest.py

# 可选 DOM 检查：先根据 package.json 安装 jsdom。
npm ci
NODE_PATH="$PWD/node_modules" node draft-revise/scripts/review_ui_test.cjs review.html
```

### 范围和许可证

该 skill 不会发布文档、联系审阅者或覆盖源文件。项目采用 [MIT License](LICENSE)。版本变化见 [CHANGELOG.md](CHANGELOG.md)，首版说明见 [v0.1.0 release notes](docs/releases/v0.1.0.md)。

## Versioning / 版本规则

This repository uses semantic versioning: patch releases fix bugs, minor releases add backward-compatible features, and major releases change the public contract. The skill release number is independent from ledger schema and feedback schema numbers.

本仓库使用语义化版本：补丁版本修复问题，次版本增加兼容功能，主版本改变公开契约。skill 发布版本与 ledger schema、feedback schema 独立编号。

## Continuous maintenance / 持续维护

Changes should pass GitHub Actions before a tag is created. Update `VERSION`, `CHANGELOG.md` and matching release notes, commit the change and create a tag such as `v0.1.1`. A tag triggers another test run and creates a **draft** GitHub Release with ZIP, tarball and SHA-256 checksums; publish the draft after review. Never rewrite a published tag. See [CONTRIBUTING.md](CONTRIBUTING.md).

每次修改应先通过 GitHub Actions，再创建版本 tag。更新 `VERSION`、`CHANGELOG.md` 和对应发布说明后提交，创建如 `v0.1.1` 的 tag。tag 会触发复测并自动创建包含 ZIP、tarball、SHA-256 校验值的 **Release 草稿**，审阅后再发布。不要重写已发布的 tag。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。
