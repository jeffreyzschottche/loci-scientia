"""
Backend translations for multilingual support.
"""
import os
from pathlib import Path
from typing import Optional

_current_language: str = "nl"

TRANSLATIONS = {
    # AI Prompt templates
    "prompt_default_template": {
        "nl": (
            "Je bent een behulpzame assistent. Gebruik context en bijlagen waar mogelijk, "
            "maar verzin niets als er geen relevante context beschikbaar is. "
            "Leg je antwoord duidelijk uit en antwoord in het Nederlands."
        ),
        "en": (
            "You are a helpful assistant. Use context and attachments where possible, "
            "but don't make anything up if there's no relevant context available. "
            "Explain your answer clearly and respond in English."
        ),
    },
    "speaker_assistant": {
        "nl": "AITJE",
        "en": "AITJE",
    },
    "speaker_system": {
        "nl": "Systeem",
        "en": "System",
    },
    "speaker_user": {
        "nl": "Gebruiker",
        "en": "User",
    },
    "previous_chat": {
        "nl": "Vorige chat:",
        "en": "Previous chat:",
    },
    "current_question": {
        "nl": "Huidige vraag:",
        "en": "Current question:",
    },
    "summary_instruction_1": {
        "nl": "Vat de chatgeschiedenis compact samen.",
        "en": "Summarize the chat history concisely.",
    },
    "summary_instruction_2": {
        "nl": "Bewaar namen, afspraken, besluiten, open vragen en voorkeuren.",
        "en": "Keep names, appointments, decisions, open questions and preferences.",
    },
    "summary_instruction_3": {
        "nl": "Schrijf in het Nederlands en blijf feitelijk.",
        "en": "Write in English and stay factual.",
    },
    "summary_instruction_4": {
        "nl": "Gebruik maximaal 8 zinnen.",
        "en": "Use a maximum of 8 sentences.",
    },
    "existing_summary": {
        "nl": "Bestaande samenvatting:",
        "en": "Existing summary:",
    },
    "new_messages": {
        "nl": "Nieuwe berichten:",
        "en": "New messages:",
    },
    "summary_failed": {
        "nl": "Samenvatting maken faalde:",
        "en": "Summary creation failed:",
    },
    "ollama_not_available": {
        "nl": "[Ollama niet beschikbaar - Mock response]",
        "en": "[Ollama not available - Mock response]",
    },
    "ollama_no_response": {
        "nl": "Kon geen antwoord krijgen van Ollama op {url} met model '{model}'.",
        "en": "Could not get a response from Ollama at {url} with model '{model}'.",
    },
    "ollama_check_service": {
        "nl": "Controleer of de Ollama-service draait en bereikbaar is.",
        "en": "Check if the Ollama service is running and accessible.",
    },
    "no_response_generated": {
        "nl": "Ik kon geen antwoord genereren.",
        "en": "I could not generate a response.",
    },
}


def _env_file_path() -> Path:
    """Return path to .env file."""
    return Path(__file__).resolve().parents[2] / ".env"


def _read_env_language() -> Optional[str]:
    """Read LANGUAGE from .env file."""
    path = _env_file_path()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() != "LANGUAGE":
            continue
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        return value.strip()
    return None


def get_current_language() -> str:
    """Get the current language code (nl or en)."""
    env_lang = os.environ.get("LANGUAGE", "")
    if env_lang:
        if "en" in env_lang.lower():
            return "en"
        return "nl"

    file_lang = _read_env_language()
    if file_lang:
        if "en" in file_lang.lower():
            return "en"
        return "nl"

    return _current_language


def t(key: str, **kwargs) -> str:
    """
    Get translated text for a key.

    Args:
        key: The translation key
        **kwargs: Format arguments to substitute into the string

    Returns:
        The translated string, or the key if not found
    """
    lang = get_current_language()

    if key not in TRANSLATIONS:
        return key

    text = TRANSLATIONS[key].get(lang, TRANSLATIONS[key].get("nl", key))

    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass

    return text
