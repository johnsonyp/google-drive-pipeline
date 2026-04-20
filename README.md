# Google Drive Pipeline

A sample Python data pipeline showcasing the ability to programmatically download files from Google Drive to enable automated downstream activity.

## Overview

This sample is admittedly a niche use case — it frames Google Drive as the core storage medium for a data pipeline, which is counter to most data engineering practices where purpose-built storage options (object stores, databases) are far more suitable. That said, a few points worth considering:

- The code stays within the Google Drive ecosystem, so it is easy to sample and test as long as you have a Gmail account or are on Google Workspace.
- Google Drive is not an uncommon data source across departments and teams, particularly in smaller organizations that have not yet adopted a more formal file management system.
- This is geared towards those on Google Workspace who may need to build custom applications to interact with files on Drive. This serves as an introductory starting point with pre-built functions — what you build beyond that is up to you.
- Google Drive is free!

---

## Project Structure

The overall structure is designed with data pipelines in mind. There is arguably more scaffolding than strictly necessary for a simple example like this, but it provides a general framework for building out a more robust pipeline if desired.

```
samples/                            # Sample data
src/
└── app/
    ├── config/
    │   ├── constants.py            # Root/app paths and Google API scopes
    │   ├── metadata.py             # Pipeline name and version from pyproject.toml
    │   └── settings.py             # Environment variable bindings via pydantic-settings
    ├── core/
    │   ├── pipeline/
    │   │   └── extract/
    │   │       └── drive.py        # Extract, parse, upload logic
    │   └── runner.py               # Pipeline entrypoint
    ├── shared/
    │   ├── google/
    │   │   └── drive.py            # Google Drive API helpers
    │   └── logging.py              # Logger setup and decorators
    └── main.py
```

`main.py` is the application entry point, executing `run_pipeline` in `runner.py`, which in turn orchestrates the logic in `pipeline/`. The `shared/` folder contains utility functions available across the entire application.

---

## Setup
 
### Installation

Requires Python 3.11+. Install dependencies from `pyproject.toml`:
 
```bash
pip install .
```

### Authentication

The pipeline authenticates with Google Drive using a Google Service Account.

1. Create a service account in [Google Cloud Console](https://console.cloud.google.com/).
2. Share your target Google Drive folders with the service account email.
3. Download the JSON key file and set `GDRIVE_SERVICE_ACCOUNT_FILE` in `.env`.

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
# .env
GDRIVE_SERVICE_ACCOUNT_FILE= # Path to your service account key file
GDRIVE_RAW_FOLDER_ID=        # Folder ID containing raw JSON files
GDRIVE_PROCESSED_FOLDER_ID=  # Folder ID to upload the processed CSV
```

Folder IDs can be found in the Google Drive URL:
`https://drive.google.com/drive/folders/<FOLDER_ID>`

### Data

The existing code is written around the sample data found in the `samples/` folder. Copy those files to your Google Drive raw folder to run the pipeline as-is. The code can be adapted to whatever data structure you need.

---

## Process Flow

The pipeline connects to Google Drive using the `google-api-python-client` SDK.
 
Using the specified `GDRIVE_RAW_FOLDER_ID`, all files in the folder are listed and downloaded concurrently into memory using `ThreadPoolExecutor`. Each thread initialises its own Drive service instance to avoid contention on the shared API client. The default concurrency is `max_workers=8` — tune this based on your file count and the Google Drive API quota (1,000 requests per 100 seconds per user).
 
Each downloaded file is parsed immediately upon download rather than buffering all files first to keep memory usage manageable. The existing code is also written for the sample JSON files in `samples/`. This can be retooled for your data.
 
The processed DataFrame is then uploaded back to Google Drive at `GDRIVE_PROCESSED_FOLDER_ID`. This step is intended to simulate staging processed data for a downstream system — for example, a Data Warehouse picking up the file for further loading. Alternatively, you can write directly to a database in-memory at this point. The next steps are ultimately up to you and your use case.

---

## Known Limitations

### Google Drive Upload

Uploading via a Service Account requires the destination folder to be on a **Google Workspace Shared Drive**. Personal Google Drive accounts do not support service account uploads due to storage quota restrictions — service accounts have no quota of their own and can only write to Shared Drives where the organisation's quota applies.

For **personal account users**, the workaround is OAuth authentication, which uploads against your personal quota. This would require re-implementing `init_drive_service` using an OAuth flow and setting up OAuth 2.0 credentials (Desktop app type) in Google Cloud Console.

Note that extraction (downloading) works fully with a service account on any personal Drive folder that has been shared with the service account — only uploads are affected by this limitation.