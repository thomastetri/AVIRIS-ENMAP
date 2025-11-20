# https://github.com/rupesh2/aviris_conversion?tab=readme-ov-file
import requests
import os
import netrc
import time

# Setup .netrc file for NASA Earthdata authentication
def setup_netrc():
    netrc_path = os.path.expanduser("~/.netrc")
    if not os.path.exists(netrc_path):
        username = input("Enter NASA Earthdata username: ")
        password = input("Enter NASA Earthdata password: ")
        
        with open(netrc_path, 'w') as f:
            f.write(f"machine urs.earthdata.nasa.gov\n")
            f.write(f"login {username}\n")
            f.write(f"password {password}\n")
        
        os.chmod(netrc_path, 0o600)
        print(f"✅ Created .netrc file at {netrc_path}")
    else:
        print("✅ .netrc file already exists")

setup_netrc()

# Try earthaccess first, fallback to netrc auth
try:
    import earthaccess
    auth = earthaccess.login()
    if auth:
        USE_EARTHACCESS = True
        print("✅ Authenticated with earthaccess")
    else:
        raise Exception("earthaccess login failed")
except:
    print("Using .netrc authentication")
    USE_EARTHACCESS = False

url = "https://cmr.earthdata.nasa.gov/search/granules.json"
base_params = {
    "collection_concept_id": "C2659129205-ORNL_CLOUD",
    "page_size": 2000,
    "sort_key": "-start_date",
    "temporal": "2022-07-01T00:00:00.000Z,"
}

# Collect all granules by paginating
all_granules = []
page_num = 1

while True:
    params = base_params.copy()
    params["page_num"] = page_num
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    
    entries = data.get('feed', {}).get('entry', [])
    if not entries:
        break
        
    all_granules.extend(entries)
    print(f"Page {page_num}: Retrieved {len(entries)} granules (Total: {len(all_granules)})")
    page_num += 1

print(f"\nAVIRIS COLLECTION SUMMARY")
print(f"Total granules found: {len(all_granules)}")
print(f"Total images (.bin & .hdr pairs): {len(all_granules) // 2}")

granules = sorted(all_granules, key=lambda x: x['title'])

os.makedirs("AVIRIS_downloads/NGL2V1_Collection/", exist_ok=True)
# Extract HDR and BIN download URLs from granules
download_pairs = []
for granule in granules:
    if 'links' in granule:
        for link in granule['links']:
            if (link.get('rel') == 'http://esipfed.org/ns/fedsearch/1.1/data#' and 
                (link.get('href', '').endswith('.hdr') or link.get('href', '').endswith('.bin'))):
                download_pairs.append({
                    'granule_title': granule['title'],
                    'download_url': link.get('href')
                })

print(f"HDR and BIN files found: {len(download_pairs)}")
print(f"\nTESTING MODE: Limiting to first 10 files")
print(f"Downloading 10 files for testing...")

# Download first 10 files for testing
urls = [item['download_url'] for item in download_pairs][:10]
if not urls:
    print("No download URLs found in granule metadata.")
    exit()

downloaded_files = []

# Try earthaccess download first
if USE_EARTHACCESS:
    try:
        print("Starting earthaccess download...")
        downloaded_files = earthaccess.download(urls, local_path="AVIRIS_downloads/NGL2V1_Collection/")
        if not downloaded_files:
            USE_EARTHACCESS = False
    except Exception as e:
        print(f"earthaccess failed: {e}. Using manual download...")
        USE_EARTHACCESS = False

# Manual download fallback (for .netrc authentication)
if not USE_EARTHACCESS:
    print("Using manual download with .netrc authentication...")
    downloaded_files = []
    for i, url in enumerate(urls):
        filename = url.split('/')[-1]
        filepath = f"AVIRIS_downloads/NGL2V1_Collection/{filename}"
        
        if os.path.exists(filepath):
            print(f"Already exists: {filename}")
        else:
            print(f"Downloading {i+1}/{len(urls)}: {filename}")
            try:
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                print(f"Downloaded: {filename}")
            except Exception as e:
                print(f"  !!!! Failed: {filename} - {e}")
                continue
        downloaded_files.append(filepath)

print(f"\n✅ Test complete! {len(downloaded_files)} files in AVIRIS_downloads/NGL2V1_Collection/")
exit()