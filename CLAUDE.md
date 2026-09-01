# CLAUDE.md

Claude Code 在此仓库中的行为指南。

## 仓库用途

这是 weiliang 的个人开发工具库，包含：
- **skills/** — Claude Code skill 文件，可通过 `/skill-name` 调用
- **packages/** — 可复用的小插件和工具包
- **scripts/** — 自动化脚本
- **workflows/** — 工作流定义

## 约定

- Skill 文件用 Markdown，放在 `skills/` 目录，文件名即调用名
- 脚本优先用 PowerShell（Windows 环境），跨平台脚本用 bash
- 文档放 `docs/`，更新 `CATALOG.md` 以保持索引同步

## 开发原则

- 保持每个 skill/plugin 职责单一
- 新增内容必须更新 CATALOG.md
