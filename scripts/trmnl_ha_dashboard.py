from dotenv import load_dotenv
import datetime
import json
import os
import requests

load_dotenv()

HA_URL = os.getenv("HA_URL", "http://192.168.1.89:8123").strip()
HA_TOKEN = os.getenv("HA_TOKEN", "").strip()
TRMNL_WEBHOOK_URL = os.getenv("TRMNL_WEBHOOK_URL", "").strip()
TRMNL_UPDATED_AT_FORMAT = os.getenv("TRMNL_UPDATED_AT_FORMAT", "%d %b %H:%M")
CACHE_FILE = os.getenv("TRMNL_CACHE_FILE", "/home/dave/.trmnl_ha_cache.json")

SONOS_ENTITIES = [
    "media_player.living_room",
    "media_player.bedroom",
    "media_player.kitchen",
    "media_player.gym",
    "media_player.sonos_roam",
]

PERSON_ENTITIES = [
    "person.david",
    "person.jennifer",
]


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
        e = fetch_entity("weather.forecast_home")
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


def fetch_home_status(cache: dict) -> dict:
    result = {}
    cached_home = cache.get("home", {})

    try:
        door = fetch_entity("binary_sensor.nuki_flat_door_locked")
        result["door_locked"] = door["state"] == "off"  # device_class:lock — off=locked, on=unlocked
    except Exception as e:
        print(f"ERROR door: {e}")
        result["door_locked"] = cached_home.get("door_locked", None)

    try:
        washer = fetch_entity("binary_sensor.wash_dryer_status")
        result["washer_running"] = washer["state"] == "on"
    except Exception as e:
        print(f"ERROR washer: {e}")
        result["washer_running"] = cached_home.get("washer_running", None)

    try:
        blind = fetch_entity("cover.blinds_controller_curtain")
        pos = blind["attributes"].get("current_position", None)
        if pos is not None:
            result["blind_position"] = pos
            # This controller uses inverted position: 0 = blind retracted (open), 100 = extended (closed)
            result["blinds_open"] = (pos == 0)
        else:
            raise ValueError("current_position is None")
    except Exception as e:
        print(f"ERROR blinds: {e} — using cached value")
        result["blind_position"] = cached_home.get("blind_position", "unavailable")
        result["blinds_open"] = cached_home.get("blinds_open", False)

    try:
        # Use lounge presence sensor for indoor temperature (thermostat entity unavailable)
        temp = fetch_entity("sensor.lounge_presence_device_temperature")
        if temp["state"] not in ("unavailable", "unknown"):
            result["thermostat_temp"] = float(temp["state"])
        else:
            raise ValueError(f"temp state={temp['state']}")
    except Exception as e:
        print(f"ERROR temp: {e} — using cached value")
        result["thermostat_temp"] = cached_home.get("thermostat_temp", None)

    return result


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
            "updated_at": datetime.datetime.now().strftime(TRMNL_UPDATED_AT_FORMAT),
            "people": fetch_people(),
            "weather": fetch_weather(),
            "sonos": fetch_sonos(),
            "home": home,
        }
    }

    resp = requests.post(TRMNL_WEBHOOK_URL, json=payload, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"Webhook failed: {resp.status_code} {resp.text}")
    print(f"OK - dashboard pushed at {payload['merge_variables']['updated_at']}")


if __name__ == "__main__":
    main()
