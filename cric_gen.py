import requests
import json
import base64
import pytz
from datetime import datetime

# --- CONFIGURATION ---
BASE_URL = "https://abczaccadec.space/"
MAIN_URL = "https://abczaccadec.space/app.json"
USER_AGENT = "okhttp/4.9.0"

# --- DECRYPTION ENGINE ---
def decrypt_cricz(encrypted_text):
    if not encrypted_text: return None
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

# --- TIME FORMATTER ---
def get_ist_time(date_str, time_str):
    try:
        full_str = f"{date_str} {time_str}"
        dt_obj = datetime.strptime(full_str, "%d/%m/%Y %H:%M:%S")
        utc_zone = pytz.timezone('UTC')
        ist_zone = pytz.timezone('Asia/Kolkata')
        dt_utc = utc_zone.localize(dt_obj)
        dt_ist = dt_utc.astimezone(ist_zone)
        return dt_ist.strftime("%I:%M %p")
    except:
        return f"{time_str}"

# --- MAIN LOGIC ---
def generate_m3u():
    print("🚀 Starting Generator (Fix: Links + Formats)...")
    
    try:
        headers = {"User-Agent": USER_AGENT}
        res = requests.get(MAIN_URL, headers=headers)
        if res.status_code != 200: return

        raw_json = res.json()
        events_str = raw_json[0].get("events", "[]")
        encrypted_list = json.loads(events_str)
        
        print(f"📋 Processing {len(encrypted_list)} items...")
        playlist_entries = []
        
        for enc_item in encrypted_list:
            dec_str = decrypt_cricz(enc_item)
            if not dec_str: continue
            
            try:
                data = json.loads(dec_str)
                matches = data if isinstance(data, list) else [data]
                
                for match in matches:
                    # Filter: Cricket Only
                    cat = match.get("category", "").lower()
                    title = match.get("eventName", "").lower()
                    
                    if "cricket" in cat or "cricket" in title or "ipl" in title or "cup" in title:
                        
                        # Info
                        event_name = match.get("eventName", "Cricket")
                        team_a = match.get("teamAName", "")
                        team_b = match.get("teamBName", "")
                        display_title = f"{team_a} vs {team_b} - {event_name}" if team_a and team_b else event_name
                        logo = match.get("teamAFlag", match.get("categoryLogo", ""))
                        
                        time_ist = get_ist_time(match.get("date", ""), match.get("time", ""))
                        group_title = f"Live Cricket [{time_ist}]"
                        
                        # --- STRATEGY 1: Check 'links' (Inner JSON) ---
                        json_path = match.get("links", "")
                        link_found = False
                        
                        if json_path:
                            inner_url = json_path if json_path.startswith("http") else BASE_URL + json_path
                            try:
                                inner_res = requests.get(inner_url, headers=headers)
                                if inner_res.status_code == 200:
                                    stream_data = None
                                    try:
                                        stream_data = inner_res.json()
                                    except:
                                        dec_inner = decrypt_cricz(inner_res.text)
                                        if dec_inner: stream_data = json.loads(dec_inner)
                                    
                                    if stream_data:
                                        # Handle List or Object inside inner JSON
                                        streams = stream_data if isinstance(stream_data, list) else [stream_data]
                                        for s in streams:
                                            url = s.get("link", s.get("url", ""))
                                            drm = s.get("api", "")
                                            name = s.get("title", "Stream")
                                            
                                            if url:
                                                ent = f'#EXTINF:-1 group-title="{group_title}" tvg-logo="{logo}", {display_title} ({name})\n'
                                                if drm:
                                                    ent += '#KODIPROP:inputstream.adaptive.license_type=clearkey\n'
                                                    ent += f'#KODIPROP:inputstream.adaptive.license_key={drm}\n'
                                                ent += f'{url}\n'
                                                playlist_entries.append(ent)
                                                link_found = True
                            except:
                                pass

                        # --- STRATEGY 2: Check 'formats' (Direct Links) if Strategy 1 failed/skipped ---
                        # (Sometimes matches have both, so we can check formats regardless)
                        formats = match.get("formats", [])
                        if formats:
                            for fmt in formats:
                                url = fmt.get("webLink", "")
                                name = fmt.get("title", "Direct Stream")
                                
                                if url:
                                    ent = f'#EXTINF:-1 group-title="{group_title}" tvg-logo="{logo}", {display_title} ({name})\n'
                                    ent += f'{url}\n'
                                    playlist_entries.append(ent)
                                    link_found = True

            except Exception:
                continue

        # Save
        with open("cricket.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f"#EXTINF:-1 logo=\"https://i.ibb.co/7xz4z0k2/Cricket.png\" group-title=\"Info\", Last Update: {datetime.now().strftime('%H:%M IST')}\n")
            f.write("http://fake.url/info\n\n")
            for line in playlist_entries:
                f.write(line + "\n")
        
        print(f"✅ Saved {len(playlist_entries)} streams.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    generate_m3u()

