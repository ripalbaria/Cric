import requests
import json
import base64
import pytz
from datetime import datetime, timedelta
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

# --- NETWORK SESSION ---
def get_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session

# --- TIME PARSER ---
def parse_dt(date_str):
    if not date_str: return None
    clean_str = date_str.split(" +")[0].strip()
    formats = ["%Y/%m/%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S"]
    for fmt in formats:
        try:
            return datetime.strptime(clean_str, fmt).replace(tzinfo=pytz.utc)
        except ValueError: continue
    return None

# --- STATUS ENGINE ---
def get_status(start_str, end_str):
    try:
        start_dt = parse_dt(start_str)
        end_dt = parse_dt(end_str)
        if not end_dt and start_dt: end_dt = start_dt + timedelta(hours=6)
        if not start_dt: return "Unknown"
        
        now = datetime.now(pytz.utc)
        
        if now < start_dt: return "UPCOMING"
        elif start_dt <= now <= end_dt: return "LIVE 🔴"
        else: return "FINISHED"
    except: return "Unknown"

# --- MAIN GENERATOR ---
def generate_m3u():
    print("🚀 Starting Match-Group Generator...")
    session = get_session()
    playlist_entries = []
    
    try:
        res = session.get(MAIN_URL, timeout=15)
        if res.status_code != 200: return

        raw_json = res.json()
        events_str = raw_json[0].get("events", "[]")
        encrypted_list = json.loads(events_str)
        
        print(f"📋 Scanning {len(encrypted_list)} items...")
        
        for enc_item in encrypted_list:
            dec_str = decrypt_cricz(enc_item)
            if not dec_str: continue
            
            try:
                data = json.loads(dec_str)
                matches = data if isinstance(data, list) else [data]
                
                for match in matches:
                    # 1. FILTER: Cricket Only
                    evt_info = match.get("eventInfo", {})
                    raw_cat = match.get("category", "").lower()
                    evt_name = match.get("eventName", "")
                    evt_type = evt_info.get("eventType", match.get("title", ""))
                    
                    is_cricket = "cricket" in raw_cat or "cricket" in evt_name.lower() or "cricket" in evt_type.lower()
                    if not is_cricket: continue

                    # 2. MATCH INFO
                    team_a = match.get("teamAName") or evt_info.get("teamA", "")
                    team_b = match.get("teamBName") or evt_info.get("teamB", "")
                    
                    if team_a and team_b:
                        match_title = f"{team_a} vs {team_b}"
                    else:
                        match_title = evt_name or "Cricket Match"
                        
                    logo = match.get("teamAFlag") or evt_info.get("eventLogo") or ""
                    
                    # 3. TIME & STATUS
                    date_part = match.get("date", "")
                    time_part = match.get("time", "")
                    if date_part and time_part: start_time = f"{date_part} {time_part}"
                    else: start_time = evt_info.get("startTime", "")
                    end_time = evt_info.get("endTime", "")
                    
                    status = get_status(start_time, end_time)
                    
                    # 4. GROUP NAME LOGIC (User Request: Group = Match Name)
                    # Convert time to IST for cleaner title
                    try:
                        dt_obj = parse_dt(start_time)
                        if dt_obj:
                            ist_str = dt_obj.astimezone(pytz.timezone('Asia/Kolkata')).strftime("%d %b %I:%M %p")
                            # Group Name: "LIVE 🔴 | RCB vs DC [05 Feb 07:30 PM]"
                            group_title = f"{status} | {match_title} [{ist_str}]"
                        else:
                            group_title = f"{status} | {match_title}"
                    except:
                        group_title = f"{status} | {match_title}"

                    print(f"   🏏 Processing Group: {group_title}")

                    # 5. FETCH LINKS
                    found_source = False
                    
                    # Helper to add entry
                    def add_entry(url, name, drm=""):
                        # Entry Title: Just the Link Name (e.g. "Willow HD")
                        # Folder already tells which match it is.
                        entry = f'#EXTINF:-1 group-title="{group_title}" tvg-logo="{logo}", {name}\n'
                        if drm:
                            entry += '#KODIPROP:inputstream.adaptive.license_type=clearkey\n'
                            entry += f'#KODIPROP:inputstream.adaptive.license_key={drm}\n'
                        entry += f'{url}\n'
                        playlist_entries.append(entry)

                    # Method A: Inner JSON
                    json_path = match.get("links")
                    if json_path:
                        target_url = json_path if json_path.startswith("http") else BASE_URL + json_path
                        try:
                            inner_res = session.get(target_url, timeout=10)
                            if inner_res.status_code == 200:
                                try: inner_data = inner_res.json()
                                except: inner_data = json.loads(decrypt_cricz(inner_res.text))
                                
                                final_streams = []
                                if isinstance(inner_data, dict) and "links" in inner_data and isinstance(inner_data["links"], str):
                                    hidden_dec = decrypt_cricz(inner_data["links"])
                                    if hidden_dec: final_streams = json.loads(hidden_dec)
                                elif isinstance(inner_data, list):
                                    final_streams = inner_data
                                elif isinstance(inner_data, dict):
                                    final_streams = inner_data.get("streamUrls", inner_data.get("channels", [inner_data]))

                                if isinstance(final_streams, dict): final_streams = [final_streams]
                                
                                for s in final_streams:
                                    u = s.get("link") or s.get("url") or s.get("file")
                                    d = s.get("api") or s.get("drm_key") or s.get("tokenApi")
                                    n = s.get("name") or s.get("title", "Stream")
                                    if u:
                                        add_entry(u, n, d)
                                        found_source = True
                        except: pass

                    # Method B: Direct Formats
                    if not found_source:
                        formats = match.get("formats", [])
                        for fmt in formats:
                            u = fmt.get("webLink", "")
                            n = fmt.get("title", "Direct Link")
                            if u:
                                add_entry(u, n)

            except Exception: continue

        # --- SAVE M3U ---
        with open("cricket.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            if playlist_entries:
                for line in playlist_entries:
                    f.write(line + "\n")
            else:
                f.write("#EXTINF:-1 group-title=\"Bot Status\", No Cricket Found\nhttp://fake.url/empty\n")
        
        print(f"✅ Success! Saved {len(playlist_entries)} streams.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    generate_m3u()

