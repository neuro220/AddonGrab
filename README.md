# Extension Downloader

A Python script to download Chrome and Firefox browser extensions by ID, saving them as ZIP files for analysis, backup, or development purposes.

## Features

- **Multi-Platform Support**: Download extensions from Chrome (CRX3 format) or Firefox (XPI format).
- **Version Control**: Fetch the latest version or specify a particular version (Firefox supports listing available versions).
- **Batch Downloads**: Process multiple extensions from a file or comma-separated list.
- **Progress Indicators**: Visual progress bars for downloads (requires tqdm).
- **Robust Handling**: Retries on failures, error recovery, and validation for IDs and files.
- **Flexible Output**: Custom output paths, force overwrites, and verbose logging.

## Requirements

- Python 3.6 or higher.
- Optional: `tqdm` for progress bars (`pip install tqdm`).

## Installation

1. Download `extension.py` to your local machine.
2. (Optional) Install tqdm: `pip install tqdm` for download progress bars.

## Usage

Run the script from the command line. Basic syntax:

```
python extension.py [extension_id] [options]
```

### Basic Download

Download the latest version of a Chrome extension:

```
python extension.py cjpalhdlnbpafiamejdnhcphjbkeiagm --platform chrome
```

Download the latest Firefox addon:

```
python extension.py ublock-origin --platform firefox
```

### Advanced Options

- **Specify Version**: Download a specific version (Firefox only supports available versions).

  ```
  python extension.py ublock-origin --platform firefox --version 1.68.0
  ```

- **Batch Download**: Download multiple extensions from a file (one ID per line) or comma-separated list.

  ```
  python extension.py --batch ids.txt --platform firefox --continue-on-error
  ```

  Or:

  ```
  python extension.py --batch id1,id2,id3 --platform chrome --force
  ```

- **List Versions**: Show available versions for a Firefox addon (Chrome not supported).

  ```
  python extension.py ublock-origin --platform firefox --list-versions
  ```

- **Verbose Logging**: Enable detailed output.

  ```
  python extension.py ublock-origin --platform firefox --verbose
  ```

- **Custom Output**: Specify output file path.

  ```
  python extension.py ublock-origin --platform firefox -o custom.zip
  ```

## Options Reference

| Option | Description |
|--------|-------------|
| `extension_id` | Extension ID (Chrome: 32 alphanumeric chars; Firefox: GUID or slug). Optional with --batch or --list-versions. |
| `-o, --output` | Output ZIP file path (default: {extension_id}.zip). |
| `-v, --version` | Version to download (default: latest). |
| `--platform` | Platform: chrome or firefox (default: chrome). |
| `--verbose` | Enable detailed logging. |
| `-f, --force` | Overwrite existing output files. |
| `--batch` | Batch download: file path or comma-separated IDs. |
| `--continue-on-error` | Skip errors in batch mode and continue. |
| `--list-versions` | List available versions for the addon. |
| `-h, --help` | Show help message. |

## Examples

1. **Download uBlock Origin for Firefox**:
   ```
   python extension.py ublock-origin --platform firefox --verbose
   ```
   Output: Downloads and saves as `ublock-origin.zip`.

2. **Download specific version**:
   ```
   python extension.py ublock-origin --platform firefox --version 1.67.0
   ```

3. **Batch download with error handling**:
   ```
   python extension.py --batch ublock-origin,invalid-id --platform firefox --continue-on-error --force
   ```
   Processes valid IDs, skips invalid ones.

4. **List Firefox versions**:
   ```
   python extension.py ublock-origin --platform firefox --list-versions
   ```
   Output: `Available versions for ublock-origin: 1.68.0, 1.67.0, ...`

5. **Chrome extension with custom output**:
   ```
   python extension.py cjpalhdlnbpafiamejdnhcphjbkeiagm --platform chrome -o my-extension.zip --force
   ```

## Troubleshooting

- **Invalid ID Format**: Ensure Chrome IDs are 32 alphanumeric characters, Firefox IDs are GUIDs (e.g., `{uuid}`) or slugs (e.g., `ublock-origin`).
- **File Not Found (Batch)**: Check the batch file path and ensure it exists with one ID per line.
- **API Errors (Firefox)**: Mozilla API may have rate limits (60 requests/hour). Wait and retry. 404 means invalid ID.
- **Download Failures**: Check network connection. Retries are automatic.
- **No Progress Bar**: Install tqdm (`pip install tqdm`) for visual progress.
- **Overwrite Prompts**: Use `--force` to overwrite existing files.
- **Platform Mismatch**: Use correct `--platform` for the ID type.

## Notes

- **Limitations**: Listing versions is only supported for Firefox. Chrome versions must be specified manually.
- **Rate Limits**: Firefox API has request limits; avoid excessive batch downloads.
- **Security**: This script downloads from official sources. Use for legitimate purposes only.
- **File Formats**: Chrome CRX files are stripped to ZIP; Firefox XPI files are saved as-is (already ZIP-compatible).
- **Dependencies**: All core features work with stdlib; tqdm enhances UX.

For issues or feedback, report at https://github.com/sst/opencode/issues.</content>
<parameter name="filePath">/root/tools/README.md