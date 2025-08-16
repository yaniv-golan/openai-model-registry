"""OpenAI Model Registry CLI package."""

# Import guard for CLI dependencies
try:
    from .app import app
except ImportError as e:
    if "CLI dependencies not available" in str(e):
        raise
    # Re-raise with helpful message if it's a different import error
    raise ImportError("CLI dependencies not available. Install with: pip install openai-model-registry[cli]") from e

__all__ = ["app"]
