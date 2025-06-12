"""FastAPI application configuration"""
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Database
    data_dir: Path = Path.home() / '.rotki'
    db_password: str = ''

    # API Configuration
    api_host: str = '127.0.0.1'
    api_port: int = 5042
    cors_origins: list[str] = []

    # Feature flags
    premium_sync_enabled: bool = True
    experimental_features: bool = False

    # Performance settings
    max_log_size_mb: int = 100
    max_log_backups: int = 5
    sql_vm_instructions_cb: int = 5000

    class Config:
        env_prefix = 'ROTKI_'
        env_file = '.env'

