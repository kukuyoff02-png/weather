
import requests
import os
import json
import time
from datetime import datetime, timedelta
from config import LATITUDE, LONGITUDE, HEAT_THRESHOLD, HEAVY_RAIN_CODES, RAIN_NOTIFICATION_INTERVAL, HEAT_NOTIFICATION_INTERVAL, OPEN_METEO_API_URL, LINE_BROADCAST_API_URL, CHECK_INTERVAL

# Global variable to track last notification times
last_rain_notification = None
last_heat_notification = None

def get_weather_data():
    """Fetches weather data from Open-Meteo API."""
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "temperature_2m,weather_code,precipitation,precipitation_probability",
        "daily": "temperature_2m_max,weather_code",
        "timezone": "Asia/Bangkok",
        "forecast_days": 1
    }
    try:
        response = requests.get(OPEN_METEO_API_URL, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

def send_line_broadcast(message):
    """Sends a broadcast message to LINE OA."""
    print(f"[MOCK] Sending LINE broadcast: {message}")
    # if not LINE_CHANNEL_ACCESS_TOKEN:
    #     print("LINE_CHANNEL_ACCESS_TOKEN is not set. Cannot send LINE message.")
    #     return

    # headers = {
    #     "Content-Type": "application/json",
    #     "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    # }
    # data = {
    #     "messages": [
    #         {
    #             "type": "text",
    #             "text": message
    #         }
    #     ]
    # }
    # try:
    #     response = requests.post(LINE_BROADCAST_API_URL, headers=headers, data=json.dumps(data))
    #     response.raise_for_status()
    #     print("LINE broadcast sent successfully.")
    # except requests.exceptions.RequestException as e:
    #     print(f"Error sending LINE broadcast: {e}")

def check_weather_conditions(weather_data):
    global last_rain_notification, last_heat_notification
    current_time = datetime.now()

    if not weather_data:
        return

    # Check for extreme heat
    daily_data = weather_data.get("daily", {})
    max_temp = daily_data.get("temperature_2m_max")
    if max_temp and max_temp[0] >= HEAT_THRESHOLD:
        if not last_heat_notification or (current_time - last_heat_notification).total_seconds() >= HEAT_NOTIFICATION_INTERVAL:
            send_line_broadcast(f"\u2600\uFE0F \uD83D\uDD25 อากาศร้อนจัด! อุณหภูมิสูงสุดวันนี้ {max_temp[0]} \u00B0C โปรดระวังสุขภาพด้วยนะคะ")
            last_heat_notification = current_time

    # Check for heavy rain
    hourly_data = weather_data.get("hourly", {})
    hourly_weather_codes = hourly_data.get("weather_code")
    hourly_times = hourly_data.get("time")

    if hourly_weather_codes and hourly_times:
        current_hour_str = current_time.strftime("%Y-%m-%dT%H:00")
        try:
            current_hour_index = hourly_times.index(current_hour_str)
        except ValueError:
            print("Current hour not found in hourly data.")
            return

        for i in range(current_hour_index, min(current_hour_index + 3, len(hourly_weather_codes))):
            weather_code = hourly_weather_codes[i]
            if weather_code in HEAVY_RAIN_CODES:
                if not last_rain_notification or (current_time - last_rain_notification).total_seconds() >= RAIN_NOTIFICATION_INTERVAL:
                    send_line_broadcast(f"\u2614\uFE0F \uD83C\uDF27\uFE0F ฝนกำลังจะตกหนักในอีกไม่กี่ชั่วโมงข้างหน้า! โปรดเตรียมตัวด้วยนะคะ")
                    last_rain_notification = current_time
def main():
    print("Starting weather bot...")
    while True:
        weather_data = get_weather_data()
        check_weather_conditions(weather_data)
        print(f"Waiting for {CHECK_INTERVAL / 60} minutes...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()