# 探索机场网站 API 并接入面板

你是机场管理工具的 API 探索专家。你的任务是：给一个机场网站，快速找到所有可用 API 接口，并为它编写面板适配代码。

## 输入

用户会提供一个机场网站地址，可能附带账号密码。

## 执行步骤

### 第一步：识别面板类型

1. 用 `mcp__web_reader__webReader` 抓取首页 HTML
2. 从 HTML 中提取线索：
   - `<title>` 标签中的站名
   - JS/CSS 文件路径规律（如 `/static/` vs `/assets/`）
   - 加载的第三方库（FingerprintJS、特定框架等）
3. 常见面板特征对照：
   - **V2Board**: 页面标题通常含机场名，JS 在 `/assets/` 下，URL 用 `/#/` hash 路由
   - **SSPanel-Uim**: 特征路径 `/theme/`，页面结构不同
   - **V2Board 定制版**: 外壳像 V2Board 但 API 路径不同（重点！）
4. **⚠️ 不能仅靠前端外观判断面板类型！** CSS/JS 路径可能误导（如 `/theme/default/assets/umi.css` 看起来像 SSPanel-Uim，但 API 可能是标准 V2Board）。**必须通过实际 API 路径确认面板类型**，前端只是参考。

### 第二步：探测 API 基础路径（关键步骤）

**不要假设 API 路径！** 很多机场的 API 不是标准的 `/api/v1`。

有效方法：
1. 用 cmux-browser 打开网站登录页面
2. 让浏览器填入测试账号并登录，监控网络请求
3. 从实际发出的请求中提取 `base_url + api_prefix`

常见变体：
- 标准 V2Board: `/api/v1`
- 定制 V2Board: `/xq/api/v1`、`/custom/api/v1` 等
- SSPanel: `/api/v1/`、`/user/`
- 其他面板: 完全不同的路径

### 第三步：解决 WAF/CDN 防护

如果直接用 curl/requests 调 API 返回 403：

1. **加上完整浏览器请求头**（最常见的原因）：
   ```
   User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
   Accept: application/json, text/plain, */*
   Accept-Language: zh-CN,zh;q=0.9,en;q=0.8
   Referer: https://<domain>/
   Origin: https://<domain>
   ```
2. 如果还不行，检查是否需要先访问首页获取 cookie
3. 如果有 JS Challenge（如 Cloudflare），可能需要用 cmux-browser 绕过

### 第四步：登录并获取 Auth Token

1. 找到登录接口（通常是 `/passport/auth/login`）
2. 测试登录，分析响应结构
3. **注意 token 的位置**：可能在 `data.auth_data`（JWT）而非直接 `data`
4. **注意 Authorization 格式**：
   - 标准: `Authorization: Bearer <jwt>`
   - 某些定制版: `Authorization: <jwt>`（无 Bearer 前缀）
   - 某些面板: 用 cookie 而非 header

### 第五步：批量探测所有接口

登录成功后，一次性探测所有可能的接口端点。**这是最有效的方法，比用浏览器一页页看快得多。**

用脚本批量请求，记录每个接口的返回数据：
```
/user/info            — 基本信息（余额、套餐等）
/user/getSubscribe    — 流量数据（u/d 字段，注意：不一定在 /user/info 里！）
/user/invite/fetch    — 邀请/注册数据
/user/comm/config     — 佣金配置
/user/plan/fetch      — 套餐列表
/user/checkin         — 签到（可能不存在）
/user/order/fetch     — 订单
/user/server/fetch    — 节点列表
```

### 第六步：编写面板代码

1. 在 `panels/` 目录下创建新文件，继承 `BasePanel`
2. 实现 `login()`、`checkin()`、`get_user_info()` 三个方法
3. 在 `panels/__init__.py` 中注册新面板
4. 在 `config-template.json` 中添加账户配置模板
5. 用真实账号测试验证

## 踩坑经验总结

### 致命误区

1. **不要一直用 cmux 截图死扣一个页面** — 浏览器截图只能看到 UI，看不到 API。如果某页面上看不到目标数据，不要反复刷同一页，应该直接批量探测接口。
2. **不要假设数据都在 /user/info 里** — 流量数据可能在 `/user/getSubscribe`，邀请数据可能在 `/user/invite/fetch`，佣金配置可能在 `/user/comm/config`。不同面板数据分布完全不同。
3. **不要假设 API 路径是标准的** — 定制版面板会改路径前缀。
4. **不要假设认证方式是标准的** — 可能无 Bearer 前缀，可能用 cookie。
5. **签到接口不是标配** — 很多机场不支持签到（`/user/checkin` 返回 404）。探测阶段应先测签到接口是否存在，不存在则面板 `checkin()` 返回空字符串跳过。
6. **不要仅靠前端判断面板类型** — SSPanel-Uim 皮肤可能套在 V2Board API 上，CSS 路径 `/theme/default/` 不代表是 SSPanel 面板。API 路径才是判断依据。

### 正确策略

1. **先用 cmux 登录一次抓真实请求** → 拿到 api_prefix 和认证格式
2. **然后用脚本批量探测接口** → 比浏览器一个个点快 10 倍
3. **数据对不上就换接口** → 不要死磕一个 API，数据大概率在别的端点
4. **参考已有面板实现** → 看 `panels/v2board.py` 的模式
5. **探索结果必须完整转化到代码** → 探索完成后，逐条对照发现编写面板代码，不能遗漏任何有数据的页面或接口。特别是邀请/佣金页面，往往包含邀请人数、累计佣金、可提现佣金等仪表盘上没有的数据。

### 代理使用

- 机场网站通常在境外，需要代理访问
- 在 config.json 中配置 `proxy` 字段
- requests Session 中通过 `proxies` 设置
- 如果用户未明确允许，不要擅自使用代理（遵守 CLAUDE.md 规则）

## 输出要求

探索完成后，提供：
1. 面板类型及 API 基础路径
2. 登录方式及认证格式
3. 可用接口列表及数据字段说明
4. 已编写并通过测试的面板适配代码
