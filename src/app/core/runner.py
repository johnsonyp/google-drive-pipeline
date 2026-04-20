from config.settings import settings

from core.pipeline.extract.drive import extract_files

from shared.google.drive import init_drive_service
from shared.logging import setup_logger, log_function_call

logger = setup_logger(__name__)


# Entry point
@log_function_call(logger)
def run_pipeline():
    
    # Initialize connection to Google Drive serivce
    drive_service = init_drive_service(settings.GOOGLE_APPLICATION_CREDENTIALS)

    # Extract files
    extract_files(drive_service)