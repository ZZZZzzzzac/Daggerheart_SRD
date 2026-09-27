# 环境数据卡片

原入口 `/SRD/adversaries-and-environments/environment-data/` 直接呈现环境卡片。
正文仍来自 `src/pages/adversaries-and-environments/environment-data/{zh,en}.md`。
19 个中文环境均有英文参考。双语配对只依赖正文中的稳定 ID；构建不依赖外部翻译仓库。

```markdown
<!-- environment: raging-river | Raging River -->

#### 汹涌河流 {#原有标题锚点}

##### *位阶 **1** 险境* {#原有类型锚点}

*简介。*  
**趋向：** 阻隔通行  
**难度：** 10  
**潜在敌人：** 野兽

#### **特性** {#原有特性锚点}

- *暗流 - 动作：* 能力正文。  
*河床上散落着什么？*

<!-- /environment -->
```

示例中的锚点需换成唯一的 ASCII 标识。已有 ID 和锚点保留不变。
`environment-core.mjs` 负责共享渲染，editor 的预览与正式构建使用同一模块。
难度允许“特殊”等非数值说明；不能自动替换为数字。
布局参考 PbDH 环境模板：标题与简介、难度色块、趋向与潜在敌人、特性与引导问题。
术语检测仅用于特性及引导问题正文。

筛选、固定卡宽、全文短语搜索、高亮、完整/紧凑开关、悬浮预览、URL 状态沿用敌人页实现。
环境类型为探索、险境、社交、事件。条目链接为 `#environment-ID`。
环境页纳入首页、侧栏和站内搜索；旧章节锚点继续有效。
