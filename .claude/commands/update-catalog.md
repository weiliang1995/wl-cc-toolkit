---
description: 扫描 skills/、packages/、scripts/ 目录，增量更新 CATALOG.md
---

扫描仓库并增量更新 CATALOG.md，步骤如下：

1. 读取当前 CATALOG.md 内容，记录已有条目（以文件名/目录名为 key）。

2. 扫描 `skills/` 目录：
   - 遍历所有 `.md` 文件（忽略 `.gitkeep`）
   - 读取每个文件的 frontmatter，提取 `name` 和 `description`
   - 若文件不在 CATALOG.md 的 Skills 表格中，追加一行；已有的保持不动
   - 调用方式列为 `/<name>`

3. 扫描 `packages/` 目录：
   - 遍历所有子目录（忽略空目录和 `.gitkeep`）
   - 读取每个子目录的 `README.md` 第一段作为描述（若无则用目录名）
   - 若目录不在 CATALOG.md 的 Packages 表格中，追加一行；已有的保持不动

4. 扫描 `scripts/` 目录：
   - 遍历所有脚本文件（`.ps1`、`.sh`、`.js`、`.ts`，忽略 `.gitkeep`）
   - 读取文件头部注释（前 5 行）提取描述
   - 若文件不在 CATALOG.md 的 Scripts 表格中，追加一行；已有的保持不动

5. 将更新后的内容写回 CATALOG.md，保留已有条目的顺序和手写内容，只在表格末尾追加新行。删除仍存在的 `_(待添加)_` 占位行。

6. 输出本次新增了哪些条目（或"无新增"）。
