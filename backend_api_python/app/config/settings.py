"""
应用主配置
"""

import os


class MetaConfig(type):
    # ==================== 服务配置 ====================
    # 服务启动参数通常由环境变量或命令行参数决定，不建议从数据库读取

    @property
    def SINGLE_USER_MODE(cls):
        # Desktop: single-user mode by default when DB_TYPE is sqlite
        if os.getenv("DB_TYPE", "").lower() == "sqlite":
            return True
        return os.getenv("SINGLE_USER_MODE", "false").lower() == "true"

    @property
    def HOST(cls):
        # Desktop: force localhost binding
        if os.getenv("DB_TYPE", "").lower() == "sqlite":
            return "127.0.0.1"
        return os.getenv("PYTHON_API_HOST", "0.0.0.0")

    @property
    def PORT(cls):
        return int(os.getenv("PYTHON_API_PORT", 5000))

    @property
    def DEBUG(cls):
        return os.getenv("PYTHON_API_DEBUG", "False").lower() == "true"

    @property
    def APP_NAME(cls):
        return "Mipham Quant"

    @property
    def VERSION(cls):
        return "0.1.0"

    # ==================== 认证配置 ====================
    @property
    def SECRET_KEY(cls):
        # Desktop: auto-generate a random key if not set
        key = os.getenv("SECRET_KEY", "").strip()
        if not key:
            import secrets
            key = secrets.token_hex(32)
            os.environ["SECRET_KEY"] = key
        return key

    @property
    def ADMIN_USER(cls):
        # Desktop: generate random admin username on first launch
        if os.getenv("DB_TYPE", "").lower() == "sqlite":
            return os.getenv("ADMIN_USER", "admin")
        val = os.getenv("ADMIN_USER", "").strip()
        if not val:
            raise RuntimeError(
                "ADMIN_USER environment variable is required in multi-user mode. "
                "Set ADMIN_USER to the admin account username."
            )
        return val

    @property
    def ADMIN_PASSWORD(cls):
        # Desktop: auto-generate random password on first launch, persisted via SECRET_KEY mechanism
        if os.getenv("DB_TYPE", "").lower() == "sqlite":
            import secrets
            pwd = os.getenv("ADMIN_PASSWORD", "").strip()
            if not pwd:
                pwd = secrets.token_urlsafe(16)
                os.environ["ADMIN_PASSWORD"] = pwd
                # Log once so the desktop app can capture and display it
                import logging
                logging.getLogger("mipham").warning(
                    "Generated random admin password. Save this password to regain access."
                )
            return pwd
        val = os.getenv("ADMIN_PASSWORD", "").strip()
        if not val:
            raise RuntimeError(
                "ADMIN_PASSWORD environment variable is required in multi-user mode. "
                "Set a strong ADMIN_PASSWORD for the admin account."
            )
        return val

    # ==================== 日志配置 ====================
    # 日志配置通常在应用启动最早阶段需要，建议保持环境变量

    @property
    def LOG_LEVEL(cls):
        return os.getenv("LOG_LEVEL", "INFO")

    @property
    def LOG_DIR(cls):
        return os.getenv("LOG_DIR", "logs")

    @property
    def LOG_FILE(cls):
        return os.getenv("LOG_FILE", "app.log")

    @property
    def LOG_MAX_BYTES(cls):
        return int(os.getenv("LOG_MAX_BYTES", 10 * 1024 * 1024))

    @property
    def LOG_BACKUP_COUNT(cls):
        return int(os.getenv("LOG_BACKUP_COUNT", 5))

    # ==================== 安全配置 ====================

    @property
    def RATE_LIMIT(cls):
        from app.utils.config_loader import load_addon_config

        val = load_addon_config().get("app", {}).get("rate_limit")
        return int(val) if val is not None else int(os.getenv("RATE_LIMIT", 100))

    # ==================== 功能开关 ====================

    @property
    def ENABLE_CACHE(cls):
        from app.utils.config_loader import load_addon_config

        val = load_addon_config().get("app", {}).get("enable_cache")
        if val is not None:
            return bool(val)
        return os.getenv("ENABLE_CACHE", "False").lower() == "true"

    @property
    def ENABLE_REQUEST_LOG(cls):
        from app.utils.config_loader import load_addon_config

        val = load_addon_config().get("app", {}).get("enable_request_log")
        if val is not None:
            return bool(val)
        return os.getenv("ENABLE_REQUEST_LOG", "True").lower() == "true"


class Config(metaclass=MetaConfig):
    """应用配置类"""

    @classmethod
    def get_log_path(cls) -> str:
        """获取日志文件完整路径"""
        return os.path.join(cls.LOG_DIR, cls.LOG_FILE)
