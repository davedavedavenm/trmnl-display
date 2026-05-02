from dotenv import load_dotenv
import datetime
import json
import os
from pathlib import Path
import requests

load_dotenv()
load_dotenv(os.getenv("TRMNL_HA_DASHBOARD_ENV", "/home/dave/.env.trmnl-ha-dashboard"))

HA_URL = os.getenv("HA_URL", "http://192.168.1.89:8123").strip()
HA_TOKEN = os.getenv("HA_TOKEN", "").strip()
TRMNL_WEBHOOK_URL = os.getenv("TRMNL_WEBHOOK_URL", "").strip()
TRMNL_UPDATED_AT_FORMAT = os.getenv("TRMNL_UPDATED_AT_FORMAT", "%d %b %H:%M")
CACHE_FILE = os.getenv("TRMNL_CACHE_FILE", "/home/dave/.trmnl_ha_cache.json")
DASHBOARD_TITLE = os.getenv("TRMNL_DASHBOARD_TITLE", "Home Assistant").strip()
INSTANCE_LABEL = os.getenv("TRMNL_INSTANCE_LABEL", "Home").strip()
LAYOUT_VARIANT = os.getenv("TRMNL_LAYOUT_VARIANT", "compact_grid").strip()
COLOUR_PROFILE = os.getenv("TRMNL_COLOUR_PROFILE", "inky_spectra_7").strip()
WEATHER_ENTITY = os.getenv("TRMNL_WEATHER_ENTITY", "weather.forecast_home").strip()
PERSON_ENTITIES = [e.strip() for e in os.getenv("TRMNL_PERSON_ENTITIES", "person.example").split(",") if e.strip()]
SONOS_ENTITIES = [e.strip() for e in os.getenv("TRMNL_SONOS_ENTITIES", "").split(",") if e.strip()]
LIGHT_ENTITIES = [e.strip() for e in os.getenv("TRMNL_LIGHT_ENTITIES", "").split(",") if e.strip()]
LIGHT_LABELS = [e.strip() for e in os.getenv("TRMNL_LIGHT_LABELS", "").split(",") if e.strip()]
DOOR_ENTITY = os.getenv("TRMNL_DOOR_ENTITY", "").strip()
WASHER_ENTITY = os.getenv("TRMNL_WASHER_ENTITY", "").strip()
BLIND_ENTITY = os.getenv("TRMNL_BLIND_ENTITY", "").strip()
BLIND_OPEN_POSITION = os.getenv("TRMNL_BLIND_OPEN_POSITION", "").strip()
THERMOSTAT_ENTITY = os.getenv("TRMNL_THERMOSTAT_ENTITY", "").strip()
ENERGY_ENTITY = os.getenv("TRMNL_ENERGY_ENTITY", "").strip()
DOOR_LABEL = os.getenv("TRMNL_DOOR_LABEL", "Front door").strip()
DOOR_DETAIL_LABEL = os.getenv("TRMNL_DOOR_DETAIL_LABEL", "Security").strip()
WASHER_LABEL = os.getenv("TRMNL_WASHER_LABEL", "Washer").strip()
WASHER_DETAIL_LABEL = os.getenv("TRMNL_WASHER_DETAIL_LABEL", "Utility").strip()
BLIND_LABEL = os.getenv("TRMNL_BLIND_LABEL", "Blinds").strip()
BLIND_DETAIL_LABEL = os.getenv("TRMNL_BLIND_DETAIL_LABEL", "Position").strip()
THERMOSTAT_LABEL = os.getenv("TRMNL_THERMOSTAT_LABEL", "Climate").strip()
THERMOSTAT_DETAIL_LABEL = os.getenv("TRMNL_THERMOSTAT_DETAIL_LABEL", "Indoor").strip()
SONOS_LABEL = os.getenv("TRMNL_SONOS_LABEL", "Sonos").strip()
PEOPLE_LABEL = os.getenv("TRMNL_PEOPLE_LABEL", "People").strip()
MEDIA_LABEL = os.getenv("TRMNL_MEDIA_LABEL", "Media").strip()
ENERGY_LABEL = os.getenv("TRMNL_ENERGY_LABEL", "Energy").strip()
NAV_LABELS = [e.strip() for e in os.getenv("TRMNL_NAV_LABELS", "Home,Rooms,Lights,Climate,Security,More").split(",") if e.strip()]
SIDECAR_PAYLOAD_PATH = os.getenv("TRMNL_SIDECAR_PAYLOAD_PATH", "").strip()


def load_cache() -> dict:
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache: dict) -> None:
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception as e:
        print(f"WARN cache write failed: {e}")


def fetch_entity(entity_id: str) -> dict:
    if not entity_id:
        raise ValueError("entity_id is required")
    resp = requests.get(
        f"{HA_URL}/api/states/{entity_id}",
        headers={"Authorization": f"Bearer {HA_TOKEN}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_people() -> list:
    people = []
    for eid in PERSON_ENTITIES:
        try:
            e = fetch_entity(eid)
            people.append({
                "name": e["attributes"].get("friendly_name", eid).split("'s")[0].split("'")[0],
                "state": e["state"],
            })
        except Exception as err:
            print(f"Error fetching {eid}: {err}")
            people.append({"name": eid, "state": "unknown"})
    return people


CONDITION_LABELS = {
    "partlycloudy": "Partly Cloudy",
    "clear-night": "Clear Night",
    "sunny": "Sunny",
    "cloudy": "Cloudy",
    "fog": "Foggy",
    "hail": "Hail",
    "lightning": "Lightning",
    "lightning-rainy": "Thunderstorm",
    "pouring": "Pouring Rain",
    "rainy": "Rainy",
    "snowy": "Snowy",
    "snowy-rainy": "Sleet",
    "windy": "Windy",
    "windy-variant": "Windy",
    "exceptional": "Unusual",
}


def fetch_weather() -> dict:
    try:
        e = fetch_entity(WEATHER_ENTITY)
        attrs = e["attributes"]
        raw = e["state"]
        label = CONDITION_LABELS.get(raw, raw.replace("-", " ").title())
        return {
            "condition": raw,
            "condition_label": label,
            "temperature": attrs.get("temperature"),
            "humidity": attrs.get("humidity"),
            "wind_speed": attrs.get("wind_speed"),
        }
    except Exception as err:
        print(f"Error fetching weather: {err}")
        return {}


def fetch_sonos() -> list:
    rooms = []
    for eid in SONOS_ENTITIES:
        try:
            e = fetch_entity(eid)
            if e["state"] in ("unavailable", "unknown"):
                continue

            picture = e["attributes"].get("entity_picture", "")
            if picture and picture.startswith("/"):
                picture = f"{HA_URL}{picture}"

            rooms.append({
                "room": e["attributes"].get("friendly_name", eid),
                "state": e["state"],
                "title": e["attributes"].get("media_title", ""),
                "artist": e["attributes"].get("media_artist", ""),
                "picture": picture,
            })
        except Exception:
            continue
    return rooms


def fetch_lights() -> list:
    lights = []
    for index, eid in enumerate(LIGHT_ENTITIES):
        try:
            e = fetch_entity(eid)
            state = e["state"]
            lights.append({
                "label": LIGHT_LABELS[index] if index < len(LIGHT_LABELS) else e["attributes"].get("friendly_name", eid),
                "state": state,
                "on": state == "on",
            })
        except Exception as err:
            print(f"Error fetching {eid}: {err}")
            lights.append({"label": LIGHT_LABELS[index] if index < len(LIGHT_LABELS) else eid, "state": "unknown", "on": False})
    return lights


def fetch_energy() -> dict:
    if not ENERGY_ENTITY:
        return {}
    try:
        e = fetch_entity(ENERGY_ENTITY)
        unit = e["attributes"].get("unit_of_measurement", "")
        value = e["state"]
        if value not in ("unknown", "unavailable"):
            return {
                "label": ENERGY_LABEL or e["attributes"].get("friendly_name", "Energy"),
                "value": f"{value} {unit}".strip(),
            }
    except Exception as err:
        print(f"Error fetching energy: {err}")
    return {}


def fetch_home_status(cache: dict) -> dict:
    result = {}
    cached_home = cache.get("home", {})

    try:
        door = fetch_entity(DOOR_ENTITY)
        result["door_locked"] = door["state"] == "off"  # device_class:lock — off=locked, on=unlocked
    except Exception as e:
        print(f"ERROR door: {e}")
        result["door_locked"] = cached_home.get("door_locked", None)

    try:
        washer = fetch_entity(WASHER_ENTITY)
        result["washer_running"] = washer["state"] == "on"
    except Exception as e:
        print(f"ERROR washer: {e}")
        result["washer_running"] = cached_home.get("washer_running", None)

    try:
        blind = fetch_entity(BLIND_ENTITY)
        pos = blind["attributes"].get("current_position", None)
        if pos is not None:
            result["blind_position"] = pos
            if BLIND_OPEN_POSITION:
                result["blinds_open"] = float(pos) == float(BLIND_OPEN_POSITION)
            else:
                result["blinds_open"] = blind["state"] == "open"
        else:
            raise ValueError("current_position is None")
    except Exception as e:
        print(f"ERROR blinds: {e} — using cached value")
        result["blind_position"] = cached_home.get("blind_position", "unavailable")
        result["blinds_open"] = cached_home.get("blinds_open", False)

    try:
        temp = fetch_entity(THERMOSTAT_ENTITY)
        if temp["state"] not in ("unavailable", "unknown"):
            result["thermostat_temp"] = float(
                temp["attributes"].get("current_temperature")
                or temp["attributes"].get("temperature")
                or temp["state"]
            )
        else:
            raise ValueError(f"temp state={temp['state']}")
    except Exception as e:
        print(f"ERROR temp: {e} — using cached value")
        result["thermostat_temp"] = cached_home.get("thermostat_temp", None)

    return result


def write_sidecar_payload(payload: dict) -> None:
    if not SIDECAR_PAYLOAD_PATH:
        return
    path = Path(SIDECAR_PAYLOAD_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def main() -> None:
    if not TRMNL_WEBHOOK_URL:
        raise RuntimeError("TRMNL_WEBHOOK_URL is required")
    if not HA_TOKEN:
        raise RuntimeError("HA_TOKEN is required")

    cache = load_cache()
    home = fetch_home_status(cache)

    # Update cache with any good values we got this run
    cache["home"] = {
        k: v for k, v in home.items()
        if v is not None and v != "unavailable"
    }
    save_cache(cache)

    payload = {
        "merge_variables": {
            "dashboard_title": DASHBOARD_TITLE,
            "instance_label": INSTANCE_LABEL,
            "layout_variant": LAYOUT_VARIANT,
            "colour_profile": COLOUR_PROFILE,
            "updated_at": datetime.datetime.now().strftime(TRMNL_UPDATED_AT_FORMAT),
            "labels": {
                "door": DOOR_LABEL,
                "door_detail": DOOR_DETAIL_LABEL,
                "washer": WASHER_LABEL,
                "washer_detail": WASHER_DETAIL_LABEL,
                "blinds": BLIND_LABEL,
                "blinds_detail": BLIND_DETAIL_LABEL,
                "thermostat": THERMOSTAT_LABEL,
                "thermostat_detail": THERMOSTAT_DETAIL_LABEL,
                "sonos": SONOS_LABEL,
                "people": PEOPLE_LABEL,
                "media": MEDIA_LABEL,
                "energy": ENERGY_LABEL,
            },
            "nav": NAV_LABELS[:6],
            "people": fetch_people(),
            "weather": fetch_weather(),
            "sonos": fetch_sonos(),
            "lights": fetch_lights(),
            "energy": fetch_energy(),
            "home": home,
        }
    }

    write_sidecar_payload(payload)

    resp = requests.post(TRMNL_WEBHOOK_URL, json=payload, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"Webhook failed: {resp.status_code} {resp.text}")
    print(f"OK - dashboard pushed at {payload['merge_variables']['updated_at']}")


if __name__ == "__main__":
    main()
