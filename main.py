import time
import os
import shutil
import scraper
from kaggle import KaggleApi as kag_api
from datetime import datetime

DATASET_NAME = "YouTube-Trending-Video-Dataset"
DATA_FOLDER = "datasets"


def clear_dir(folder):
    for filename in os.listdir(folder):
        if filename == 'dataset-metadata.json':
            pass
        else:
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                print("[INFO] Files removed.")
            except Exception as e:
                print('[ERROR] Failed to delete %s. Reason: %s' % (file_path, e))


def kaggle_authenticate():
    api = kag_api()
    kag_api.authenticate(api)
    print("\n[INFO] Kaggle api authenticated.")
    return api


def kaggle_dataset_download(api, dataset_name, path):
    kag_api.dataset_download_files(api, dataset_name, unzip=True, path=path)
    print("[INFO] Dataset downloaded.")


def kaggle_upload_dataset(api, path):
    kag_api.dataset_create_version(api, path, f"Dataset updated till (UTC): {datetime.utcnow()}",
                                   convert_to_csv=True, delete_old_versions=False)
    print("\n[INFO] Dataset uploaded.\n")
    clear_dir(path)


if __name__ == '__main__':
    api = kaggle_authenticate()
    # kag_api.dataset_download_files(api, DATASET_NAME, unzip=True, path=DATA_FOLDER)
    kaggle_dataset_download(api, DATASET_NAME, DATA_FOLDER)
    print("[INFO] Dataset downloaded.")
    if scraper.scrap() is True:
        kaggle_upload_dataset(api, DATA_FOLDER)
