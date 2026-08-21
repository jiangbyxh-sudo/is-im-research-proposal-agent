# C 端 Web 应用 UI / UX 设计规范
## Style: Warm Premium Consumer Web App

> 适用对象：AI Coding Agent、前端工程师、UI 设计师  
> 适用产品：面向 C 端用户的 Web 应用、会员产品、健康 / 教育 / 生活方式 / AI 助手 / 效率工具  
> 设计方向：暖白、杏橙、轻盈、高级、友好、可信、低压力  
> 重要：这是 **登录后的 Web App 规范**，不是营销 Landing Page，也不是企业后台。

---

# 1. 产品体验目标

用户进入 Web App 后应该感受到：

- **轻松**：界面不压迫，不像企业后台。
- **清晰**：信息层级明确，一眼知道下一步做什么。
- **温暖**：暖白背景、杏橙主色、低饱和辅助色。
- **高级**：留白充足、排版克制、阴影极轻、动效细腻。
- **个人化**：强调“我的进度 / 我的计划 / 我的内容”，而不是系统管理。
- **有陪伴感**：文案自然、鼓励式，不机械。

视觉上应更接近：

```text
Calm / Headspace / Apple Health / Notion Consumer
现代生活方式 Web App
精品订阅型消费者产品
```

而不是：

```text
ERP
CRM
BI Dashboard
Ant Design Admin
AWS Console
复杂企业 SaaS 后台
```

---

# 2. 核心视觉语言

```yaml
visual_language:
  tone:
    - warm
    - premium
    - consumer
    - calm
    - friendly
    - trustworthy
    - spacious
    - personal

  avoid:
    - enterprise_dashboard
    - dense_tables
    - dark_neon
    - cyberpunk
    - excessive_glassmorphism
    - heavy_blue_theme
    - developer_console
```

一句话定义：

> **一个看起来像高品质生活方式产品，而不是“管理系统”的 Web 应用。**

---

# 3. Desktop-first 页面框架

推荐主结构：

```text
┌──────────────────────────────────────────────────────────────┐
│ Top Bar                                                      │
├──────────────┬───────────────────────────────────────────────┤
│              │                                               │
│ Sidebar      │ Main Content                                  │
│              │                                               │
│              │                                               │
│              │                                               │
└──────────────┴───────────────────────────────────────────────┘
```

但注意：

**Sidebar 必须轻量化。**

不要做成传统后台那种：

```text
20 个菜单
二级树形菜单
大量分组
图标 + 文本 + 箭头 + Badge
```

推荐最多：

```text
首页
计划
进度
发现
收藏
```

底部：

```text
设置
帮助
用户头像
```

---

# 4. Layout Tokens

## Desktop

```yaml
layout:
  viewport:
    min_width: 1024px

  sidebar:
    width: 220px
    collapsed_width: 72px

  topbar:
    height: 72px

  content:
    max_width: 1320px
    padding_x: 32px
    padding_y: 32px

  page_gap: 24px
```

## Large Desktop

```text
1440–1920px
```

主内容不要无限拉宽。

建议：

```css
.main-content {
  max-width: 1320px;
  margin: 0 auto;
}
```

---

# 5. Color Tokens

```json
{
  "colors": {
    "app_background": "#FBF8F5",
    "page_background": "#FFFDFC",
    "surface": "#FFFFFF",
    "surface_warm": "#FFF6F0",

    "text_primary": "#181614",
    "text_secondary": "#625C57",
    "text_muted": "#96908A",

    "primary": "#F47A4A",
    "primary_hover": "#E96B3A",
    "primary_active": "#D85E31",
    "primary_soft": "#FFE9DD",

    "accent_peach": "#FFDCCB",
    "accent_green": "#A9D7B0",
    "accent_purple": "#C5B7EA",
    "accent_yellow": "#F1CB72",

    "border": "#ECE5E0",
    "border_strong": "#DDD4CD",

    "success": "#4FAE72",
    "warning": "#E5A143",
    "error": "#DF6464",
    "info": "#7189C7"
  }
}
```

规则：

- App Shell 背景：`#FBF8F5`
- 内容卡片：白色
- 大面积纯橙禁止
- 蓝色不作为默认品牌主色
- 所有辅助色都降低饱和度
- 内容区依靠留白和层级，而不是颜色堆叠

---

# 6. Typography

## Font

中文：

```text
PingFang SC
HarmonyOS Sans SC
Noto Sans SC
```

英文：

```text
Inter
SF Pro Text
```

推荐：

```css
font-family:
Inter,
"PingFang SC",
"HarmonyOS Sans SC",
"Noto Sans SC",
sans-serif;
```

## Scale

```yaml
page_title:
  size: 30-34px
  weight: 650
  line_height: 1.25

section_title:
  size: 20-24px
  weight: 600

card_title:
  size: 16-18px
  weight: 600

body:
  size: 15-16px
  line_height: 1.7

caption:
  size: 13px
  line_height: 1.5
```

不要在 Web App 里使用 Landing Page 那种 60px Hero 标题。

---

# 7. Radius / Border / Shadow

```json
{
  "radius": {
    "xs": "8px",
    "sm": "12px",
    "md": "16px",
    "lg": "20px",
    "xl": "24px",
    "pill": "999px"
  }
}
```

默认 Card：

```css
border: 1px solid #ECE5E0;
border-radius: 18px;
background: #FFFFFF;
box-shadow: 0 6px 24px rgba(68, 45, 30, 0.045);
```

悬停：

```css
box-shadow: 0 10px 32px rgba(68, 45, 30, 0.07);
transform: translateY(-1px);
```

禁止：

```text
重阴影
硬黑阴影
过度浮层
所有元素都 Card 化
```

---

# 8. App Shell

## 8.1 Sidebar

视觉：

```text
暖白 / 半透明暖白
无明显阴影
右侧 1px 边界
```

结构：

```text
Logo

首页
计划
进度
发现
收藏

────────

设置
帮助

Avatar + Name
```

选中状态：

```css
background: #FFF0E7;
color: #D96034;
border-radius: 12px;
```

禁止使用：

```text
整块高饱和橙色选中
纯蓝选中
厚重图标
```

---

# 9. Top Bar

建议：

```text
左：页面标题 / Breadcrumb（最多一级）
右：搜索 / 消息 / 用户头像 / Primary Action
```

示例：

```text
我的计划                         搜索   通知   + 新建计划   头像
```

Top Bar 尽量稳定，不要频繁变化。

---

# 10. 首页 Dashboard

这里虽然叫 Dashboard，但必须是 **Consumer Dashboard**。

布局建议：

```text
Greeting
Today's Main Action

Progress Summary
Recommended / Continue

Recent Activity
Insight / Motivation
```

示例：

```text
晚上好，小林
今天也完成一点点就很好。

[继续今天的计划]

┌ 今日进度 ─────────────┐
│ 4 / 6                 │
│ ████████░░            │
└───────────────────────┘

┌ 最近计划 ┐  ┌ 连续记录 ┐
│ 阅读      │  │ 12 天     │
└──────────┘  └───────────┘
```

首页不要出现：

```text
Revenue
MAU
Conversion Rate
System Health
API Usage
```

除非这些就是用户本人的消费数据。

---

# 11. Main Action Card

每页应该有一个最主要行为。

例如：

```text
继续学习
开始今天的训练
继续上次任务
完成今日计划
生成我的方案
```

主操作卡片可以使用浅杏色背景：

```css
background:
linear-gradient(135deg, #FFF6F0, #FFF0E5);
```

不要使用纯橙整屏背景。

---

# 12. Web App Card Types

允许的核心 Card 类型：

```text
Progress Card
Content Card
Recommendation Card
Plan Card
Insight Card
Activity Card
Profile Card
Subscription Card
```

禁止到处使用：

```text
KPI Card
Data Metric Tile
Admin Stat Card
```

除非数据对 C 端用户真的有价值。

---

# 13. Progress Card

推荐结构：

```text
Title
Primary Number
Progress Visualization
Friendly Insight
CTA
```

例：

```text
本周进度

72%

██████████████░░░░

比上周多完成了 2 次

查看详情 →
```

不要：

```text
+14.29%
QoQ
Benchmark
Variance
```

这种企业数据表达。

---

# 14. 数据可视化

C 端数据图表必须简单。

推荐：

```text
Line Chart
Progress Ring
7-day Bar Chart
Calendar Heatmap
Streak
```

单张卡片最多：

```text
1 个主要图表
1 个核心数字
1 条洞察
```

禁止：

```text
6 个指标
Dual Axis
复杂 Legend
Dense Scatter Plot
```

图表颜色：

```text
Primary Orange
Soft Green
Muted Purple
Warm Gray
```

---

# 15. Empty State

必须设计 Empty State。

结构：

```text
简单插图 / Icon
一句解释
一个 CTA
```

示例：

```text
还没有计划

从一个小目标开始，
你的第一步不需要很大。

[创建第一个计划]
```

不要：

```text
暂无数据
No Data
```

直接丢给消费者。

---

# 16. Forms

C 端表单要短。

原则：

```text
单页 ≤ 6 个输入项
能选择就不要输入
能推断就不要询问
```

Input：

```css
height: 46px;
border-radius: 12px;
border: 1px solid #E6DED8;
background: #FFFFFF;
```

Focus：

```css
border-color: #F47A4A;
box-shadow: 0 0 0 3px rgba(244,122,74,.12);
```

---

# 17. Buttons

## Primary

```css
height: 46px;
padding: 0 20px;
border-radius: 12px;
background: #F47A4A;
color: #FFFFFF;
font-weight: 600;
```

## Secondary

```css
background: #FFFFFF;
border: 1px solid #E4DCD6;
color: #322D29;
```

## Ghost

```css
background: transparent;
color: #625C57;
```

每个页面最多一个视觉权重最高的 Primary CTA。

---

# 18. Modal / Drawer

C 端优先使用：

```text
Modal：确认 / 简短编辑
Right Drawer：复杂设置 / 详情
```

Modal：

```text
width: 480–560px
radius: 20px
```

避免传统后台式超大 Modal。

---

# 19. Search

搜索建议使用：

```text
Command Palette
Top Search
Inline Search
```

Placeholder：

```text
搜索计划、内容或记录
```

不要：

```text
请输入关键词
```

尽量自然。

---

# 20. Notification

通知语气：

正确：

```text
今天的计划还有 1 项未完成
你已经连续坚持 7 天了
新的推荐内容已准备好
```

错误：

```text
Task ID #49283 finished
System notification
Operation success
```

---

# 21. Consumer Copy Rules

所有产品文案都遵循：

```text
用户语言 > 系统语言
结果 > 功能
鼓励 > 命令
自然 > 正式
```

正确：

```text
继续今天的计划
看看你的进步
为你推荐
稍后再做
```

错误：

```text
执行任务
查看数据详情
系统推荐
取消操作
```

---

# 22. 推荐的核心 Web 页面

建议至少设计：

```text
/
首页

/plans
我的计划

/progress
进度

/discover
发现

/favorites
收藏

/profile
个人中心

/settings
设置

/subscription
会员
```

---

# 23. 首页具体结构

```text
Page Header

Greeting + Main CTA

Today's Progress

Current Plans

Recommended For You

Recent Progress

Motivation / Insight
```

布局：

```text
12-column grid
```

示例：

```text
┌──────────────────── 8 cols ─────────────────┬─ 4 cols ──────┐
│ Today's Plan                                │ Streak         │
├─────────────────────────────────────────────┼────────────────┤
│ Continue                                    │ Weekly Insight │
├─────────────────────────────────────────────┴────────────────┤
│ Recommendations                                              │
└──────────────────────────────────────────────────────────────┘
```

---

# 24. 内容列表页

不要默认用后台表格。

优先：

```text
Card Grid
Compact List
Feed
```

例如：

```text
我的计划

[全部] [进行中] [已完成]

┌──────────┐
│ 阅读计划 │
│ 12 / 30  │
│ █████░░  │
└──────────┘
```

只有以下场景才用 Table：

```text
账单
交易
大量结构化历史记录
```

---

# 25. Detail Page

详情页建议：

```text
Back
Title
Status / Meta

Main Content

Progress / Activity

Related Content

Primary Action
```

不要做 6 个 Tab。

推荐最多：

```text
概览
记录
```

---

# 26. Subscription Page

会员页仍然保持 C 端风格。

结构：

```text
Current Plan
Benefits
Upgrade CTA
Billing History
```

重点：

```text
你会得到什么
```

而不是：

```text
SKU
License
Seat
Workspace
```

---

# 27. Responsive Breakpoints

```yaml
breakpoints:
  mobile: "< 768px"
  tablet: "768-1023px"
  desktop: "1024-1439px"
  large: ">= 1440px"
```

Mobile：

```text
Sidebar → Bottom Nav / Drawer
Top Bar 精简
Card 单列
主要操作置底或全宽
```

Tablet：

```text
Sidebar 可折叠
2-column cards
```

Desktop：

```text
完整 Sidebar
2–3 column grid
```

---

# 28. Bottom Navigation (Mobile Web)

移动端建议：

```text
首页
计划
发现
进度
我的
```

最多 5 项。

高度：

```text
64–72px
```

---

# 29. Motion

允许：

```text
hover lift 1px
fade 180–240ms
drawer 240ms
progress animation
micro celebration
```

成功行为可以用：

```text
小型 confetti
check animation
progress ring animation
```

不要：

```text
大面积粒子
持续漂浮
复杂 3D
强 parallax
```

---

# 30. Accessibility

必须：

```text
WCAG AA
Keyboard navigation
Visible focus
aria-label
44px touch target
Reduced motion
Semantic headings
```

---

# 31. React / Next.js 推荐结构

```text
src/
  app/
    (app)/
      layout.tsx
      page.tsx

      plans/
        page.tsx

      progress/
        page.tsx

      discover/
        page.tsx

      favorites/
        page.tsx

      settings/
        page.tsx

  components/
    app-shell/
      Sidebar.tsx
      Topbar.tsx
      MobileNav.tsx

    dashboard/
      Greeting.tsx
      TodayPlan.tsx
      ProgressSummary.tsx
      RecommendationGrid.tsx
      RecentActivity.tsx

    plans/
      PlanCard.tsx
      PlanProgress.tsx

    progress/
      ProgressRing.tsx
      WeeklyChart.tsx
      StreakCard.tsx

    common/
      EmptyState.tsx
      PageHeader.tsx

    ui/
      Button.tsx
      Card.tsx
      Badge.tsx
      Avatar.tsx
      Input.tsx
      Modal.tsx

  styles/
    tokens.css
    globals.css
```

---

# 32. CSS Variables

```css
:root {
  --app-bg: #FBF8F5;
  --page-bg: #FFFDFC;
  --surface: #FFFFFF;

  --text-primary: #181614;
  --text-secondary: #625C57;
  --text-muted: #96908A;

  --brand-500: #F47A4A;
  --brand-600: #E96B3A;
  --brand-soft: #FFE9DD;

  --border: #ECE5E0;

  --radius-sm: 12px;
  --radius-md: 16px;
  --radius-lg: 20px;

  --shadow-card:
    0 6px 24px rgba(68, 45, 30, 0.045);
}
```

---

# 33. Tailwind Mapping

```js
theme: {
  extend: {
    colors: {
      app: "#FBF8F5",
      surface: "#FFFFFF",

      ink: {
        900: "#181614",
        700: "#625C57",
        500: "#96908A",
      },

      brand: {
        50: "#FFF6F0",
        100: "#FFE9DD",
        500: "#F47A4A",
        600: "#E96B3A",
      }
    },

    borderRadius: {
      card: "18px",
      control: "12px",
    }
  }
}
```

---

# 34. Agent Build Prompt

以下可以直接给代码 Agent：

```text
Build a production-quality consumer-facing Web App UI.

This is NOT a landing page and NOT an enterprise admin dashboard.

The product should feel like a premium lifestyle subscription web application.

Visual direction:
- warm off-white app background
- white surfaces
- coral/orange brand color
- subtle peach gradients
- generous whitespace
- rounded 16–20px cards
- very soft shadows
- clean typography
- restrained use of icons
- calm and friendly interaction design

Desktop-first application shell:
- 220px lightweight sidebar
- 72px top bar
- max content width 1320px
- responsive layout

Primary navigation:
- 首页
- 计划
- 进度
- 发现
- 收藏
- 设置

Homepage must include:
1. Personal greeting
2. One clear primary action
3. Today's progress
4. Current plans
5. Recommendations
6. Weekly progress / streak
7. Recent activity

Do not create:
- enterprise KPI tiles
- revenue charts
- dense data tables
- nested admin menus
- blue enterprise SaaS styling
- neon gradients
- cyberpunk visuals
- code console aesthetics

Use consumer-friendly language.
Prefer cards, feeds and progress visuals over tables.

Make the UI responsive:
- desktop sidebar
- tablet collapsible sidebar
- mobile bottom navigation

Accessibility:
- WCAG AA
- keyboard navigation
- visible focus
- reduced-motion support

The final UI should feel calm, personal, premium and easy to use.
```

---

# 35. Agent 验收标准

```yaml
acceptance_criteria:

  shell:
    - desktop_has_lightweight_sidebar
    - topbar_height_around_72px
    - content_width_is_constrained
    - mobile_navigation_exists

  visual:
    - warm_off_white_background
    - coral_orange_primary
    - white_surface_cards
    - no_heavy_blue_theme
    - no_neon
    - subtle_shadow_only
    - card_radius_between_16_and_20px

  consumer_experience:
    - personal_greeting_present
    - clear_primary_action
    - user_progress_visible
    - recommendations_present
    - no_enterprise_kpi_language
    - no_admin_dashboard_feel

  information_density:
    - no_dense_table_on_home
    - no_more_than_5_primary_nav_items
    - max_1_primary_cta_per_view
    - charts_are_simple

  interaction:
    - button_min_height_44px
    - focus_states_visible
    - loading_states_present
    - empty_states_present
    - error_states_are_human_friendly

  responsive:
    - sidebar_collapses_on_tablet
    - mobile_uses_single_column
    - mobile_has_bottom_navigation

  accessibility:
    - wcag_aa
    - semantic_html
    - keyboard_navigation
    - aria_labels
    - reduced_motion
```

---

# 36. 最终设计判断

如果最终页面第一眼像：

```text
一个漂亮的个人健康 / 学习 / AI 助手 Web App
```

就是正确的。

如果第一眼像：

```text
公司内部运营后台
```

就是错误的。

最终视觉原则：

> **Personal Product, not Business Software.**

> **Warm, calm, premium, and clear.**

> **让用户感觉自己在使用一个属于自己的产品，而不是操作一套系统。**
