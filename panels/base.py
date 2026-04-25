from abc import ABC, abstractmethod


class BasePanel(ABC):
    """机场面板基类，所有面板实现都需要继承此类"""

    def __init__(self, account: dict):
        self.name = account["name"]
        self.base_url = account["base_url"].rstrip("/")
        self.api_prefix = account.get("api_prefix", "/api/v1")
        self.proxy = account.get("proxy")
        self.token = None

        # 登录方式：email+password 或 token
        self.email = account.get("email")
        self.password = account.get("password")
        self.auth_token = account.get("auth_token")

    def _api_url(self, path: str) -> str:
        return f"{self.base_url}{self.api_prefix}{path}"

    def _proxies(self):
        if self.proxy:
            return {"http": self.proxy, "https": self.proxy}
        return None

    @abstractmethod
    def login(self) -> bool:
        """登录，成功返回 True"""
        ...

    @abstractmethod
    def checkin(self) -> str:
        """签到，返回签到结果描述"""
        ...

    @abstractmethod
    def get_user_info(self) -> dict:
        """获取用户信息（余额、流量、到期时间、邀请人数、佣金等）"""
        ...

    def run(self) -> str:
        """执行完整流程，返回格式化的结果文本"""
        results = [f"【{self.name}】"]

        # 登录
        if not self.login():
            results.append("  登录失败")
            return "\n".join(results)

        results.append("  登录成功")

        # 签到
        checkin_result = self.checkin()
        if checkin_result:
            results.append(f"  签到: {checkin_result}")

        # 用户信息
        info = self.get_user_info()
        if info:
            for key, value in info.items():
                results.append(f"  {key}: {value}")

        return "\n".join(results)
