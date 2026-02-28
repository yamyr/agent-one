from __future__ import annotations

SUPPORTED_LOCALES = [
    {"code": "en-US", "label": "English (US)"},
    {"code": "zh-Hans", "label": "简体中文"},
    {"code": "zh-Hant", "label": "繁體中文"},
    {"code": "ta-IN", "label": "தமிழ்"},
    {"code": "ml-IN", "label": "മലയാളം"},
    {"code": "ja-JP", "label": "日本語"},
    {"code": "fr-FR", "label": "Français"},
    {"code": "pt-PT", "label": "Português"},
    {"code": "de-DE", "label": "Deutsch"},
    {"code": "uk-UA", "label": "Українська"},
]

RAW_TRANSLATIONS = {
    "app.title": {
        "en-US": "Mars Mission Control",
        "zh-Hans": "火星任务控制中心",
        "zh-Hant": "火星任務控制中心",
        "ta-IN": "செவ்வாய் மிஷன் கட்டுப்பாடு",
        "ml-IN": "മാർസ് മിഷൻ നിയന്ത്രണം",
        "ja-JP": "火星ミッション管制",
    },
    "header.language": {"en-US": "Language"},
    "header.reset": {
        "en-US": "RESET",
        "zh-Hans": "重置",
        "zh-Hant": "重設",
        "ta-IN": "மீட்டமை",
        "ml-IN": "റീസെറ്റ്",
        "ja-JP": "リセット",
    },
    "header.pause": {
        "en-US": "PAUSE",
        "zh-Hans": "暂停",
        "zh-Hant": "暫停",
        "ta-IN": "இடைநிறுத்து",
        "ml-IN": "താൽക്കാലിക നിർത്തൽ",
        "ja-JP": "一時停止",
    },
    "header.resume": {
        "en-US": "RESUME",
        "zh-Hans": "继续",
        "zh-Hant": "繼續",
        "ta-IN": "தொடர்",
        "ml-IN": "തുടരുക",
        "ja-JP": "再開",
    },
    "status.connected": {
        "en-US": "CONNECTED",
        "zh-Hans": "已连接",
        "zh-Hant": "已連線",
        "ta-IN": "இணைந்தது",
        "ml-IN": "കണക്റ്റഡ്",
        "ja-JP": "接続中",
    },
    "status.disconnected": {
        "en-US": "DISCONNECTED",
        "zh-Hans": "未连接",
        "zh-Hant": "未連線",
        "ta-IN": "துண்டிக்கப்பட்டது",
        "ml-IN": "ഡിസ്കണക്റ്റഡ്",
        "ja-JP": "未接続",
    },
    "ui.follow": {"en-US": "Follow:"},
    "ui.follow_agent": {"en-US": "Follow {agent}"},
    "ui.free": {"en-US": "Free"},
    "ui.switch_free_camera": {"en-US": "Switch to free camera"},
    "stats.tick": {"en-US": "Tick"},
    "stats.revealed": {"en-US": "Revealed"},
    "stats.tiles": {"en-US": "tiles"},
    "stats.agents": {"en-US": "Agents"},
    "stats.veins": {"en-US": "Veins"},
    "stats.collected": {"en-US": "Collected"},
    "stats.events": {"en-US": "Events"},
    "mission.label": {"en-US": "Mission"},
    "mission.collect": {"en-US": "collect {target} basalt"},
    "mission.in_transit": {"en-US": "{count} in transit"},
    "mission.abort": {"en-US": "ABORT"},
    "log.title": {"en-US": "Event Log"},
    "overview.title": {"en-US": "Overview"},
    "overview.no_data": {"en-US": "No data"},
    "legend.toggle": {"en-US": "Toggle map legend"},
    "legend.station": {"en-US": "Station"},
    "legend.rover": {"en-US": "Rover"},
    "legend.drone": {"en-US": "Drone"},
    "toast.mission_complete": {"en-US": "Mission complete — {count} collected"},
    "toast.mission_aborted": {"en-US": "Mission aborted — {reason}"},
    "toast.alert_default": {"en-US": "Alert"},
    "toast.found_vein": {"en-US": "{source}: found {grade} vein"},
    "world.surface_map": {"en-US": "Surface Map"},
    "world.following": {"en-US": "(following {agent})"},
    "world.free_camera_hint": {"en-US": "(free camera · drag to pan)"},
    "world.zoom_out": {"en-US": "Zoom out"},
    "world.zoom_in": {"en-US": "Zoom in"},
    "world.zoom_reset": {"en-US": "Reset zoom"},
    "world.zoom_out_aria": {"en-US": "Zoom out map"},
    "world.zoom_in_aria": {"en-US": "Zoom in map"},
    "world.zoom_reset_aria": {"en-US": "Reset map zoom"},
    "world.reset": {"en-US": "Reset"},
    "world.aria_map": {
        "en-US": "Interactive world map. Drag or use keyboard arrows/WASD to pan, mouse wheel to zoom."
    },
    "world.connecting": {"en-US": "Connecting to satellite feed..."},
    "world.agent_tooltip": {
        "en-US": "{id} [{type}]\nPosition: {pos}\nBattery: {bat}%\nTiles visited: {visited}"
    },
    "world.stone_tooltip": {"en-US": "{grade} vein\nPosition: {pos}\nQuantity: {qty}"},
    "world.panel_tooltip": {"en-US": "Solar Panel {state}\nPosition: {pos}"},
    "world.panel_active": {"en-US": "(active)"},
    "world.panel_depleted": {"en-US": "(depleted)"},
    "help.keyboard_shortcuts": {"en-US": "Keyboard Shortcuts"},
    "help.close": {"en-US": "Close help"},
    "help.camera": {"en-US": "Camera"},
    "help.simulation": {"en-US": "Simulation"},
    "help.or": {"en-US": "or"},
    "help.pan_camera": {"en-US": "Pan camera"},
    "help.zoom_in_out": {"en-US": "Zoom in/out"},
    "help.free_camera": {"en-US": "Free camera"},
    "help.pause_resume": {"en-US": "Pause / Resume"},
    "help.follow_agent": {"en-US": "Follow agent"},
    "help.close_modal": {"en-US": "Close modal"},
    "help.toggle_help": {"en-US": "Toggle this help"},
    "narration.mission_comms": {"en-US": "MISSION COMMS"},
    "narration.awaiting_events": {"en-US": "Awaiting mission events..."},
    "narration.skip": {"en-US": "SKIP"},
    "narration.skip_title": {"en-US": "Skip narration"},
    "narration.voice_on": {"en-US": "Voice ON"},
    "narration.voice_off": {"en-US": "Voice OFF"},
    "narration.voice_turn_off": {"en-US": "Turn voice off"},
    "narration.voice_turn_on": {"en-US": "Turn voice on"},
    "agentpane.no_activity": {"en-US": "No activity yet"},
    "agentpane.think": {"en-US": "think"},
    "agentpane.action": {"en-US": "action"},
    "agentpane.inventory_prefix": {"en-US": "inv ({quantities})"},
    "agentdetail.dialog_aria": {"en-US": "Agent details for {agent}"},
    "agentdetail.close": {"en-US": "Close agent details"},
    "agentdetail.type": {"en-US": "Type"},
    "agentdetail.mission": {"en-US": "Mission"},
    "agentdetail.current_task": {"en-US": "Current Task"},
    "agentdetail.position": {"en-US": "Position"},
    "agentdetail.battery": {"en-US": "Battery"},
    "agentdetail.tiles_visited": {"en-US": "Tiles visited"},
    "agentdetail.inventory": {"en-US": "Inventory"},
    "agentdetail.empty": {"en-US": "Empty"},
    "agentdetail.tools": {"en-US": "Tools"},
    "agentdetail.no_tools": {"en-US": "No tools"},
    "agentdetail.system_prompt": {"en-US": "System Prompt"},
    "agent.type.rover": {"en-US": "rover"},
}


def _fill_missing_locales() -> dict[str, dict[str, str]]:
    locale_codes = [entry["code"] for entry in SUPPORTED_LOCALES]
    out: dict[str, dict[str, str]] = {}
    for key, translations in RAW_TRANSLATIONS.items():
        en = translations.get("en-US") or key
        out[key] = {locale: translations.get(locale, en) for locale in locale_codes}
    return out


DEFAULT_TRANSLATIONS = _fill_missing_locales()


def resolve_locale(locale: str | None) -> str:
    allowed = {item["code"] for item in SUPPORTED_LOCALES}
    if locale in allowed:
        return locale
    return "en-US"
