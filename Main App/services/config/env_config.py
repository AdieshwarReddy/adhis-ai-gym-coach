import os
from pathlib import Path

# Automatically load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    # Search root and parent directories for .env
    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    app_dir = Path(__file__).resolve().parent.parent.parent
    if (app_dir / ".env").exists():
        load_dotenv(app_dir / ".env")
    elif (root_dir / ".env").exists():
        load_dotenv(root_dir / ".env")
except ImportError:
    pass


def get_secret(key: str, default: str = "") -> str:
    """
    Safely retrieves a configuration key checking:
    1. Streamlit secrets (st.secrets)
    2. Environment variables (os.environ)
    3. Default value fallback
    Never raises StreamlitSecretNotFoundError.
    """
    # 1. Try Streamlit secrets
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            val = st.secrets[key]
            if val is not None:
                return str(val).strip()
    except Exception:
        pass

    # 2. Try OS environment variables
    env_val = os.environ.get(key)
    if env_val is not None:
        return str(env_val).strip()

    return default


def is_feature_enabled(key: str, default: bool = True) -> bool:
    """Returns True if a boolean feature toggle is enabled."""
    val = get_secret(key, str(default)).lower()
    return val in ("true", "1", "yes", "on")


# Clean properties
def get_supabase_url() -> str:
    return get_secret("SUPABASE_URL", "")


def get_supabase_anon_key() -> str:
    return get_secret("SUPABASE_ANON_KEY", "")


def get_groq_api_key() -> str:
    return get_secret("GROQ_API_KEY", "")


def get_gemini_api_key() -> str:
    return get_secret("GEMINI_API_KEY", "")


def get_app_env() -> str:
    return get_secret("APP_ENV", "development")


def is_llm_enabled() -> bool:
    return is_feature_enabled("LLM_ENABLED", True) and bool(get_groq_api_key() or get_gemini_api_key())


def is_voice_enabled() -> bool:
    return is_feature_enabled("VOICE_ENABLED", True)

