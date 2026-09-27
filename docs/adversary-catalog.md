# 敌人数据卡片

唯一入口是 `/SRD/adversaries-and-environments/adversary-data/`，即原规则章节。
旧 `/SRD/adversaries/` 仅用于兼容跳转，不出现在目录或搜索中。
中文正文是规则依据，英文仅作参考。

## 在 editor 中编辑

从该页侧栏点击「管理员编辑」，继续编辑原来的 `zh.md` / `en.md`。
每个敌人用下面的标记包围；内容仍然是普通 Markdown：

```markdown
<!-- adversary: my-adversary | English reference name -->

#### 敌人名称 {#existing-name-anchor}

##### *位阶 **1** 标准* {#existing-role-anchor}

*外观描述。*  
**动机与战术：** 保护、巡逻  
**难度：** 12 | **阈值：** 8/14 | **生命点：** 5 | **压力点：** 3  
**攻击：** +1 | **匕首：** 近战 | 1d8+1 物理

#### **特性** {#existing-features-anchor}

- *特性名称 - 被动：* 普通 Markdown 能力说明。

<!-- /adversary -->
```

开始标记中的英文 ID 用于条目链接及双语配对，已有 ID 不要修改。
竖线后是英文参考名称，用于双语全文搜索。开始与结束标记必须成对且不能嵌套。
名称、位阶、类型、难度、阈值、生命点、压力点、攻击、经历与全部能力均从正文渲染。
新增中文敌人无需再维护 JSON 映射；英文可后续以相同 ID 补充。
历史标题锚点保留以兼容旧链接；新增标题的锚点应全页唯一，两种语言的标题锚点独立，按卡片 ID 配对。

`static/js/adversary-core.mjs` 是 editor 与正式构建共用的卡片渲染器，
通过 Render Core 调用；预览和发布呈现相同卡片结构。
`scripts/adversary_catalog.py` 仅将两种语言按 ID 组合、依中文位阶分组，并生成筛选属性与搜索记录。
删除了独立名称映射文件，规则只需维护原 Markdown。
目前为 139 个中文条目、129 个英文条目；英文缺失时显示中文并提示。

默认完整卡片，完整／紧凑通过滑动开关切换；内容区最大宽度 100rem、居中显示；卡片固定 26rem，空间足够时每行三张，窄屏自动减列，搜索结果保留卡片宽度。支持紧凑卡片、全文搜索、位阶/类型筛选；按正文顺序排列。
位阶与类型支持多选：同组为“或”，不同组为“且”。`tier` 和 `type` 用逗号保存多项。
紧凑条目右侧显示中文规则的难度、阈值、生命点和压力点；悬停或聚焦名称显示完整卡片，Escape 可关闭，手机点击名称展开完整视图。
名称本身是条目链接，不另设链接行。
查询参数 `q`、`tier`、`type`、`view` 保存条件；`#adversary-ID` 定位卡片。
没有 JavaScript 也能阅读全部卡片。

验证命令：

```text
python scripts/build_srd.py
python -m pytest tests/test_adversary_catalog.py
npx playwright test tests/browser/adversaries.spec.mjs --workers=2
```

卡片视觉参考 PbDH 的敌人／环境文字模板：深色标题栏、骨白底、酒红攻击条、分块特性。生命和压力格仅静态展示。工具栏为单行，下拉多选保留组合条件；窄屏可横向滚动工具栏。
本地 preview_server 默认免登录，仅绑定 127.0.0.1；需要验证认证时仍可显式设置 --admin-password。

全文筛选同时匹配两种语言的名称、简介、数值、动机、经历及特性。术语检测仅用于特性说明，名称与类型标签、简介、数值和攻击等不检测。

搜索按完整短语匹配，忽略空格、换行、大小写和全半角差异；不再把空格分隔的词分别匹配。命中处在完整卡片、紧凑条目及悬浮预览中高亮，清空搜索会移除高亮。
