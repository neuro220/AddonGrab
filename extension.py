#!/usr/bin/env python3
"""
Download any Chrome or Firefox extension by ID and save it as a plain ZIP.
Usage:  python extension.py <extension-id> [-o OUTPUT] [-v VERSION] [--platform PLATFORM] [--verbose]
"""
import argparse
import json
import logging
import re
import sys
import struct
import time
from typing import Optional
import zipfile
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

# ①  New end-point – same one Chrome itself uses
CRX_URL = (
    "https://clients2.google.com/service/update2/crx?"
    "response=redirect&prodversion={ver}&acceptformat=crx2,crx3&"
    "x=id%3D{id}%26installsource%3Dondemand%26uc"
)

def download_crx(extension_id: str, chrome_ver: str = "119.0.6045.0") -> bytes:
    """Return raw CRX bytes (CRX3) for the given extension ID."""
    # ②  Use a very recent Chrome version string
    url = CRX_URL.format(ver=chrome_ver, id=extension_id)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"})
    with urlopen(req, timeout=30) as resp:
        if resp.status == 404:
            raise RuntimeError("Extension not found or invalid ID.")
        elif resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}: {resp.reason}")
        return resp.read()

def download_crx_with_retry(extension_id: str, chrome_ver: str) -> bytes:
    """Download CRX with retries on transient failures."""
    attempt = 0
    while attempt < 3:
        try:
            return download_crx(extension_id, chrome_ver)
        except (URLError, OSError) as e:
            attempt += 1
            if attempt == 3:
                raise RuntimeError(f"Failed to download after 3 attempts: {e}")
            logging.warning(f"Attempt {attempt} failed: {e}. Retrying in {2 ** (attempt - 1)} seconds...")
            time.sleep(2 ** (attempt - 1))
    # Unreachable, but for type checker
    raise RuntimeError("Unreachable")

def validate_extension_id(ext_id: str, platform: str) -> bool:
    """Validate extension ID based on platform."""
    if platform == "chrome":
        return bool(re.match(r'^[a-z0-9]{32}$', ext_id))
    elif platform == "firefox":
        # GUID format: {8-4-4-4-12 hex}
        guid_pattern = r'^\{[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\}$'
        # Slug/ID format: alphanumeric, hyphens, underscores, dots, @
        slug_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9_.@-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$'
        return bool(re.match(guid_pattern, ext_id) or re.match(slug_pattern, ext_id))
    return False

def get_latest_chrome_version() -> str:
    """Fetch the latest stable Chrome version."""
    try:
        url = "https://omahaproxy.appspot.com/all.json"
        with urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        for entry in data:
            if entry.get('os') == 'win64' and entry.get('channel') == 'stable':
                versions = entry.get('versions', [])
                if versions:
                    return versions[0]['version']
        return "119.0.6045.0"  # fallback
    except Exception:
        return "119.0.6045.0"  # fallback

def fetch_firefox_addon_info(addon_id: str, version: Optional[str] = None) -> str:
    """Fetch download URL for Firefox addon from API with retries."""
    if version is None:
        # Fetch current version
        url = f"https://addons.mozilla.org/api/v5/addons/addon/{addon_id}/"
        attempt = 0
        while attempt < 3:
            try:
                req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0", "Accept": "application/json"})
                with urlopen(req, timeout=30) as resp:
                    if resp.status == 404:
                        raise RuntimeError("Firefox addon not found or invalid ID.")
                    elif resp.status == 429:
                        logging.warning("Rate limit hit, retrying after delay...")
                        time.sleep(5)
                        attempt += 1
                        continue
                    elif resp.status != 200:
                        raise RuntimeError(f"API error: HTTP {resp.status}")
                    data = json.loads(resp.read().decode('utf-8'))
                    current_version = data.get('current_version')
                    if not current_version:
                        raise RuntimeError("No current version found for addon.")
                    file_info = current_version.get('file')
                    if not file_info:
                        raise RuntimeError("No file found for addon.")
                    download_url = file_info.get('url')
                    if not download_url:
                        raise RuntimeError("No download URL found.")
                    return download_url
            except (URLError, OSError, json.JSONDecodeError) as e:
                attempt += 1
                if attempt == 3:
                    raise RuntimeError(f"Failed to fetch addon info: {e}")
                logging.warning(f"API fetch attempt {attempt} failed: {e}. Retrying...")
                time.sleep(2 ** attempt)
        raise RuntimeError("Unreachable")
    else:
        # Fetch specific version
        versions_url = f"https://addons.mozilla.org/api/v5/addons/addon/{addon_id}/versions/"
        attempt = 0
        while attempt < 3:
            try:
                req = Request(versions_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0", "Accept": "application/json"})
                with urlopen(req, timeout=30) as resp:
                    if resp.status == 404:
                        raise RuntimeError("Firefox addon not found or invalid ID.")
                    elif resp.status == 429:
                        logging.warning("Rate limit hit, retrying after delay...")
                        time.sleep(5)
                        attempt += 1
                        continue
                    elif resp.status != 200:
                        raise RuntimeError(f"Versions API error: HTTP {resp.status}")
                    versions_data = json.loads(resp.read().decode('utf-8'))
                    for ver in versions_data.get('results', []):
                        if ver.get('version') == version:
                            file_info = ver.get('file')
                            if file_info:
                                download_url = file_info.get('url')
                                if download_url:
                                    return download_url
                    raise RuntimeError(f"Version {version} not found for addon.")
            except (URLError, OSError, json.JSONDecodeError) as e:
                attempt += 1
                if attempt == 3:
                    raise RuntimeError(f"Failed to fetch versions: {e}")
                logging.warning(f"Versions fetch attempt {attempt} failed: {e}. Retrying...")
                time.sleep(2 ** attempt)
        raise RuntimeError("Unreachable")

def download_xpi_with_retry(url: str) -> bytes:
    """Download XPI file with retries and progress bar."""
    attempt = 0
    while attempt < 3:
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"})
            with urlopen(req, timeout=60) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Download failed: HTTP {resp.status}")
                total_size = int(resp.headers.get('content-length', 0))
                data = b""
                chunk_size = 8192
                if tqdm:
                    with tqdm(total=total_size, unit='B', unit_scale=True, desc="Downloading") as pbar:
                        while True:
                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break
                            data += chunk
                            pbar.update(len(chunk))
                else:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        data += chunk
                return data
        except (URLError, OSError) as e:
            attempt += 1
            if attempt == 3:
                raise RuntimeError(f"Failed to download XPI: {e}")
            logging.warning(f"Download attempt {attempt} failed: {e}. Retrying...")
            time.sleep(2 ** attempt)
    raise RuntimeError("Unreachable")

def crx_to_zip(crx_data: bytes) -> bytes:
    """Strip CRX3 header and return the embedded ZIP file."""
    if crx_data[:4] != b"Cr24":
        raise ValueError("Invalid CRX file: missing 'Cr24' header")
    if len(crx_data) < 12:
        raise ValueError("Invalid CRX file: file too short")
    header_len = struct.unpack("<I", crx_data[8:12])[0] + 12   # CRX3
    if header_len > len(crx_data):
        raise ValueError("Invalid CRX file: header length exceeds file size")
    return crx_data[header_len:]

# ---------- rest of the file unchanged ----------
def main():
    parser = argparse.ArgumentParser(description="Download any Chrome or Firefox extension by ID and save it as a plain ZIP.")
    parser.add_argument("extension_id", nargs="?", help="The extension ID (Chrome: 32 hex chars; Firefox: GUID or slug); optional if --batch or --list-versions")
    parser.add_argument("-o", "--output", help="Output ZIP file path (default: {extension_id}.zip)")
    parser.add_argument("-v", "--version", help="Version to use (default: latest; for Firefox, fetches specific version if available)")
    parser.add_argument("--platform", choices=["chrome", "firefox"], default="chrome", help="Platform to download from (default: chrome)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite output file if it exists")
    parser.add_argument("--batch", help="Batch download: file path (one ID per line) or comma-separated IDs")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue batch download on individual errors")
    parser.add_argument("--list-versions", action="store_true", help="List available versions for the addon")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format='%(levelname)s: %(message)s')

    # Parse IDs
    if args.batch:
        if "," in args.batch:
            ids = [id.strip() for id in args.batch.split(",") if id.strip()]
        else:
            try:
                with open(args.batch, "r") as f:
                    ids = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                print(f"Error: Batch file {args.batch} not found.")
                sys.exit(1)
    elif args.extension_id:
        ids = [args.extension_id.strip()]
    else:
        print("Error: Must provide extension_id, --batch, or --list-versions.")
        sys.exit(1)

    platform = args.platform
    version = args.version

    if args.list_versions:
        if len(ids) != 1:
            print("Error: --list-versions requires exactly one ID.")
            sys.exit(1)
        ext_id = ids[0]
        try:
            if platform == "firefox":
                versions_url = f"https://addons.mozilla.org/api/v5/addons/addon/{ext_id}/versions/"
                req = Request(versions_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0", "Accept": "application/json"})
                with urlopen(req, timeout=30) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"API error: HTTP {resp.status}")
                    versions_data = json.loads(resp.read().decode('utf-8'))
                    versions = [ver.get('version') for ver in versions_data.get('results', [])]
                    print(f"Available versions for {ext_id}: {', '.join(versions)}")
            else:
                print("Listing versions is not supported for Chrome; specify version manually.")
        except Exception as e:
            print(f"Error listing versions: {e}")
        sys.exit(0)

    # Download loop
    for i, ext_id in enumerate(ids):
        logging.info(f"Processing {i+1}/{len(ids)}: {ext_id}")
        if not validate_extension_id(ext_id, platform):
            msg = f"Invalid {platform} extension ID format for {ext_id}."
            if platform == "chrome":
                msg += " Must be 32 alphanumeric characters."
            else:
                msg += " Must be a GUID (e.g., {uuid}) or slug (alphanumeric with hyphens/underscores)."
            if args.continue_on_error:
                logging.warning(msg + " Skipping.")
                continue
            else:
                print(f"Error: {msg}")
                sys.exit(1)

        out_file = Path(args.output) if args.output else Path(f"{ext_id}.zip")
        if out_file.exists() and not args.force:
            msg = f"Output file {out_file} already exists."
            if args.continue_on_error:
                logging.warning(msg + " Skipping.")
                continue
            else:
                print(f"Error: {msg} Use --force to overwrite.")
                sys.exit(1)

        try:
            if platform == "chrome":
                chrome_ver = version if version else get_latest_chrome_version()
                logging.info(f"Downloading CRX3 for {ext_id} (version {chrome_ver}) …")
                crx = download_crx_with_retry(ext_id, chrome_ver)
                zip_bytes = crx_to_zip(crx)
                out_file.write_bytes(zip_bytes)
            else:  # firefox
                logging.info(f"Fetching Firefox addon info for {ext_id}" + (f" (version {version})" if version else " (latest)") + " …")
                download_url = fetch_firefox_addon_info(ext_id, version)
                logging.info(f"Downloading XPI …")
                xpi_bytes = download_xpi_with_retry(download_url)
                out_file.write_bytes(xpi_bytes)
            logging.info(f"Saved → {out_file.resolve()}")
        except Exception as e:
            if args.continue_on_error:
                logging.error(f"Failed for {ext_id}: {e}. Continuing.")
            else:
                logging.error(f"Failed for {ext_id}: {e}")
                sys.exit(1)

if __name__ == "__main__":
    main()
