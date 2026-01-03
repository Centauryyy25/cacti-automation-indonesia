"""Centralized configuration management for CactiAutomation.

Uses pydantic-settings for type-safe configuration with environment variable support.
All sensitive values should be set via environment variables or .env file.

Usage:
    from config import settings

    url = settings.CACTI_BASE_URL
    username = settings.CACTI_USERNAME
"""

from __future__ import annotations

from functools import lru_cache

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for environments without pydantic-settings
    from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # ==========================================================================
    # Environment
    # ==========================================================================
    ENV: str = Field(default="development", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=False, description="Enable debug mode (NEVER in production)")

    # ==========================================================================
    # CACTI Configuration
    # ==========================================================================
    CACTI_BASE_URL: str = Field(
        default="",  # Set via CACTI_BASE_URL environment variable
        description="Base URL for CACTI NMS"
    )
    CACTI_ALLOWED_URLS: str = Field(
        default="",  # Set via CACTI_ALLOWED_URLS environment variable
        description="Comma-separated list of allowed CACTI URLs (SSRF protection)"
    )

    # ==========================================================================
    # Credentials (MUST be set via environment)
    # ==========================================================================
    CACTI_USERNAME: str = Field(
        default="",
        description="CACTI login username"
    )
    CACTI_PASSWORD: str = Field(
        default="",
        description="CACTI login password"
    )

    # ==========================================================================
    # Web Server
    # ==========================================================================
    HOST: str = Field(default="127.0.0.1", description="Server host")
    PORT: int = Field(default=5000, description="Server port")
    CORS_ORIGINS: str = Field(
        default="http://localhost:5000,http://127.0.0.1:5000",
        description="Comma-separated allowed CORS origins"
    )

    # ==========================================================================
    # Selenium / Scraping
    # ==========================================================================
    SELENIUM_HEADLESS: bool = Field(default=False, description="Run Chrome in headless mode")
    SELENIUM_WAIT_TIMEOUT: int = Field(default=15, description="WebDriverWait timeout in seconds")
    SELENIUM_PAGE_LOAD_TIMEOUT: int = Field(default=30, description="Page load timeout in seconds")

    # ==========================================================================
    # Request / Retry Configuration
    # ==========================================================================
    REQUEST_TIMEOUT: int = Field(default=30, description="HTTP request timeout in seconds")
    RETRY_MAX_ATTEMPTS: int = Field(default=3, description="Maximum retry attempts")
    RETRY_BASE_DELAY: float = Field(default=1.0, description="Base delay for exponential backoff (seconds)")
    RETRY_MAX_DELAY: float = Field(default=60.0, description="Maximum delay between retries (seconds)")
    RETRY_EXPONENTIAL_BASE: float = Field(default=2.0, description="Exponential backoff multiplier")

    # ==========================================================================
    # OCR Configuration
    # ==========================================================================
    OCR_GPU_ENABLED: bool = Field(default=False, description="Enable GPU for EasyOCR")
    OCR_TARGET_WIDTH: int = Field(default=1600, description="Target image width for preprocessing")
    OCR_BATCH_SIZE: int = Field(default=4, description="OCR batch size")
    OCR_LANGUAGES: str = Field(default="en", description="Comma-separated OCR languages")

    # ==========================================================================
    # Storage
    # ==========================================================================
    OUTPUT_DIR: str = Field(default="output", description="Base output directory")
    LOG_DIR: str = Field(default="Debug", description="Log files directory")

    # ==========================================================================
    # Redis (for task queue)
    # ==========================================================================
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")

    # ==========================================================================
    # Notifications
    # ==========================================================================
    NOTIFICATION_ENABLED: bool = Field(default=False, description="Enable notifications")

    # Email (SMTP)
    SMTP_HOST: str = Field(default="", description="SMTP server host")
    SMTP_PORT: int = Field(default=587, description="SMTP server port")
    SMTP_USER: str = Field(default="", description="SMTP username")
    SMTP_PASSWORD: str = Field(default="", description="SMTP password")
    SMTP_FROM: str = Field(default="", description="From email address")
    SMTP_TO: str = Field(default="", description="Comma-separated recipient emails")

    # Slack
    SLACK_WEBHOOK_URL: str = Field(default="", description="Slack webhook URL")

    # ==========================================================================
    # Helper Properties
    # ==========================================================================
    @property
    def allowed_urls_list(self) -> list[str]:
        """Parse CACTI_ALLOWED_URLS into a list."""
        return [url.strip() for url in self.CACTI_ALLOWED_URLS.split(",") if url.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def ocr_languages_list(self) -> list[str]:
        """Parse OCR_LANGUAGES into a list."""
        return [lang.strip() for lang in self.OCR_LANGUAGES.split(",") if lang.strip()]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENV.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENV.lower() == "development"

    # ==========================================================================
    # Validation
    # ==========================================================================
    def validate_url(self, url: str) -> bool:
        """Validate if URL is in the allowed list (SSRF protection)."""
        if not self.allowed_urls_list:
            return True  # No restrictions if list is empty
        return any(url.startswith(allowed) for allowed in self.allowed_urls_list)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Default settings instance for easy import
settings = get_settings()


# ==========================================================================
# Utility Functions
# ==========================================================================
def validate_cacti_url(url: str) -> tuple[bool, str]:
    """
    Validate CACTI URL against allowlist.

    Returns:
        tuple: (is_valid, error_message)
    """
    if not url:
        return False, "URL cannot be empty"

    if not url.startswith(("http://", "https://")):
        return False, "URL must start with http:// or https://"

    if not settings.validate_url(url):
        allowed = ", ".join(settings.allowed_urls_list)
        return False, f"URL not in allowed list. Allowed: {allowed}"

    return True, ""


def mask_sensitive(value: str, visible_chars: int = 4) -> str:
    """Mask sensitive values for logging."""
    if not value or len(value) <= visible_chars:
        return "***"
    return value[:visible_chars] + "*" * (len(value) - visible_chars)
