import requests
import os
import netrc
import time
import rasterio

def convert_to_geotiff(hdr_path):
    """Convert HDR file to GeoTIFF and delete originals"""
    try:
        os.makedirs("geotiffs", exist_ok=True)
        output_path = f"geotiffs/{os.path.basename(hdr_path).replace('.hdr', '.tif')}"
        
        if not os.path.exists(output_path):
            with rasterio.open(hdr_path) as src:
                profile = src.profile.copy()
                profile.update(driver='GTiff', compress='lzw')
                
                with rasterio.open(output_path, 'w', **profile) as dst:
                    dst.write(src.read())
            
            print(f"  ✅ Converted to GeoTIFF: {os.path.basename(output_path)}")
            
            # Delete original files to save space
            os.remove(hdr_path)
            bin_path = hdr_path.replace('.hdr', '.bin')
            if os.path.exists(bin_path):
                os.remove(bin_path)
            print(f"  🗑️ Deleted originals to save space")
        
    except Exception as e:
        print(f"  ❌ Conversion failed: {e}")

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
print(f"\nDOWNLOADING DATA")
print(f"Downloading {len(download_pairs)} files (HDR + BIN pairs)...")

# Create download directory
os.makedirs("aviris_downloads", exist_ok=True)

# Download all files
urls = [item['download_url'] for item in download_pairs]
if urls:
    if USE_EARTHACCESS:
        try:
            downloaded_files = earthaccess.download(urls, local_path="aviris_downloads")
            print(f"\nDownloaded {len(downloaded_files)} files to aviris_downloads/")
        except Exception as e:
            print(f"earthaccess download failed: {e}")
            print("Falling back to manual download...")
            USE_EARTHACCESS = False
    
    if not USE_EARTHACCESS:
        # Download with .netrc authentication
        downloaded_files = []
        for i, url in enumerate(urls):
            filename = url.split('/')[-1]
            filepath = f"aviris_downloads/{filename}"
            
            if not os.path.exists(filepath):
                print(f"Downloading {i+1}/{len(urls)}: {filename}")
                start_time = time.time()
                
                try:
                    response = requests.get(url, stream=True, timeout=30)
                    response.raise_for_status()
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded_size = 0
                    
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=1024*1024):
                            if chunk:
                                f.write(chunk)
                                downloaded_size += len(chunk)
                                
                                if total_size > 0:
                                    progress = (downloaded_size / total_size) * 100
                                    elapsed = time.time() - start_time
                                    speed = downloaded_size / (1024*1024) / elapsed if elapsed > 0 else 0
                                    print(f"\r  Progress: {progress:.1f}% ({downloaded_size/(1024*1024):.1f}MB/{total_size/(1024*1024):.1f}MB) - {speed:.1f}MB/s", end="")
                    
                    print(f"\n  ✅ Downloaded: {filename}")
                    downloaded_files.append(filepath)
                    
                    # Convert HDR files immediately after download
                    if filename.endswith('.hdr'):
                        convert_to_geotiff(filepath)
                    
                except requests.exceptions.Timeout:
                    print(f"\n  ⏰ Timeout downloading {filename} - skipping")
                except Exception as e:
                    print(f"\n  ❌ Failed to download {filename}: {e}")
            else:
                print(f"Already exists: {filename}")
        
        print(f"\nDownloaded {len(downloaded_files)} files to aviris_downloads/")
    
    print(f"\n✅ Download and conversion complete!")
else:
    print("No download URLs found in granule metadata.")