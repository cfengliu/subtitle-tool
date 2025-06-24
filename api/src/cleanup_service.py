import logging
import time
import tempfile
import pathlib
from apscheduler.schedulers.blocking import BlockingScheduler

TEMP_DIR = pathlib.Path(tempfile.gettempdir()) / "converted_audios"
EXPIRATION_SECONDS = 60 * 60  # 1 小時


def clean_audio_files():
    """Remove converted audio files older than EXPIRATION_SECONDS from TEMP_DIR."""
    if not TEMP_DIR.exists():
        return

    now = time.time()
    removed = 0
    for p in TEMP_DIR.iterdir():
        try:
            if not p.is_file():
                continue
            # 若檔案最後修改時間距離現在超過一小時
            if now - p.stat().st_mtime > EXPIRATION_SECONDS:
                p.unlink()
                removed += 1
        except Exception as e:
            logging.warning(f"Failed to delete {p}: {e}")
    if removed:
        logging.info(f"Cleanup job removed {removed} files from {TEMP_DIR}")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Audio cleanup service started. Scanning directory: %s", TEMP_DIR)

    # 初次啟動時先清一次
    clean_audio_files()

    scheduler = BlockingScheduler()
    # 每 10 分鐘執行一次
    scheduler.add_job(clean_audio_files, "interval", minutes=10, id="audio_cleanup")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Audio cleanup service stopped.")


if __name__ == "__main__":
    main() 