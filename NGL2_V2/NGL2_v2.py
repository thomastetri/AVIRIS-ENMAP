import earthaccess
import time
import os
import requests


earthaccess.login(strategy="interactive", persist=True)  # Saves to .netrc file

url = "https://cmr.earthdata.nasa.gov/search/granules.json"
base_params = {
    "collection_concept_id": "C2659129205-ORNL_CLOUD",
    "page_size": 1000,
    "sort_key": "-start_date",
    "temporal": "2022-07-01T00:00:00.000Z,"
}
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

print(f"====== AVIRIS COLLECTION SUMMARY ======")
print(f"Total Granules Found: {len(all_granules)}")
print(f"Total Images (.bin + .hdr): {len(all_granules) // 2}")

granules = sorted(all_granules, key=lambda x: x['title'])

download_pairs = []
for granule in granules:
    if 'links' in granule:
        for link in granule['links']:
            if (link.get('rel') == 'http://esipfed.org/ns/fedsearch/1.1/data#' and 
                link.get('href', '').endswith(('.hdr', '.bin'))):
                download_pairs.append(link['href'])

print(f"HDR & BIN files found: {len(download_pairs)}")
print("\n====== DOWNLOADING DATA ======")
print("Downloading files...")

os.makedirs("NGL2_V2/AVIRIS_Data", exist_ok=True)

download_files = []
USE_EARTHACCESS = True

if download_pairs:
    # Try earthaccess first
    if USE_EARTHACCESS:
        try:
            download_files = earthaccess.download(download_pairs, local_path="NGL2_V2/AVIRIS_Data")
            print(f"Downloaded {len(download_files)} files to NGL2_V2/AVIRIS_Data/")
        except Exception as e:
            print(f"earthaccess download failed: {e}")
            print("Falling back to manual download...")
            USE_EARTHACCESS = False
    
    # Manual download if earthaccess failed or wasn't used
    if not USE_EARTHACCESS:
        download_files = []
        session = earthaccess.get_requests_https_session()
        
        for i, url in enumerate(download_pairs, start=1):
            filename = url.split('/')[-1]
            filepath = f"NGL2_V2/AVIRIS_Data/{filename}"

            if not os.path.exists(filepath):
                print(f"Downloading {i+1}/{len(download_pairs)}: {filename}")
                start_time = time.time()
                
                try:
                    response = session.get(url, stream=True, timeout=30)
                    response.raise_for_status()

                    total_size = int(response.headers.get('content-length', 0))
                    download_size = 0

                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=1024*1024):
                            if chunk:
                                f.write(chunk)
                                download_size += len(chunk)

                                if total_size > 0:
                                    progress = (download_size / total_size) * 100
                                    elapsed = time.time() - start_time
                                    speed = download_size / (1024*1024) / elapsed if elapsed > 0 else 0
                                    print(f"\r  Progress: {progress:.1f}% ({download_size/(1024*1024):.1f}MB/{total_size/(1024*1024):.1f}MB) - {speed:.1f}MB/s", end="")

                    print(f"\n  Downloaded: {filename}")
                    download_files.append(filepath)

                except requests.exceptions.Timeout:
                    print(f"\n  Timeout downloading {filename} - skipping")
                except Exception as e:
                    print(f"\n  Failed to download {filename}: {e}")
            else:
                print(f"Already exists: {filename}")
    
    print(f"\nDownload complete! {len(download_files)} files saved to NGL2_V2/AVIRIS_Data/")
else:
    print("No download URLs found.")

                    