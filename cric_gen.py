import requests
import json
import base64
import os
from datetime import datetime, timedelta

# --- Configuration ---
MAIN_URL = "https://abczaccadec.space/app.json"
BASE_URL = "https://abczaccadec.space/"
USER_AGENT = "okhttp/4.9.0"

# --- Decryption Logic (The "Key" you found) ---
def decrypt_cricz(encrypted_text):
    # Maps from Smali
    src = "aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsStTuUvVwWxXyYzZ"
    target = "fFgGjJkKaApPbBmMoOzZeEnNcCdDrRqQtTvVuUxXhHiIwWyYlLsS"
    
    try:
        decode_map = str.maketrans(target, src)
        substituted_str = encrypted_text.translate(decode_map)
        
        # Fix padding
        missing_padding = len(substituted_str) % 4
        if missing_padding:
            substituted_str += '=' * (4 - missing_padding)
            
        return base64.b64decode(substituted_str).decode('utf-8')
    except Exception:
        return None

# --- Helper: Convert Time to IST ---
def get_ist_time(date_str):
    # Example Input: 07/02/2026 05:30:00
    try:
        # Parse assuming UTC or Server Time. Adjust logic if server is already IST.
        # Assuming the date format in JSON is DD/MM/YYYY HH:MM:SS
        dt_obj = datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S")
        # If server time is UTC, add 5h 30m for IST
        # If server time is already IST, remove the timedelta line
        # Based on logs, it often looks like UTC. Let's add IST offset.
        ist_time = dt_obj # + timedelta(hours=5, minutes=30) 
        return ist_time.strftime("%I:%M %p %d-%b")
    except:
        return date_str

# --- Main Generator ---
def generate_playlist():
    print(f"[*] Connecting to Server...")
    
    try:
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(MAIN_URL, headers=headers)
        
        if response.status_code != 200:
            print("Server error")
            return

        raw_json = response.json()
        if not isinstance(raw_json, list) or len(raw_json) == 0:
            return

        # 1. Extract and Parse the 'events' string
        events_string = raw_json[0].get("events", "[]")
        events_list = json.loads(events_string)
        
        print(f"[*] Found {len(events_list)} total events. Processing...")

        m3u_content = ["#EXTM3U"]
        m3u_content.append('#EXTINF:-1 logo="https://i.ibb.co/7xz4z0k2/Cricket.png" group-title="Info", Auto-Updated Playlist')
        m3u_content.append("http://fake.url/info")

        for encrypted_data in events_list:
            # 2. Decrypt Event
            decrypted_str = decrypt_cricz(encrypted_data)
            
            if decrypted_str:
                try:
                    data = json.loads(decrypted_str)
                    
                    # Ensure it's a list for iteration
                    matches = data if isinstance(data, list) else [data]
                    
                    for match in matches:
                        # 3. Filter for CRICKET
                        cat = match.get("category", "").lower()
                        event_name = match.get("eventName", "").lower()
                        
                        if "cricket" in cat or "cricket" in event_name:
                            
                            # Basic Info
                            title = match.get("eventName", "Cricket Match")
                            team_a = match.get("teamAName", "")
                            team_b = match.get("teamBName", "")
                            match_title = f"{team_a} vs {team_b}" if team_a and team_b else title
                            
                            logo = match.get("teamAFlag", match.get("categoryLogo", ""))
                            
                            # Time Handling
                            raw_date = match.get("date", "")
                            raw_time = match.get("time", "")
                            full_time_str = f"{raw_date} {raw_time}"
                            formatted_time = get_ist_time(full_time_str)
                            
                            # Group Title with Time (As requested)
                            group_name = f"Live Cricket ({formatted_time})"

                            # 4. Handle Inner JSON Links ("links" field)
                            json_link = match.get("links", "")
                            
                            if json_link:
                                # Construct full URL
                                target_url = json_link if json_link.startswith("http") else BASE_URL + json_link
                                print(f"   -> Fetching inner JSON: {target_url}")
                                
                                try:
                                    inner_res = requests.get(target_url, headers=headers)
                                    inner_data = None
                                    
                                    # Try decrypting inner data first (Consistency)
                                    if inner_res.status_code == 200:
                                        # Often inner data is also encrypted or raw JSON
                                        # Let's try raw JSON first
                                        try:
                                            inner_data = inner_res.json()
                                        except:
                                            # If raw json fails, try decrypting string
                                            decrypted_inner = decrypt_cricz(inner_res.text)
                                            if decrypted_inner:
                                                inner_data = json.loads(decrypted_inner)
                                    
                                    if inner_data:
                                        # Extract stream info from inner JSON
                                        # Assuming inner JSON has a 'link' or 'stream_url'
                                        # Adjust keys based on actual inner json structure
                                        stream_link = inner_data.get("link", inner_data.get("url", ""))
                                        drm_key = inner_data.get("api", "") # USER SAID: API IS CLEARKEY
                                        
                                        if stream_link:
                                            # Write to M3U
                                            header = f'#EXTINF:-1 group-title="{group_name}" tvg-logo="{logo}", {match_title}'
                                            m3u_content.append(header)
                                            
                                            # Add DRM Headers if 'api' key exists
                                            if drm_key:
                                                m3u_content.append('#KODIPROP:inputstream.adaptive.license_type=clearkey')
                                                m3u_content.append(f'#KODIPROP:inputstream.adaptive.license_key={drm_key}')
                                            
                                            m3u_content.append(stream_link)

                                except Exception as e:
                                    print(f"Error fetching inner JSON: {e}")

                            # 5. Handle Direct Links ('formats' array) if inner link failed or doesn't exist
                            # (Add logic here if 'formats' are prioritized)

                except Exception as e:
                    pass
        
        # Save File
        with open("cricket.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_content))
        
        print("[*] Playlist 'cricket.m3u' generated successfully!")

    except Exception as e:
        print(f"[!] Critical Error: {e}")

if __name__ == "__main__":
    generate_playlist()

