import requests
import json
import base64
import pytz
from datetime import datetime

# --- CONFIGURATION ---
BASE_URL = "https://abczaccadec.space/"
MAIN_URL = "https://abczaccadec.space/app.json"
USER_AGENT = "okhttp/4.9.0"

# --- DECRYPTION ENGINE (Universal) ---
def decrypt_cricz(encrypted_text):
    if not encrypted_text: return None
    # Logic from Smali kb/a
    src = "aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsStTuUvVwWxXyYzZ"
    target = "fFgGjJkKaApPbBmMoOzZeEnNcCdDrRqQtTvVuUxXhHiIwWyYlLsS"
    try:
        decode_map = str.maketrans(target, src)
        substituted_str = encrypted_text.translate(decode_map)
        missing_padding = len(substituted_str) % 4
        if missing_padding:
            substituted_str += '=' * (4 - missing_padding)
        return base64.b64decode(substituted_str).decode('utf-8')
    except:
        return None

# --- TIME FORMATTER (IST) ---
def get_ist_time(time_str):
    # Input formats can vary, trying to parse generic datetime
    try:
        # Example: 2026/02/07 05:30:00 +0000
        clean_time = time_str.split(" +")[0]
        for fmt in ["%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
            try:
                dt_obj = datetime.strptime(clean_time, fmt)
                utc_zone = pytz.timezone('UTC')
                ist_zone = pytz.timezone('Asia/Kolkata')
                dt_utc = utc_zone.localize(dt_obj)
                dt_ist = dt_utc.astimezone(ist_zone)
                return dt_ist.strftime("%I:%M %p %d-%b")
            except: continue
        return time_str
    except:
        return ""

# --- MAIN LOGIC ---
def generate_m3u():
    print("🚀 Starting Deep-Link Generator...")
    
    try:
        headers = {"User-Agent": USER_AGENT}
        res = requests.get(MAIN_URL, headers=headers)
        if res.status_code != 200:
            print("❌ Main JSON fetch failed")
            return

        raw_json = res.json()
        events_str = raw_json[0].get("events", "[]")
        encrypted_list = json.loads(events_str)
        
        print(f"📋 Found {len(encrypted_list)} items. Filtering Cricket...")
        playlist_entries = []
        
        for enc_item in encrypted_list:
            # Step 1: Decrypt Main Item
            dec_str = decrypt_cricz(enc_item)
            if not dec_str: continue
            
            try:
                data = json.loads(dec_str)
                # Ensure it's a list to loop through
                matches = data if isinstance(data, list) else [data]
                
                for match in matches:
                    # Step 2: STRICT CRICKET FILTER
                    # Check in multiple places to be sure
                    row_cat = match.get("category", "").lower()
                    event_info = match.get("eventInfo", {})
                    event_cat = event_info.get("eventCat", "").lower()
                    event_name = event_info.get("eventName", "").lower()
                    
                    is_cricket = "cricket" in row_cat or "cricket" in event_cat or "cricket" in event_name
                    
                    if is_cricket:
                        # Gather Info
                        title = match.get("title", "Cricket")
                        team_a = event_info.get("teamA", "")
                        team_b = event_info.get("teamB", "")
                        
                        if team_a and team_b:
                            display_title = f"{team_a} vs {team_b}"
                        else:
                            display_title = title
                            
                        logo = event_info.get("eventLogo") or match.get("categoryLogo") or ""
                        time_ist = get_ist_time(event_info.get("startTime", ""))
                        group_title = f"Live Cricket [{time_ist}]"
                        
                        print(f"   🏏 Found Match: {display_title}")

                        # Step 3: HUNT FOR LINK (The Critical Part)
                        # Priority A: Check 'links' (Inner JSON Path) - Most Reliable
                        json_path = match.get("links", "")
                        
                        found_source = False
                        
                        if json_path:
                            # Construct URL: https://abczaccadec.space/pro/match.json
                            inner_url = json_path if json_path.startswith("http") else BASE_URL + json_path
                            print(f"      -> Fetching inner JSON: {json_path}")
                            
                            try:
                                inner_res = requests.get(inner_url, headers=headers)
                                if inner_res.status_code == 200:
                                    stream_data = None
                                    # Try Decrypting (Inner JSON is often encrypted too)
                                    dec_inner = decrypt_cricz(inner_res.text)
                                    if dec_inner:
                                        stream_data = json.loads(dec_inner)
                                    else:
                                        # If not encrypted, try raw
                                        try: stream_data = inner_res.json()
                                        except: pass
                                    
                                    if stream_data:
                                        # Handle 'streamUrls' list inside inner JSON
                                        streams = stream_data.get("streamUrls", [])
                                        # Sometimes it's just a direct dict or list
                                        if not streams and isinstance(stream_data, list): streams = stream_data
                                        if not streams and isinstance(stream_data, dict): streams = [stream_data]

                                        for s in streams:
                                            final_link = s.get("link") or s.get("url") or s.get("webLink")
                                            drm_key = s.get("api", "") # ClearKey
                                            s_name = s.get("title", "Stream")
                                            
                                            if final_link:
                                                entry = f'#EXTINF:-1 group-title="{group_title}" tvg-logo="{logo}", {display_title} ({s_name})\n'
                                                if drm_key:
                                                    entry += '#KODIPROP:inputstream.adaptive.license_type=clearkey\n'
                                                    entry += f'#KODIPROP:inputstream.adaptive.license_key={drm_key}\n'
                                                entry += f'{final_link}\n'
                                                playlist_entries.append(entry)
                                                found_source = True
                            except Exception as e:
                                print(f"      -> Inner fetch error: {e}")

                        # Priority B: Check 'formats' (Direct Links in Main JSON) - Backup
                        # Only if Inner JSON failed or didn't exist
                        if not found_source:
                            formats = match.get("formats", [])
                            for fmt in formats:
                                web_link = fmt.get("webLink", "")
                                if web_link:
                                    entry = f'#EXTINF:-1 group-title="{group_title}" tvg-logo="{logo}", {display_title} (Direct)\n'
                                    entry += f'{web_link}\n'
                                    playlist_entries.append(entry)
                                    found_source = True

            except Exception:
                continue

        # Save M3U
        with open("cricket.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f"#EXTINF:-1 logo=\"https://i.ibb.co/7xz4z0k2/Cricket.png\" group-title=\"Info\", Last Update: {datetime.now().strftime('%d-%b %H:%M IST')}\n")
            f.write("http://fake.url/info\n\n")
            
            if playlist_entries:
                for line in playlist_entries:
                    f.write(line + "\n")
            else:
                f.write("#EXTINF:-1, No Live Cricket Found\nhttp://fake.url/empty\n")
        
        print(f"✅ Finished. Saved {len(playlist_entries)} streams.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    generate_m3u()

