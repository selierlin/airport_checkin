# Airport Checkin

多机场账号自动签到与信息查询工具。

## 安装

先安装 [uv](https://docs.astral.sh/uv/)（Python 包管理工具）：

```bash
# macOS（推荐）
brew install uv

# Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

然后安装依赖：

```bash
uv sync
```

## 配置

复制模板并填写你的机场账号信息：

```bash
cp config-template.json config.json
```

编辑 `config.json`：

```json
{
  "accounts": [
    {
      "name": "我的机场",
      "panel": "v2board",
      "base_url": "https://example.com",
      "api_prefix": "/api/v1",
      "email": "your@email.com",
      "password": "your_password",
      "auth_token": "",
      "proxy": "http://127.0.0.1:7890"
    }
  ],
  "notify": {
    "enabled": false,
    "qywx_key": "YOUR_QYWX_ROBOT_KEY"
  }
}
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `name` | 账号显示名称 |
| `panel` | 面板类型，目前支持 `v2board` |
| `base_url` | 机场站点地址 |
| `api_prefix` | API 路径前缀，标准 V2Board 为 `/api/v1`，部分定制版可能不同 |
| `email` | 登录邮箱 |
| `password` | 登录密码 |
| `auth_token` | JWT token（可选，填写后优先使用，无需邮箱密码） |
| `proxy` | 代理地址（可选，留空则直连） |

可以配置多个账号，会依次执行。

## 使用

```bash
uv run python main.py
```

输出示例：

```
【飞鸟云】
  登录成功
  余额: ¥0.00
  佣金余额: ¥131.19
  已用流量: 16.4% (33.1GB / 201.9GB)
  到期时间: 无限期
```

## 定时运行

### macOS / Linux（crontab）

```bash
crontab -e
```

添加：

```
0 8 * * * cd /path/to/airport_checkin && uv run python main.py
```

### Windows（任务计划程序）

```
schtasks /create /tn "airport_checkin" /tr "cmd /c cd C:\path\to\airport_checkin && uv run python main.py" /sc daily /st 08:00
```

## 企业微信通知

在 `config.json` 中启用：

```json
"notify": {
  "enabled": true,
  "qywx_key": "你的企业微信机器人key"
}
```

## 支持的面板

| 面板类型 | 说明 |
|---------|------|
| `v2board` | V2Board 及其兼容面板 |
| `sspanel` | SSPanel（极客云等） |
| `bygcloud` | 白月光 |
| `wmsxwd` | 我們所嚮往的（SSPanel Metron 主题） |
| `fatcatcf` | 肥猫云（FatcatCF 面板） |
