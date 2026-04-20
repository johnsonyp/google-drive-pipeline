from config.settings import settings

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import io
import json
import pandas as pd

from shared.google.drive import init_drive_service, list_files, download_file, upload_file
from shared.logging import setup_logger, log_function_call

logger = setup_logger(__name__)


def _download_and_parse(file):
    """
    Download file from Google Drive and pre-process.
    A fresh drive service will be initiated each time to avoid locking with concurrency.
    """

    service = init_drive_service(settings.GOOGLE_APPLICATION_CREDENTIALS, verbose=False)

    file_id = file.get("id")
    filename = file.get("name")

    try:
        fh = download_file(service, file_id, verbose=False)
        json_data = json.load(fh)
        match_id = json_data["metadata"].get("matchId")
        record = {
            "match_id": match_id,
            "game_creation": json_data["info"]["gameCreation"],
            "game_duration": json_data["info"]["gameDuration"],
            "game_end_timestamp": json_data["info"]["gameEndTimestamp"],
            "game_id": json_data["info"]["gameId"],
            "game_mode": json_data["info"]["gameMode"],
            "game_start_timestamp": json_data["info"]["gameStartTimestamp"],
            "game_type": json_data["info"]["gameType"],
            "game_version": json_data["info"]["gameVersion"],
            "map_id": json_data["info"]["mapId"],
            "platform_id": json_data["info"]["platformId"],
            "queue_id": json_data["info"]["queueId"],
            "tournament_code": json_data["info"].get("tournamentCode"),
            "_src_id": file_id,
            "_src_filename": filename
        }

        return record
    
    except Exception as e:
        logger.error(f"Failed to process file '{file_id}': {str(e)}")

        return None


@log_function_call(logger)
def extract_files(service):
    logger.info("Preparing to extract files from Google Drive...")

    # List files from raw data folder
    # Ensure 'raw_folder_id' is shared with the Servie Account

    files = list_files(service, settings.RAW_FOLDER_ID)
    files = files[:20]
    total_files = len(files)

    # Download files in parallel
    # Adjust `max_workers` accordignly based on expected file volume and rate limits
    max_workers = 8
    logger.info(f"Downloading {total_files} files | max_workers={max_workers}")

    data = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_download_and_parse, file): file for file in files}
        for future in as_completed(futures):
            result = future.result()
            if result:
                data.append(result)

    logger.info(f"Parsed {len(data)}/{total_files} files successfully")

    # Upload to processed folder / next destination
    # Processed folder must be on a Shared Drive (for Google Drive) - personal accounts require
    # OAuth authentication to write back instead of using a Service Account

    df = pd.DataFrame(data)
    df["_import_date"] = datetime.now(timezone.utc)

    filename = "processed.csv"
    csv_buffer = io.BytesIO(df.to_csv(index=False).encode())
    upload_file(service, settings.PROCESSED_FOLDER_ID, filename, csv_buffer, "text/csv")

    logger.info("Finished extracting data from Google Drive")

    return {"status": "success"}