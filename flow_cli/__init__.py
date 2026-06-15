"""
Flow CLI — Professional image generation library for Google Flow.

Usage::

    from flow_cli import FlowClient, ImageGenerator

    async with FlowClient() as client:
        ...
"""

from flow_cli._version import __version__

# Configuration
from flow_cli.config import AppConfig, get_config, set_config

# Core classes — the primary public API
from flow_cli.core.client import FlowClient
from flow_cli.core.generator import ImageGenerator
from flow_cli.core.session import SessionManager
from flow_cli.core.sdk import FlowSDK
from flow_cli.captcha import (
    CaptchaProvider,
    NullCaptchaProvider,
    PlaywrightCaptchaProvider,
    InProcessCaptchaProvider,
)

# Exceptions
from flow_cli.exceptions import (
    FlowAuthError,
    FlowCaptchaError,
    FlowConfigError,
    FlowError,
    FlowGenerationError,
    FlowModelNotFoundError,
    FlowNetworkError,
    FlowRateLimitError,
    FlowServerError,
    FlowTimeoutError,
    FlowTokenExpiredError,
    FlowUploadError,
    FlowUpscaleError,
)

# Model registry
from flow_cli.models.registry import (
    IMAGE_MODELS,
    get_model_config,
    list_model_ids,
    list_models,
    resolve_model,
)

# Typed data models
from flow_cli.types import (
    AspectRatio,
    CaptchaMethod,
    CreditsInfo,
    GenerationResult,
    ModelConfig,
    Orientation,
    TokenInfo,
    UpscaleResolution,
)

__all__ = [
    # Version
    "__version__",
    # Core
    "FlowClient",
    "ImageGenerator",
    "SessionManager",
    "FlowSDK",
    "CaptchaProvider",
    "NullCaptchaProvider",
    "PlaywrightCaptchaProvider",
    "InProcessCaptchaProvider",
    # Config
    "AppConfig",
    "get_config",
    "set_config",
    # Types
    "AspectRatio",
    "CaptchaMethod",
    "CreditsInfo",
    "GenerationResult",
    "ModelConfig",
    "Orientation",
    "TokenInfo",
    "UpscaleResolution",
    # Exceptions
    "FlowAuthError",
    "FlowCaptchaError",
    "FlowConfigError",
    "FlowError",
    "FlowGenerationError",
    "FlowModelNotFoundError",
    "FlowNetworkError",
    "FlowRateLimitError",
    "FlowServerError",
    "FlowTimeoutError",
    "FlowTokenExpiredError",
    "FlowUploadError",
    "FlowUpscaleError",
    # Models
    "IMAGE_MODELS",
    "get_model_config",
    "list_model_ids",
    "list_models",
    "resolve_model",
]
