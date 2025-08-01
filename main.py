import requests
import os
import json
from datetime import datetime, timezone, timedelta

# --- Configuration ---
# Coordinates for In Buri District, Sing Buri Province
LATITUDE = 15.0273
LONGITUDE = 100.3444

# Notification thresholds and settings
HEAT_THRESHOLD = 35.0  # (องศาเซลเซียส) อุณหภูมิที่ถือว่าร้อนจัด
HEAVY_RAIN_CODES = {80, 81, 82, 95, 96, 99} # WMO Codes for Rain Showers / Thunderstorms

# APIs
OPEN_METEO_API_URL = "https://api.open-meteo.com/v1/forecast"
LINE_BROADCAST_API_URL = "https://api.line.me/v2/bot/message/broadcast"

# State file to track notifications
STATE_FILE = "notification_state.json"

def get_bangkok_time():
    """Returns the current time in Asia/Bangkok timezone."""
    return datetime.now(timezone(timedelta(hours=7)))

def read_notification_state():
    """Reads the notification state from the JSON file."""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def write_notification_state(state):
    """Writes the notification state to the JSON file."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def get_weather_data():
    """Fetches weather data from Open-Meteo API for the next 24 hours."""
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "temperature_2m,weather_code",
        "daily": "temperature_2m_max",
        "timezone": "Asia/Bangkok",
        "forecast_days": 1
    }
    try:
        response = requests.get(OPEN_METEO_API_URL, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

def send_line_broadcast(message):
    """Sends a broadcast message to LINE OA."""
    line_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    if not line_token:
        print("Error: LINE_CHANNEL_ACCESS_TOKEN is not set in GitHub Secrets.")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {line_token}"
    }
    data = {"messages": [{"type": "text", "text": message}]}
    try:
        response = requests.post(LINE_BROADCAST_API_URL, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        print("LINE broadcast sent successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending LINE broadcast: {e}")
        print(f"Response: {e.response.text}")

def check_weather_conditions():
    """Checks weather data and sends notifications if conditions are met."""
    current_time = get_bangkok_time()
    today_str = current_time.strftime("%Y-%m-%d")
    print(f"Running weather check for {today_str} at {current_time.strftime('%H:%M:%S')}")

    weather_data = get_weather_data()
    if not weather_data:
        print("Could not retrieve weather data. Exiting.")
        return

    state = read_notification_state()

    # --- Initialize state keys if they don't exist ---
    if "notified_heat_dates" not in state:
        state["notified_heat_dates"] = []
    if "notified_rain_events" not in state:
        state["notified_rain_events"] = []

    # --- Clean up old notifications from the state file ---
    state["notified_heat_dates"] = [d for d in state["notified_heat_dates"] if d == today_str]
    state["notified_rain_events"] = [e for e in state["notified_rain_events"] if e.startswith(today_str)]

    # --- 1. Check for Extreme Heat ---
    max_temp = weather_data.get("daily", {}).get("temperature_2m_max", [None])[0]
    if max_temp and max_temp >= HEAT_THRESHOLD:
        if today_str not in state["notified_heat_dates"]:
            message = (
                f"อินทร์บุรีวันนี้... แดดแรงเหมือนโกรธใครมา! 🥵\n\n"
                f"อุณหภูมิสูงสุดพุ่งไปถึง {max_temp}°C เลยนะ ออกไปไหนพกน้ำเย็นๆ ไปจิบด้วยเด้อ เดี๋ยวจะสุกเอา! 🍳"
            )
            send_line_broadcast(message)
            state["notified_heat_dates"].append(today_str)
        else:
            print(f"Heat notification for {today_str} already sent. Skipping.")

    # --- 2. Check for Heavy Rain in the next hours ---
    hourly_data = weather_data.get("hourly", {})
    hourly_times = hourly_data.get("time", [])
    hourly_codes = hourly_data.get("weather_code", [])

    if not (hourly_times and hourly_codes):
        print("Hourly data is missing. Skipping rain check.")
        write_notification_state(state)
        return

    try:
        current_hour_str = current_time.strftime("%Y-%m-%dT%H:00")
        start_index = hourly_times.index(current_hour_str)
    except ValueError:
        print("Current hour not found in forecast data. Skipping rain check.")
        write_notification_state(state)
        return

    for i in range(start_index, len(hourly_codes)):
        forecast_time_str = hourly_times[i]
        if hourly_codes[i] in HEAVY_RAIN_CODES:
            if forecast_time_str not in state["notified_rain_events"]:
                rain_time_formatted = datetime.fromisoformat(forecast_time_str).strftime("%H:%M")
                message = (
                    f"ชาวอินทร์บุรี! ⛈️ เย็นนี้เมฆเหมือนจะตั้งตี้สาดน้ำกันเลย!\n\n"
                    f"มีแววว่าฝนจะเทลงมาช่วงประมาณ {rain_time_formatted} น. พกร่มไปด้วยนะ เดี๋ยวตัวเปียก! 😎"
                )
                send_line_broadcast(message)
                state["notified_rain_events"].append(forecast_time_str)
            else:
                print(f"Rain notification for event at {forecast_time_str} already sent. Skipping.")

    write_notification_state(state)
    print("Weather check complete.")

if __name__ == "__main__":
    check_weather_conditions()
