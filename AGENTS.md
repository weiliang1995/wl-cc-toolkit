# AGENTS.md

AI agent 使用指南（适用于 Claude Code、Copilot 等）。

## Skills 使用

Skills 位于 `skills/` 目录。在 Claude Code 中通过以下方式调用：

```
/skill-name
```

或在对话中直接描述任务，Claude 会自动匹配相关 skill。

## 目录索引

所有可用工具见 [CATALOG.md](CATALOG.md)。

## 注意事项

- 修改或新增 skill 后，同步更新 CATALOG.md
- Skill 文件遵循 Claude Code skill 格式（frontmatter + 正文）
