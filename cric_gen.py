import requests
import json
import base64
import time
import pytz
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# --- CONFIGURATION ---
BASE_URL = "https://abczaccadec.space/"
MAIN_URL = "https://abczaccadec.space/app.json"
USER_AGENT = "okhttp/4.9.2"

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

# --- ROBUST NETWORK SESSION (Anti-Block) ---
def get_session():
    session = requests.Session()
    # 3 Retries agar server connection kaat de
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    })
    return session

# --- TIME FORMATTER (IST) ---
def get_ist_time(time_str):
    try:
        clean_time = time_str.split(" +")[0]
        # Common formats check
        for fmt in ["%Y/%m/%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
            try:
                dt_obj = datetime.strptime(clean_time, fmt)
                utc_zone = pytz.timezone('UTC')
                ist_zone = pytz.timezone('Asia/Kolkata')
                dt_utc = utc_zone.localize(dt_obj)
                dt_ist = dt_utc.astimezone(ist_zone)
                return dt_ist.strftime("%I:%M %p %d-%b")
            except: continue
        return time_str
    except: return ""

# --- MAIN GENERATOR ---
def generate_m3u():
    print("🚀 Starting Universal Cricket Generator...")
    session = get_session()
    playlist_entries = []
    
    try:
        # 1. Fetch Main List
        res = session.get(MAIN_URL, timeout=15)
        if res.status_code != 200: return

        raw_json = res.json()
        events_str = raw_json[0].get("events", "[]")
        encrypted_list = json.loads(events_str)
        
        print(f"📋 Scanning {len(encrypted_list)} items for Cricket...")
        
        for enc_item in encrypted_list:
            # Level 1 Decrypt
            dec_str = decrypt_cricz(enc_item)
            if not dec_str: continue
            
            try:
                data = json.loads(dec_str)
                matches = data if isinstance(data, list) else [data]
                
                for match in matches:
                    # --- UNIVERSAL FILTER ---
                    # Naam pata ho ya na ho, agar 'Cricket' hai to utha lo
                    # Check in Category, EventName, EventType
                    raw_cat = match.get("category", "").lower()
                    evt_name = match.get("eventName", "") # Check original case later
                    evt_info = match.get("eventInfo", {})
                    evt_type = evt_info.get("eventType", "").lower()
                    
                    is_cricket = "cricket" in raw_cat or "cricket" in evt_name.lower() or "cricket" in evt_type
                    
                    if is_cricket:
                        # Info Extraction
                        team_a = match.get("teamAName") or evt_info.get("teamA", "")
                        team_b = match.get("teamBName") or evt_info.get("teamB", "")
                        
                        if team_a and team_b:
                            title = f"{team_a} vs {team_b}"
                        else:
                            title = evt_name or "Cricket Match"
                            
                        logo = match.get("teamAFlag") or evt_info.get("eventLogo") or ""
                        
                        # Time
                        time_val = match.get("date", "") + " " + match.get("time", "")
                        if len(time_val) < 5: time_val = evt_info.get("startTime", "")
                        
                        ist_time = get_ist_time(time_val)
                        group_title = f"Live Cricket [{ist_time}]" if ist_time else "Live Cricket"

                        print(f"   🏏 Processing: {title}")
                        
                        # --- DEEP LINK EXTRACTION STRATEGY ---
                        found_source = False
                        
                        # PATH A: 'links' key (The Hidden Layer Route)
                        json_path = match.get("links")
                        if json_path:
                            target_url = json_path if json_path.startswith("http") else BASE_URL + json_path
                            try:
                                inner_res = session.get(target_url, timeout=15)
                                if inner_res.status_code == 200:
                                    # Level 2 Decrypt: File content
                                    try:
                                        inner_data = inner_res.json()
                                    except:
                                        inner_data = json.loads(decrypt_cricz(inner_res.text))
                                    
                                    # Level 3 Decrypt: HIDDEN LAYER CHECK
                                    # Agar 'links' key ke andar ek encrypted string hai (W3UogcP...)
                                    final_streams = []
                                    if isinstance(inner_data, dict) and "links" in inner_data and isinstance(inner_data["links"], str):
                                        # Decrypt the hidden blob
                                        hidden_dec = decrypt_cricz(inner_data["links"])
                                        if hidden_dec:
                                            final_streams = json.loads(hidden_dec) # Yahan milta hai asli khazana
                                    
                                    # Fallback: Agar hidden layer nahi hai, to direct list use karo
                                    elif isinstance(inner_data, list):
                                        final_streams = inner_data
                                    elif isinstance(inner_data, dict):
                                        # Keys like 'streamUrls' or 'channels'
                                        final_streams = inner_data.get("streamUrls", inner_data.get("channels", [inner_data]))

                                    # --- PROCESS FINAL STREAMS ---
                                    # Ensure it is a list
                                    if isinstance(final_streams, dict): final_streams = [final_streams]
                                    
                                    for s in final_streams:
                                        # Keys can be 'link', 'url', 'file'
                                        stream_url = s.get("link") or s.get("url") or s.get("file")
                                        drm_key = s.get("api") or s.get("drm_key") or s.get("tokenApi") # ClearKey
                                        name = s.get("name") or s.get("title", "Stream")
                                        
                                        if stream_url:
                                            entry = f'#EXTINF:-1 group-title="{group_title}" tvg-logo="{logo}", {title} ({name})\n'
                                            if drm_key:
                                                entry += '#KODIPROP:inputstream.adaptive.license_type=clearkey\n'
                                                entry += f'#KODIPROP:inputstream.adaptive.license_key={drm_key}\n'
                                            entry += f'{stream_url}\n'
                                            playlist_entries.append(entry)
                                            found_source = True
                            except Exception as e:
                                print(f"      ⚠️ Inner fetch error: {e}")

                        # PATH B: 'formats' key (Backup for simple matches)
                        if not found_source:
                            formats = match.get("formats", [])
                            for fmt in formats:
                                url = fmt.get("webLink", "")
                                if url:
                                    entry = f'#EXTINF:-1 group-title="{group_title}" tvg-logo="{logo}", {title} (Direct)\n'
                                    entry += f'{url}\n'
                                    playlist_entries.append(entry)

            except Exception: continue

        # --- SAVE M3U ---
        with open("cricket.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f"#EXTINF:-1 logo=\"https://i.ibb.co/7xz4z0k2/Cricket.png\" group-title=\"Info\", Updated: {datetime.now().strftime('%d-%b %H:%M IST')}\n")
            f.write("http://fake.url/info\n\n")
            
            if playlist_entries:
                for line in playlist_entries:
                    f.write(line + "\n")
            else:
                f.write("#EXTINF:-1, No Live Cricket Found\nhttp://fake.url/empty\n")
        
        print(f"✅ Success! Saved {len(playlist_entries)} streams to cricket.m3u")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    generate_m3u()

