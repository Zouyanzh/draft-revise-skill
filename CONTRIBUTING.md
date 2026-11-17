# Maintaining the Codex skill / 维护 Codex skill

Edit the repository's `draft-revise/` directory, not a separate installed copy. Keep task-specific manuscripts, reviewer comments and generated feedback out of this public repository. Tests use synthetic fixtures. Skill edits do not authorize publishing; publish only when the maintainer requests a release.

请修改仓库中的 `draft-revise/`，以它作为唯一开发源。个人论文、导师批注、生成的反馈文件留在各自项目目录，公开测试使用合成文档。修改 skill 本身不代表授权发布，只有维护者要求发版时才执行发布。

## Development / 开发

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
npm ci --ignore-scripts
python tools/check_skill.py
python draft-revise/scripts/selftest.py --output test-output
node draft-revise/scripts/review_ui_test.cjs test-output/report/report_revised_v1.html test-output/report-feedback.json
python draft-revise/scripts/draft_revise.py feedback test-output/report/report_revised_v1.json test-output/report-feedback.json
node draft-revise/scripts/review_ui_test.cjs test-output/slides/slides_revised_v1.html test-output/slides-feedback.json --file
python tools/build_release.py
```

Use a fresh empty output directory when rerunning `selftest.py`, or omit `--output` to use a temporary directory. DOM tests supplement actual browser inspection: inspect desktop and narrow views whenever layout changes.

重跑 `selftest.py` 时使用新的空输出目录，或省略 `--output` 使用临时目录。DOM 测试不能代替实际浏览器检查，涉及布局时应检查桌面和窄屏。

## Install local changes / 同步本地安装

```sh
python tools/install_local.py
```

The default target is `$CODEX_HOME/skills/draft-revise`, falling back to `~/.codex/skills/draft-revise`. `--dest` overrides it. Existing content is backed up next to the skills directory; `.release.json` records version, source repository path, commit and whether local changes existed. A dirty install is explicitly labeled and is not an immutable release.

默认目标为 `$CODEX_HOME/skills/draft-revise`，未设置时为 `~/.codex/skills/draft-revise`，可通过 `--dest` 覆盖。已有内容会备份到 skills 目录旁；`.release.json` 记录版本、源仓库位置、commit 和是否存在未提交修改。含未提交修改的安装会明确标记。

## Release / 发布

1. Update `VERSION`, `CHANGELOG.md` and `docs/releases/vX.Y.Z.md`; keep English and Chinese notes aligned. Update pinned installation examples in both README sections. Feedback schema, ledger schema and release versions are independent.
2. Pass local checks, commit and push `main`; wait for **Test Codex skill** to succeed.
3. Create an annotated tag and push it. Published tags must never be moved.
4. The release workflow runs the tests again, verifies tag versus `VERSION`, builds deterministic archives and creates a **draft** release.
5. Review the draft, publish it, then install that commit locally if desired.

1. 同步更新 `VERSION`、`CHANGELOG.md`、`docs/releases/vX.Y.Z.md` 和 README 中英文安装版本。
2. 本地检查后提交、推送 `main`，等待 **Test Codex skill** 通过。
3. 创建附注 tag 并推送，已发布 tag 不得移动。
4. 工作流复测、核对 tag 和 `VERSION`、构建可复现压缩包，创建 **Release 草稿**。
5. 审阅后发布，需要时将对应 commit 安装到本机。

```sh
git tag -a v0.1.1 -m 'Release v0.1.1'
git push origin v0.1.1
gh release view v0.1.1
gh release edit v0.1.1 --draft=false --latest
```

The commands above illustrate a future release after updating its version files. Use the actual version being released.

上面的命令是后续发版示例，执行前应完成版本文件更新，并使用实际版本号。
