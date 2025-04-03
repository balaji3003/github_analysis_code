import csv
from extract_commit_history import extract_commit_history_from_url

CSV_FILE = "github_java_repositories_paginated.csv"  # replace with your actual filename
NUM_REPOS = 5

def process_repos(csv_path, limit=5):
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader):
            if i >= limit:
                break
            url = row['URL']
            print(f"Processing ({i+1}/{limit}): {url}")
            extract_commit_history_from_url(url, years_back=10)

if __name__ == "__main__":
    process_repos(CSV_FILE, NUM_REPOS)