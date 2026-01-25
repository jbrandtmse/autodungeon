"""Streamlit entry point for autodungeon.

This is the main application entry point. Run with:
    streamlit run app.py
"""

import streamlit as st

from config import AppConfig, get_config, validate_api_keys


def get_api_key_status(config: AppConfig) -> str:
    """Generate a formatted string showing API key configuration status.

    Args:
        config: The application configuration.

    Returns:
        Formatted string showing which API keys are configured.
    """
    lines: list[str] = []

    # Google/Gemini status
    if config.google_api_key:
        lines.append("- **Google (Gemini)**: Configured")
    else:
        lines.append("- **Google (Gemini)**: Not configured")

    # Anthropic/Claude status
    if config.anthropic_api_key:
        lines.append("- **Anthropic (Claude)**: Configured")
    else:
        lines.append("- **Anthropic (Claude)**: Not configured")

    # Ollama status (always has a default URL)
    lines.append(f"- **Ollama (Local)**: {config.ollama_base_url}")

    return "\n".join(lines)


def main() -> None:
    """Main Streamlit application entry point."""
    st.set_page_config(
        page_title="autodungeon",
        page_icon="🎲",
        layout="wide",
    )

    st.title("autodungeon")
    st.caption("Multi-agent D&D game engine")

    # Load configuration
    config = get_config()

    # Display configuration status
    st.header("Configuration Status")

    # API Key Status
    st.subheader("LLM Provider Status")
    st.markdown(get_api_key_status(config))

    # Show warnings for missing API keys
    warnings = validate_api_keys(config)
    if warnings:
        st.warning("\n".join(warnings))

    # Display current defaults
    st.subheader("Current Defaults")
    st.markdown(
        f"""
- **Default Provider**: {config.default_provider}
- **Default Model**: {config.default_model}
- **Party Size**: {config.party_size}
- **Auto Save**: {config.auto_save}
"""
    )

    # Placeholder for future features
    st.divider()
    st.info(
        "Game functionality will be implemented in subsequent stories. "
        "This foundation story establishes project configuration."
    )


if __name__ == "__main__":
    main()
