"""Translation system for multi-language support.

Stores translations in SurrealDB and provides functions to get translated strings.
"""

import logging
from typing import Dict, Optional

from .config import settings
from .db import get_db_sync

logger = logging.getLogger(__name__)

# Default supported languages
SUPPORTED_LANGUAGES = ["en", "es", "fr", "de", "zh", "ja"]

# Translation keys for the UI
TRANSLATION_KEYS = {
    "help_title": "Mission Control Help",
    "drone_title": "Drone",
    "drone_description": "Aerial reconnaissance unit capable of scanning terrain from above, mapping routes through obstacles, and relaying communications between rovers and the station.",
    "movement_title": "Movement",
    "movement_rover": "Rover",
    "movement_drone": "Drone",
    "movement_station": "Station",
    "movement_rover_range": "±1 tile/turn",
    "movement_drone_range": "±2 tiles/turn",
    "movement_station_range": "Fixed",
    "movement_rover_desc": "Ground traversal",
    "movement_drone_desc": "Aerial flight",
    "movement_station_desc": "Base operations",
    "limitations_title": "Limitations",
    "storm_damage": "High dust storms degrade movement and sensor effectiveness",
    "communication_range": "Direct contact or relay via drone required",
    "carry_capacity": "Rovers limited to 3 stone units, drones cannot carry",
    "drone_battery": "Cannot operate below 20% charge",
    "station_power": "Limited allocation affects charge rate",
    "storm_events": "Random storms reduce visibility, increase battery drain, and create urgency",
    "battery_title": "Battery",
    "full_charge": "Full charge",
    "drone_minimum": "Drone minimum",
    "cost_per_move": "Cost per move",
    "cost_per_scan": "Cost per scan",
    "charge_rate": "Charge rate",
    "storm_penalty": "Storm penalty",
    "battery_100": "100%",
    "battery_20": "20%",
    "rover_2_drone_3": "Rover 2% | Drone 3%",
    "drone_5": "Drone 5%",
    "charge_5_per_turn": "5% per turn at station",
    "storm_50_extra": "+50% cost during storms",
    "controls_title": "Controls",
    "pause_resume": "Pause/Resume",
    "pan_camera": "Pan camera",
    "follow_agent": "Follow agent",
    "free_camera": "Free camera",
    "close_modals": "Close modals",
}


def init_translations():
    """Initialize default translations in the database."""
    try:
        db = get_db_sync()
        # Create translations table if it doesn't exist
        db.query("DEFINE TABLE translations SCHEMAFULL;").execute()
        db.query("DEFINE FIELD language ON translations TYPE string;").execute()
        db.query("DEFINE FIELD key ON translations TYPE string;").execute()
        db.query("DEFINE FIELD value ON translations TYPE string;").execute()
        db.query(
            "DEFINE INDEX translations_language_key ON translations COLUMNS language, key UNIQUE;"
        ).execute()

        # Insert default English translations
        for key, value in TRANSLATION_KEYS.items():
            db.query("UPSERT translations SET language = 'en', key = $key, value = $value;").bind(
                {"key": key, "value": value}
            ).execute()

        logger.info("Default translations initialized")
        db.close()
    except Exception as e:
        logger.error(f"Failed to initialize translations: {e}")


def get_translation(language: str, key: str, default: str = None) -> str:
    """Get a translation for a specific language and key."""
    try:
        db = get_db_sync()
        result = (
            db.query(
                "SELECT value FROM translations WHERE language = $language AND key = $key LIMIT 1;"
            )
            .bind({"language": language, "key": key})
            .execute()
        )

        if result and len(result) > 0:
            return result[0]["value"]
        else:
            # Return default if available, otherwise return the key
            return default or TRANSLATION_KEYS.get(key, key)
    except Exception as e:
        logger.error(f"Failed to get translation for {language}:{key}: {e}")
        return default or TRANSLATION_KEYS.get(key, key)
    finally:
        try:
            db.close()
        except:
            pass


def get_all_translations(language: str) -> Dict[str, str]:
    """Get all translations for a specific language."""
    try:
        db = get_db_sync()
        result = (
            db.query("SELECT key, value FROM translations WHERE language = $language;")
            .bind({"language": language})
            .execute()
        )

        translations = {}
        for item in result:
            translations[item["key"]] = item["value"]

        # Fill in missing keys with defaults
        for key, default_value in TRANSLATION_KEYS.items():
            if key not in translations:
                translations[key] = default_value

        return translations
    except Exception as e:
        logger.error(f"Failed to get all translations for {language}: {e}")
        return TRANSLATION_KEYS.copy()
    finally:
        try:
            db.close()
        except:
            pass


def set_translation(language: str, key: str, value: str):
    """Set a translation for a specific language and key."""
    try:
        db = get_db_sync()
        db.query("UPSERT translations SET language = $language, key = $key, value = $value;").bind(
            {"language": language, "key": key, "value": value}
        ).execute()
        logger.info(f"Translation set: {language}:{key} = {value}")
    except Exception as e:
        logger.error(f"Failed to set translation for {language}:{key}: {e}")
    finally:
        try:
            db.close()
        except:
            pass


def get_supported_languages() -> list:
    """Get list of supported languages."""
    try:
        db = get_db_sync()
        result = db.query("SELECT DISTINCT language FROM translations;").execute()

        languages = [item["language"] for item in result]
        return languages if languages else SUPPORTED_LANGUAGES
    except Exception as e:
        logger.error(f"Failed to get supported languages: {e}")
        return SUPPORTED_LANGUAGES
    finally:
        try:
            db.close()
        except:
            pass
