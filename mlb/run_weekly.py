#!/usr/bin/env python3
# MLB Weekly Runner
from config import log_header
from download_mlb_data import MLBDataDownloader
from fixture_downloader import MLBFixtureDownloader
from data_ingest import MLBDataIngestor
from features import build_features_from_raw
from models import train_mlb_models
from predict import predict_upcoming_games
from config import PROCESSED_DIR

def main():
    log_header("MLB Weekly Betting System")
    
    print("\n1. Downloading fixtures...")
    MLBFixtureDownloader().download_and_save()
    
    print("\n2. Processing data...")
    # Skip download and ingestion for now
    
    print("\n3. Generating predictions...")
    # predict_upcoming_games()
    
    print("\n✅ Pipeline complete!")

if __name__ == "__main__":
    main()
