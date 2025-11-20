#!/usr/bin/env python3
import os
from glob import glob
from pathlib import Path
import rasterio
from rasterio.shutil import copy as rio_copy

INPUT_DIR = "/orange/ntziolas/teznatriana/AVIRIS_downloads/NGL2_HDR&BINPairs/"
OUTPUT_DIR = "/orange/ntziolas/teznatriana/AVIRIS_downloads/NGL2_TranslatedTIFs/"


def find_data_file(hdr_path: str):
    """
    For AVIRIS NGL2:
    Look for data filename matching header without the .hdr extension.
    """
    base = hdr_path[:-4]  # strip ".hdr"

    # Try exact match (no extension)
    if os.path.exists(base):
        return base

    # Try known ENVI extensions
    for ext in [".img", ".bsq", ".bin"]:
        candidate = base + ext
        if os.path.exists(candidate):
            return candidate

    return None


def convert_envi_to_tif(hdr_path: str, tif_path: str):
    data_file = find_data_file(hdr_path)

    if data_file is None:
        print(f"❌ Cannot find data file for {hdr_path}")
        return

    # Rasterio requires opening the **data file**, not the header
    try:
        with rasterio.open(data_file) as src:
            rio_copy(src, tif_path, driver="GTiff")
            print(f"✔️ Converted: {tif_path}")
    except Exception as e:
        print(f"❌ Error: {hdr_path}\n   {e}")


def main():
    Path(OUTPUT_DIR).mkdir(exist_ok=True, parents=True)

    hdr_files = sorted(glob(os.path.join(INPUT_DIR, "*.hdr")))

    print(f"Found {len(hdr_files)} HDR files\n")

    for hdr in hdr_files:
        base = Path(hdr).stem
        out_tif = os.path.join(OUTPUT_DIR, base + ".tif")
        convert_envi_to_tif(hdr, out_tif)

    print("\nDone.")


if __name__ == "__main__":
    main()
