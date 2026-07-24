# 公众号排版设计与构建系统

## 1. 配色

| theme | 气质 | 主色 | 辅助色 | 深色 |
| --- | --- | --- | --- | --- |
| `tech` | 科技蓝绿 | `#3266F5` | `#31BFA6` | `#142744` |
| `government` | 理性深蓝 | `#2B5F8F` | `#5F87AA` | `#173A59` |
| `education` | 教育蓝暖 | `#3479B8` | `#E6A03C` | `#183F5D` |
| `party` | 庄重红金 | `#AA3028` | `#C4943E` | `#681F1A` |
| `culture` | 文化米棕 | `#96613A` | `#B28A58` | `#4E3B31` |
| `nature` | 自然绿橙 | `#35745A` | `#C07A42` | `#29473B` |
| `business` | 商务蓝金 | `#294765` | `#A68143` | `#172A3D` |
| `editorial` | 编辑黑白 | `#242424` | `#9A5B43` | `#171717` |

配色控制在两种主色加一种强调色以内。主题由文章类型、目的和读者决定，不根据单个关键词机械选择。用户确认后必须写入明确主题或自定义颜色。

## 2. 视觉基线

- 文章最大宽度677px。
- 正文16px，行高1.95–2，字间距0.03–0.04em。
- 主标题30–36px，章节标题20–24px，辅助文字12–14px。
- 正文使用深灰；主题色承担锚点，不承担长正文。
- 深色、浅色、白底区域交替；全文通常2–5个视觉锚点。
- 政务、新闻、商务使用直角或8–14px圆角；科技、活动、教育可使用16–22px；杂志和文化可使用0–16px。
- 同一篇只使用一套主要圆角、边界和阴影语言。
- 小标签、英文眉题、虚线、图标不要同时堆叠。
- 不默认蓝紫渐变，也不默认浅色顶栏＋粗色条＋虚线＋小标签。
- 允许在首屏、金句或核心数据使用1–2处克制渐变；先设置纯色背景，确保微信清洗后仍可读。
- UI感来自索引、信息分区、状态条、数据面板和稳定对齐，不模拟按钮、输入框或其他不可交互控件。

## 3. 版式参数

支持的 `layout`：

- `briefing`
- `minimal-news`
- `tech-brand`
- `business-report`
- `event-story`
- `education-warm`
- `editorial`
- `culture-story`

支持的 `scene`：

- `official-briefing`
- `news-release`
- `party-study`
- `product-launch`
- `event-recruitment`
- `event-recap`
- `strategic-cooperation`
- `education-research`
- `policy-explainer`
- `people-story`
- `lifestyle-event`
- `culture-journey`
- `general`

密度：

- `light`：1类重点模块，正文和图片为主。
- `balanced`：2–3类重点模块，默认。
- `rich`：3–5类模块，仅用于图片、数据或流程充足的文章。

视觉变体：

- `hero_variant`：`scene-default`、`brand-gradient`、`editorial-light`、`calendar-blocks`、`ui-dashboard`、`split-gradient`
- `section_variant`：`scene-default`、`accent-line`、`editorial-rule`、`label-rule`、`ui-index`、`number-stack`、`gradient-underline`
- `metrics_variant`：`scene-default`、`dark-feature`、`stacked-facts`、`light-grid`
- `steps_variant`：`scene-default`、`rounded-cards`、`schedule-list`、`ticket-list`、`ui-rail`
- `emphasis_variant`：`scene-default`、`gradient-statement`、`editorial-statement`、`ui-notice`
- `points_variant`：`scene-default`、`ui-list`、`index-grid`、`plain-checklist`

用户选择方案后必须显式写入这些参数。`scene-default` 代表使用该场景的成熟默认值，不代表回退到统一模板。

## 4. 模块规则

- `lead`：只使用原稿已有导语或可直接拆出的摘要。
- `section`：标题通常控制在8–16个汉字；允许忠实提炼，不增加新事实。
- `subheading`：章节内部小标题，通常6–18个汉字，视觉强度低于 `section`。
- `keyline`：原稿金句或核心价值句，不得编造口号，一篇通常1–3个。
- `callout`：核心摘要或重点判断，一篇通常不超过2个。
- `keypoints`：2–6个同层级要点，使用 `title`＋可选 `text`。
- `metrics`：精确数据或事实，可用深色锚点、堆叠事实条或浅色网格。
- `timeline`：明确时间顺序。
- `steps`：操作、赛程、实施路径或参与指南。
- `features`：功能、能力和并列事项。
- `quote`：只使用原稿明确引语，不虚构说话人。
- `image`：等比例、居中，最大宽度100%；小图不强制放大。
- `caption`：只使用原稿已有或用户确认的客观说明。
- `closing`：只使用原稿支持的结语。

## 5. 构建计划

```json
{
  "title": "文章标题",
  "label": "原稿短标签或适合的栏目眉题",
  "subtitle": "原稿已有或可直接拆出的事实行",
  "theme": "nature",
  "layout": "event-story",
  "scene": "lifestyle-event",
  "density": "balanced",
  "compatibility": "stable",
  "hero_variant": "brand-gradient",
  "section_variant": "accent-line",
  "metrics_variant": "dark-feature",
  "steps_variant": "rounded-cards",
  "emphasis_variant": "gradient-statement",
  "points_variant": "ui-list",
  "colors": {
    "accent": "#46B890",
    "accent2": "#F0A34E",
    "dark": "#162B4A",
    "pale": "#F0F7F3",
    "page_bg": "#EDF2F0"
  },
  "lead": [
    "原稿导语。"
  ],
  "blocks": [
    {
      "type": "section",
      "label": "MUSIC IN THE PARK",
      "title": "简洁章节标题"
    },
    {
      "type": "paragraph",
      "text": "正文段落。"
    },
    {
      "type": "subheading",
      "title": "章节内的小标题"
    },
    {
      "type": "keyline",
      "label": "核心观点",
      "text": "来自原稿的金句。"
    },
    {
      "type": "keypoints",
      "label": "关键要点",
      "items": [
        {"title": "要点标题", "text": "对应原稿内容"}
      ]
    },
    {
      "type": "metrics",
      "items": [
        {"value": "15场", "label": "高品质户外音乐盛宴"}
      ]
    },
    {
      "type": "steps",
      "items": [
        {"title": "演出地点", "text": "原稿地点"}
      ]
    }
  ],
  "output": {
    "directory": "/absolute/output/directory",
    "stem": "文章标题_公众号排版"
  }
}
```

## 6. 微信兼容

- 正文只使用行内 `style`。
- 不使用外链CSS、网络字体、CSS变量、伪元素、动画、背景图片或CSS Grid。
- 渐变只用于少数首屏、金句或结尾，并同时设置纯色回退。
- 富文本版按钮只复制 `wechat-article`。
- 纯净版不得包含脚本。
- 图片宽度不超过100%，保持 `height:auto`。

## 7. 一次性验收

- 标题、正文、数据、网址和图片完整，无虚构信息。
- 标题、金句、要点和段落层级识别准确；首屏有明确第一视觉，深浅节奏成立。
- 不存在三处以上无意义虚线、小标签堆叠、混杂圆角或每段卡片化。
- 最终版式与所选场景和变体一致，不是只换颜色。
- 两份HTML各只有一个 `wechat-article`；富文本版有复制按钮，纯净版无脚本；无外链样式和明显横向溢出。
