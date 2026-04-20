from config.constants import SCOPES

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.http import MediaIoBaseDownload
import io
import os

from shared.logging import setup_logger

logger = setup_logger(__name__)


def init_drive_service(service_account_file: str, verbose: bool = False):
    """
    Initialize Google Drive API client using a service account.

    Args:
        service_account_file (str): path to Google Service Account key to provide as credentials.
    """
    
    # Establish drive service
    credentials = Credentials.from_service_account_file(
        service_account_file,
        scopes=SCOPES
    )
    service = build("drive", "v3", credentials=credentials)

    # Test connection
    try:
        service.files().list(pageSize=1).execute()
        if verbose:
            logger.info("Google Drive service initialized")
            
    except:
        logger.error("Google drive service failed to initialize")

        raise RuntimeError("Google Drive connection failed")

    return service


def list_files(service: Resource, folder_id: str, verbose: bool = True):
    """
    List all non-trashed files within a specified Google Drive folder,
    paginating through all results.

    Args:
        service:    Authenticated Google Drive API service instance.
        folder_id:  ID of the Google Drive folder.
    """

    if verbose:
        logger.info(f"Retrieving list of files from folder '{folder_id}'")
    
    query = f"'{folder_id}' in parents and trashed=false"
    files = []
    page_token = None

    while True:
        response = (
            service.files()
            .list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name, fileExtension, createdTime, modifiedTime, parents)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageToken=page_token,
            )
            .execute()
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    if verbose:
        logger.info(f"List of {len(files)} files retrieved from folder '{folder_id}'")

    return files


def download_file(
    service: Resource,
    file_id: str,
    destination: str = None,
    filename: str = None,
    verbose: bool = True
):
    """
    Downloads a file from Google Drive by file ID.

    Args:
        service:     Authenticated Google Drive API service instance.
        file_id:     Google Drive file ID.
        destination: Local directory to save the file. If provided with
                     filename, the file is written to disk and None is returned.
        filename:    Local filename to use when writing to disk.
                     Must be provided together with destination.
    """

    if bool(destination) ^ bool(filename):
        raise ValueError("Both destination and filename must be provided together")

    if verbose:
        logger.info(f"Downloading file '{file_id}'")

    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    fh.seek(0)
    if filename:
        os.makedirs(destination, exist_ok=True)
        local_file_path = f"{destination}/{filename}"
        with open(local_file_path, "wb") as f:
            f.write(fh.read())

        if verbose:
            logger.info(f"File '{file_id}' saved to {local_file_path}")
        
        return None

    if verbose:
        logger.info(f"File '{file_id}' loaded into memory")

    return fh


def upload_file(
    service: Resource,
    folder_id: str,
    drive_filename: str,
    content: str | io.BytesIO,
    content_type: str = "text/plain",
    source_type: str = "in-memory",
    upload_method: str = "overwrite",
    upload_type: str = "multipart",
    verbose: bool = True
):
    """
    Uploads content (or file) to a specified Google Drive folder.

    Args:
        service:        Authenticated Google Drive API service instance.
        folder_id:      ID of the Google Drive folder.
        drive_filename: Name the file will have in Google Drive.
        content:        Raw text/BytesIO (in-memory) or local file path (file).
        content_type:   MIME type (https://www.iana.org/assignments/media-types/media-types.xhtml).
        source_type:    "in-memory" for text/BytesIO content; "file" for a local file path.
        upload_method:  "overwrite" updates existing file in place (preserving ID);
                        "delete" removes the existing file and creates a new one.
    """

    if source_type not in ("file", "in-memory"):
        raise ValueError(f"Invalid source_type '{source_type}'. Expected 'file' or 'in-memory'")
    
    if upload_method not in ("overwrite", "delete"):
        raise ValueError(f"Invalid upload_method '{upload_method}'. Expected 'overwrite' or 'delete'")

    # Build the file buffer
    if source_type == "file":
        if not os.path.isfile(content):
            raise FileNotFoundError(f"Local file not found: '{content}'")
        with open(content, "rb") as fh:
            file_buffer = io.BytesIO(fh.read())
    else:
        file_buffer = content if isinstance(content, io.BytesIO) else io.BytesIO(content.encode())

    media = MediaIoBaseUpload(file_buffer, mimetype=content_type)

    # Search for existing files with the same name in the specified folder
    query = f"name='{drive_filename}' and '{folder_id}' in parents and trashed=false"
    response = (
        service.files()
        .list(
            q=query,
            spaces="drive",
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        )
        .execute()
    )
    files = response.get("files", [])

    if files and upload_method == "delete":
        for file in files:
            delete_file(service, folder_id, file["name"], verbose=verbose)
        files = []

    elif files and upload_method == "overwrite":
        for file in files:
            updated = (
                service.files()
                .update(
                    uploadType=upload_type,
                    fileId=file["id"],
                    media_body=media,
                    supportsAllDrives=True
                )
                .execute()
            )

        if verbose:
            logger.info(f"Updated existing file {updated.get('id')} - {drive_filename}")

    if not files:
        file_metadata = {"name": drive_filename, "parents": [folder_id]}
        created = (
            service.files()
            .create(
                uploadType=upload_type,
                body=file_metadata,
                media_body=media,
                fields="id",
                supportsAllDrives=True
            )
            .execute()
        )

        if verbose:
            logger.info(f"Uploaded new file {created.get('id')} - {drive_filename}")


def delete_file(service: Resource, file_id: str, verbose: bool = True):
    """
    Delete a file from Google Drive by file ID.

    Args:
        service:    Authenticated Google Drive API service instance.
        file_id:    Google Drive file ID.
    """

    service.files().update(fileId=file_id, body={"trashed": True}, supportsAllDrives=True).execute()
    
    if verbose:
        logger.info(f"Deleted file '{file_id}'")
