# CONTRIBUTING.md

## 新增 Skill

1. 在 `skills/` 下创建 `<skill-name>.md`
2. 文件顶部加 frontmatter：

```yaml
---
name: skill-name
description: 一句话说明用途和触发时机
---
```

3. 正文写清楚 skill 的步骤或指令
4. 在 [CATALOG.md](CATALOG.md) 的 Skills 表格中添加一行

## 新增 Package / 插件

1. 在 `packages/<package-name>/` 下创建插件目录
2. 包含 `README.md` 说明用途和使用方式
3. 在 [CATALOG.md](CATALOG.md) 的 Packages 表格中添加一行

## 新增 Script

1. 脚本放入 `scripts/`
2. 文件头部注释说明用途、参数、示例
3. 在 [CATALOG.md](CATALOG.md) 的 Scripts 表格中添加一行

## Commit 规范

```
feat: 新增 xxx skill
fix: 修复 xxx 问题
docs: 更新 CATALOG.md
```
