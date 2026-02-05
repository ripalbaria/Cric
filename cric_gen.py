import requests
import json
import base64
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

# --- NETWORK SESSION ---
def get_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session

# --- STATUS ENGINE (Live/Upcoming/Finished) ---
def get_status_data(start_str, end_str, event_type):
    try:
        # Format: 2026/02/05 03:00:00 +0000
        fmt = "%Y/%m/%d %H:%M:%S"
        
        # Clean strings
        s_clean = start_str.split(" +")[0]
        e_clean = end_str.split(" +")[0]
        
        # Parse to UTC
        start_dt = datetime.strptime(s_clean, fmt).replace(tzinfo=pytz.utc)
        end_dt = datetime.strptime(e_clean, fmt).replace(tzinfo=pytz.utc)
        
        # Current UTC Time
        now = datetime.now(pytz.utc)
        
        if now < start_dt:
            status = "Upcoming"
        elif start_dt <= now <= end_dt:
            status = "LIVE"
        else:
            status = "Finished"
            
        # Tournament Name Cleaning
        tourn_name = event_type.replace(",", "").strip()
        group_title = f"{status} | {tourn_name}"
        
        return group_title, status
    except:
        # Fallback agar date parsing fail ho
        return f"Check Status | {event_type}", "Unknown"

# --- MAIN GENERATOR ---
def generate_m3u():
    print("🚀 Starting Safe-Mode Generator...")
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
                    # --- 1. STRICT FILTERING (Sirf Cricket) ---
                    evt_info = match.get("eventInfo", {})
                    raw_cat = match.get("category", "").lower()
                    evt_name = match.get("eventName", "")
                    # "eventType" mein aksar tournament ka naam hota hai (e.g. ICC U19)
                    evt_type = evt_info.get("eventType", match.get("title", ""))
                    
                    # Check keywords
                    is_cricket = "cricket" in raw_cat or "cricket" in evt_name.lower() or "cricket" in evt_type.lower()
                    
                    # Agar Cricket nahi hai, to skip karo (Safe Filter)
                    if not is_cricket:
                        continue

                    # --- 2. MATCH INFO ---
                    team_a = match.get("teamAName") or evt_info.get("teamA", "")
                    team_b = match.get("teamBName") or evt_info.get("teamB", "")
                    
                    if team_a and team_b:
                        base_title = f"{team_a} vs {team_b}"
                    else:
                        base_title = evt_name or "Cricket Match"
                        
                    logo = match.get("teamAFlag") or evt_info.get("eventLogo") or ""
                    
                    # --- 3. STATUS LOGIC (Time Check) ---
                    start_time = match.get("date", "") + " " + match.get("time", "")
                    if len(start_time) < 5: start_time = evt_info.get("startTime", "")
                    end_time = evt_info.get("endTime", "")
                    
                    # Yahan se Group Name aur Status milega
                    group_title, status_tag = get_status_data(start_time, end_time, evt_type)

                    # --- 4. TITLE FORMATTING (Date/Time dikhana) ---
                    try:
                        s_clean = start_time.split(" +")[0]
                        dt_obj = datetime.strptime(s_clean, "%Y/%m/%d %H:%M:%S")
                        ist_time = dt_obj.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Asia/Kolkata')).strftime("%d-%b %I:%M %p")
                        display_title_prefix = f"[{ist_time}] {base_title}"
                    except:
                        display_title_prefix = base_title

                    print(f"   🏏 {status_tag}: {display_title_prefix}")

                    # --- 5. FETCH LINKS (Mixed Links Handling) ---
                    found_source = False
                    
                    # METHOD A: Inner JSON ('links' key) - Priority
                    json_path = match.get("links")
                    if json_path:
                        target_url = json_path if json_path.startswith("http") else BASE_URL + json_path
                        try:
                            inner_res = session.get(target_url, timeout=10)
                            if inner_res.status_code == 200:
                                try: inner_data = inner_res.json()
                                except: inner_data = json.loads(decrypt_cricz(inner_res.text))
                                
                                # Hidden Layer handling
                                final_streams = []
                                if isinstance(inner_data, dict) and "links" in inner_data and isinstance(inner_data["links"], str):
                                    hidden_dec = decrypt_cricz(inner_data["links"])
                                    if hidden_dec: final_streams = json.loads(hidden_dec)
                                elif isinstance(inner_data, list):
                                    final_streams = inner_data
                                elif isinstance(inner_data, dict):
                                    final_streams = inner_data.get("streamUrls", inner_data.get("channels", [inner_data]))

                                if isinstance(final_streams, dict): final_streams = [final_streams]
                                
                                # Loop through ALL links inside this match
                                for s in final_streams:
                                    stream_url = s.get("link") or s.get("url") or s.get("file")
                                    drm_key = s.get("api") or s.get("drm_key") or s.get("tokenApi")
                                    # Name of the specific stream (e.g., Willow, Hindi, 4K)
                                    stream_name = s.get("name") or s.get("title", "Stream")
                                    
                                    if stream_url:
                                        # UNIQUE TITLE: [Time] IND vs PAK [Willow HD]
                                        full_name = f"{display_title_prefix} [{stream_name}]"
                                        
                                        entry = f'#EXTINF:-1 group-title="{group_title}" tvg-logo="{logo}", {full_name}\n'
                                        if drm_key:
                                            entry += '#KODIPROP:inputstream.adaptive.license_type=clearkey\n'
                                            entry += f'#KODIPROP:inputstream.adaptive.license_key={drm_key}\n'
                                        entry += f'{stream_url}\n'
                                        playlist_entries.append(entry)
                                        found_source = True
                        except: pass

                    # METHOD B: Formats (Backup)
                    # Agar inner json fail hua ya nahi mila, tabhi ye chalega
                    if not found_source:
                        formats = match.get("formats", [])
                        for fmt in formats:
                            url = fmt.get("webLink", "")
                            stream_name = fmt.get("title", "Direct")
                            
                            if url:
                                full_name = f"{display_title_prefix} [{stream_name}]"
                                entry = f'#EXTINF:-1 group-title="{group_title}" tvg-logo="{logo}", {full_name}\n'
                                entry += f'{url}\n'
                                playlist_entries.append(entry)

            except Exception: continue

        # --- SAVE M3U ---
        with open("cricket.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f"#EXTINF:-1 logo=\"https://i.ibb.co/7xz4z0k2/Cricket.png\" group-title=\"Info\", Auto-Updated: {datetime.now().strftime('%d-%b %H:%M IST')}\n")
            f.write("http://fake.url/info\n\n")
            
            if playlist_entries:
                for line in playlist_entries:
                    f.write(line + "\n")
            else:
                f.write("#EXTINF:-1 group-title=\"Bot Status\", No Matches Found\nhttp://fake.url/empty\n")
        
        print(f"✅ Success! Saved {len(playlist_entries)} streams.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    generate_m3u()

