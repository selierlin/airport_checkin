import requests
from urllib.parse import urlparse
from .base import BasePanel


class V2Board(BasePanel):
    """V2Board 面板实现"""

    def __init__(self, account: dict):
        super().__init__(account)
        self.cf_clearance = account.get("cf_clearance")

        if self.cf_clearance:
            from curl_cffi import requests as cf_requests
            self.session = cf_requests.Session(impersonate="chrome")
            domain = urlparse(self.base_url).hostname
            self.session.cookies.set("cf_clearance", self.cf_clearance, domain=domain)
        else:
            self.session = requests.Session()

        if self._proxies():
            if hasattr(self.session.proxies, "update"):
                self.session.proxies.update(self._proxies())
            else:
                self.session.proxies = self._proxies()

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.base_url + "/",
            "Origin": self.base_url,
        }
        if not self.cf_clearance:
            headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.session.headers.update(headers)

    def login(self) -> bool:
        # 优先使用已有 auth_token（JWT）
        if self.auth_token:
            self.session.headers["Authorization"] = self.auth_token
            try:
                resp = self.session.get(self._api_url("/user/info"))
                if resp.status_code == 200 and resp.json().get("data"):
                    return True
            except Exception:
                pass

        if not self.email or not self.password:
            print(f"[{self.name}] 没有配置邮箱密码，且 token 无效")
            return False

        try:
            resp = self.session.post(
                self._api_url("/passport/auth/login"),
                json={"email": self.email, "password": self.password},
            )
            data = resp.json()
            if data.get("data"):
                auth_data = data["data"]
                if isinstance(auth_data, dict):
                    self.token = auth_data.get("auth_data", "")
                else:
                    self.token = str(auth_data)
                self.session.headers["Authorization"] = self.token
                return True
            else:
                print(f"[{self.name}] 登录失败: {data.get('message', '未知错误')}")
                return False
        except Exception as e:
            print(f"[{self.name}] 登录异常: {e}")
            return False

    def checkin(self) -> str:
        try:
            resp = self.session.post(self._api_url("/user/checkin"))
            if resp.status_code == 404:
                return ""
            data = resp.json()
            if data.get("status") == "success" or data.get("data"):
                return data.get("message", "签到成功")
            return data.get("message", "")
        except Exception:
            return ""

    def get_user_info(self) -> dict:
        result = {}
        try:
            resp = self.session.get(self._api_url("/user/info"))
            data = resp.json().get("data", {})
            if not data:
                return result

            # 余额（单位：分）— 放最前
            result["余额"] = "¥{:.2f}".format(data.get("balance", 0) / 100)

            # 流量 — 从 /user/getSubscribe 获取（/user/info 里没有 u/d）
            self._fill_traffic_info(result, data.get("transfer_enable", 0))

            # 到期时间
            expired_at = data.get("expired_at")
            if expired_at and expired_at > 0:
                from datetime import datetime
                result["到期时间"] = datetime.fromtimestamp(expired_at).strftime("%Y-%m-%d")
            else:
                result["到期时间"] = "无限期"

            # 佣金比例
            rate = data.get("commission_rate")
            if rate is not None:
                result["佣金比例"] = "{}%".format(rate)

            # 邀请/注册数据 — 从 /user/invite/fetch 获取
            self._fill_invite_info(result)

            # 佣金余额 — 放最后
            result["佣金余额"] = "¥{:.2f}".format(data.get("commission_balance", 0) / 100)

            # 总佣金 — 放最后
            self._fill_commission_info(result)

        except Exception as e:
            print(f"[{self.name}] 获取用户信息失败: {e}")

        return result

    def _fill_traffic_info(self, result: dict, fallback_transfer: int):
        """从 /user/getSubscribe 获取真实流量数据"""
        try:
            resp = self.session.get(self._api_url("/user/getSubscribe"))
            data = resp.json().get("data", {})
            u = data.get("u", 0)
            d = data.get("d", 0)
            transfer_enable = data.get("transfer_enable", fallback_transfer)
            used = u + d
        except Exception:
            used = 0
            transfer_enable = fallback_transfer

        if transfer_enable > 0:
            from utils import format_bytes
            pct = used / transfer_enable * 100
            result["已用流量"] = "{:.1f}% ({} / {})".format(pct, format_bytes(used), format_bytes(transfer_enable))
        else:
            result["已用流量"] = "无限制"

    def _fill_invite_info(self, result: dict):
        """从 /user/invite/fetch 获取邀请注册数据"""
        try:
            resp = self.session.get(self._api_url("/user/invite/fetch"))
            data = resp.json().get("data", {})
            stat = data.get("stat", [])
            # stat: [已注册人数, 总佣金(分), 待确认佣金, 可提现佣金?, 佣金余额(分)]
            if stat and len(stat) >= 1:
                result["已注册人数"] = str(stat[0])
        except Exception:
            pass

    def _fill_commission_info(self, result: dict):
        """从 /user/invite/fetch 获取总佣金"""
        try:
            resp = self.session.get(self._api_url("/user/invite/fetch"))
            data = resp.json().get("data", {})
            stat = data.get("stat", [])
            if stat and len(stat) >= 2:
                result["总佣金"] = "¥{:.2f}".format(stat[1] / 100)
        except Exception:
            pass
