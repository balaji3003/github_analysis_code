import os
import tempfile
import subprocess
from git import Repo
from datetime import datetime, timedelta
import json
from urllib.parse import urlparse, quote_plus


def clone_repo_only_git(git_url, clone_path):
    print(f"Cloning only Git history from {git_url}...")
    subprocess.run(["git", "clone", "--mirror", git_url, clone_path], check=True)


def extract_commit_history(repo_path, git_url, years_back=10):
    print("Extracting commit history...")
    repo = Repo(repo_path)
    start_date = datetime.now() - timedelta(days=365 * years_back)

    commits_data = []
    for commit in repo.iter_commits():
        commit_date = datetime.fromtimestamp(commit.committed_date)
        if commit_date < start_date:
            continue

        try:
            tree_info = commit.tree.hexsha
            blob_ids = [blob.hexsha for blob in commit.tree.traverse() if blob.type == 'blob']
        except Exception as e:
            tree_info = None
            blob_ids = []

        commit_info = {
            "commit_hash": commit.hexsha,
            "author": {
                "name": commit.author.name,
                "email": commit.author.email
            },
            "committer": {
                "name": commit.committer.name,
                "email": commit.committer.email
            },
            "commit_date": commit_date.isoformat(),
            "message": commit.message,
            "parents": [parent.hexsha for parent in commit.parents],
            "tree_id": tree_info,
            "blob_ids": blob_ids,
            "stats": {
                "total": commit.stats.total,
                "files": commit.stats.files
            },
            "files_changed": list(commit.stats.files.keys())
        }
        commits_data.append(commit_info)

        parsed_url = urlparse(git_url)
    repo_name = os.path.splitext(os.path.basename(parsed_url.path))[0]
    owner = parsed_url.path.strip('/').split('/')[0]
    safe_filename = f"{owner}_{repo_name}"
    json_output_file = f"{safe_filename}.json"
    with open(json_output_file, "w", encoding="utf-8") as f:
        json.dump(commits_data, f, indent=4)

    print(f"✅ Commit history saved to {json_output_file} with {len(commits_data)} commits.")


def extract_commit_history_from_url(git_url, years_back=10):
    with tempfile.TemporaryDirectory() as tmpdir:
        clone_repo_only_git(git_url, tmpdir)
        extract_commit_history(tmpdir, git_url, years_back)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract Git commit history from a GitHub repo")
    parser.add_argument("--url", type=str, required=True, help="GitHub repository URL")
    args = parser.parse_args()

    extract_commit_history_from_url(args.url)

#python extract_commit_history.py --url https://github.com/pallets/flask.git