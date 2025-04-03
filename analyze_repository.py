import os
import shutil
import tempfile
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
from radon.complexity import cc_visit
from radon.metrics import mi_visit
from git import Repo
from collections import defaultdict, Counter
import math
from datetime import datetime, timedelta
import lizard
import re


def clone_repo(git_url, clone_path):
    print(f"Cloning repository from {git_url}...")
    subprocess.run(["git", "clone", git_url, clone_path], check=True)


def calculate_entropy(change_counts):
    """
    Calculate the entropy of file changes.

    Entropy is a measure of uncertainty or randomness in the distribution
    of file changes. It is calculated using the formula:
    H = -Σ (p * log2(p)), where p is the proportion of changes for each file.

    Args:
        change_counts (dict): A dictionary where keys are file names and values
                              are the number of changes made to each file.

    Returns:
        float: The entropy value. Returns 0 if there are no changes.
    """
    # Calculate the total number of changes across all files
    total = sum(change_counts.values())
    
    # If there are no changes, return 0 as entropy
    if total == 0:
        return 0
    
    # Calculate entropy using the formula: H = -Σ (p * log2(p))
    # For each file, compute its proportion of changes (p) and its contribution to entropy
    entropy = -sum((count / total) * math.log2(count / total) for count in change_counts.values())
    
    return entropy


def measure_cyclomatic_complexity(source_code, file_extension):
    """
    Measure the cyclomatic complexity of the given source code.

    Cyclomatic complexity is a software metric used to measure the complexity
    of a program by counting the number of linearly independent paths through
    the source code.

    Args:
        source_code (str): The source code to analyze.
        file_extension (str): The file extension (e.g., ".py", ".java") to determine
                              the appropriate tool for analysis.

    Returns:
        int: The total cyclomatic complexity of the source code.
    """
    # If the file is a Python file, use Radon's cc_visit to calculate complexity
    if file_extension == ".py":
        complexity_list = cc_visit(source_code)
        # Sum up the complexity values for all code blocks in the file
        return sum(c.complexity for c in complexity_list)
    else:
        # For other file types, use Lizard to analyze the source code
        result = lizard.analyze_file.analyze_source_code("", source_code)
        # Sum up the cyclomatic complexity of all functions in the file
        return sum(func.cyclomatic_complexity for func in result.function_list)


def measure_maintainability_index(source_code):
    """
    Measure the maintainability index of the given source code.

    The maintainability index is a software metric that evaluates how easy 
    it is to maintain a piece of code. It is calculated based on factors 
    such as cyclomatic complexity, lines of code, and Halstead metrics.

    Args:
        source_code (str): The source code to analyze.

    Returns:
        float: The maintainability index value. Returns 0 if an error occurs.
    """
    try:
        # Use Radon's mi_visit function to calculate the maintainability index
        return mi_visit(source_code, False)['mi']
    except:
        # If an error occurs (e.g., invalid source code), return 0
        return 0


def measure_cohesion_lcom(source_code):
    """
    Measure the cohesion of the given source code using the LCOM metric.

    LCOM (Lack of Cohesion in Methods) is a software metric that evaluates
    the cohesion of a class or module. It is calculated based on the number
    of functions or methods in the source code.

    Args:
        source_code (str): The source code to analyze.

    Returns:
        int: The number of functions or methods in the source code, as a proxy
             for cohesion. Returns 0 if an error occurs during analysis.
    """
    try:
        # Use Lizard to analyze the source code and extract function details
        result = lizard.analyze_file.analyze_source_code("", source_code)
        # Return the number of functions/methods in the source code
        return len(result.function_list)
    except:
        # If an error occurs (e.g., invalid source code), return 0
        return 0


def measure_coupling_imports(source_code):
    return len(re.findall(r'\bimport\b|\bfrom\b', source_code))


def analyze_repository(repo_path):
    print("Starting longitudinal analysis...")
    data = []
    file_ownership = defaultdict(set)
    commit_counts_by_author = Counter()

    repo = Repo(repo_path)
    one_year_ago = datetime.now() - timedelta(days=365)

    for commit in repo.iter_commits():
        try:
            commit_date = datetime.fromtimestamp(commit.committed_date)
        except:
            continue

        if commit_date < one_year_ago:
            continue

        churn_add = 0
        churn_del = 0
        file_count = 0
        complexity_total = 0
        mi_total = 0
        lcom_total = 0
        import_count_total = 0
        file_change_counter = defaultdict(int)
        author_email = commit.author.email
        commit_counts_by_author[author_email] += 1

        for file in commit.stats.files:
            file_path = os.path.join(repo_path, file)
            file_change_counter[file] += 1
            file_ownership[file].add(author_email)

            if file.endswith(('.py', '.java')):
                try:
                    blob = commit.tree / file
                    source_code = blob.data_stream.read().decode("utf-8", errors="ignore")
                    churn_add += commit.stats.files[file]['insertions']
                    churn_del += commit.stats.files[file]['deletions']
                    file_count += 1

                    ext = os.path.splitext(file)[1]
                    complexity_total += measure_cyclomatic_complexity(source_code, ext)
                    if ext == ".py":
                        mi_total += measure_maintainability_index(source_code)
                    import_count_total += measure_coupling_imports(source_code)
                    lcom_total += measure_cohesion_lcom(source_code)
                except Exception:
                    continue

        entropy = calculate_entropy(file_change_counter)

        data.append({
            "commit_hash": commit.hexsha,
            "commit_date": commit_date,
            "author": author_email,
            "files_changed": file_count,
            "lines_added": churn_add,
            "lines_deleted": churn_del,
            "total_cyclomatic_complexity": complexity_total,
            "total_maintainability_index": mi_total,
            "total_cohesion_metric_lcom": lcom_total,
            "total_coupling_metric_imports": import_count_total,
            "code_entropy": entropy,
            "commit_frequency_by_author": commit_counts_by_author[author_email],
            "unique_authors_per_file_avg": sum(len(owners) for owners in file_ownership.values()) / len(file_ownership)
        })

    df = pd.DataFrame(data)
    df['commit_date'] = pd.to_datetime(df['commit_date'])
    df.sort_values('commit_date', inplace=True)

    output_file = "longitudinal_metrics.csv"
    df.to_csv(output_file, index=False)
    print(f"✅ Analysis complete. Data saved to {output_file}")
    return df


def plot_metrics(df):
    print("Generating separate plots for each metric...")
    metrics = [
        ("total_cyclomatic_complexity", "Cyclomatic Complexity"),
        ("total_maintainability_index", "Maintainability Index"),
        ("code_entropy", "Code Entropy"),
        ("total_cohesion_metric_lcom", "LCOM (Cohesion Metric)"),
        ("total_coupling_metric_imports", "Coupling (Import Count)"),
        ("lines_added", "Lines Added"),
        ("lines_deleted", "Lines Deleted"),
        ("files_changed", "Files Changed"),
        ("commit_frequency_by_author", "Commit Frequency by Author"),
        ("unique_authors_per_file_avg", "Unique Authors per File")
    ]

    for column, label in metrics:
        if column in df.columns:
            plt.figure(figsize=(12, 6))
            plt.plot(df['commit_date'], df[column], label=label)
            plt.xlabel("Date")
            plt.ylabel(label)
            plt.title(f"{label} Over Time")
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            filename = f"plot_{column}.png"
            plt.savefig(filename)
            plt.show()
            print(f"📊 Plot saved as {filename}")


def run_analysis_from_url(git_url):
    with tempfile.TemporaryDirectory() as tmpdir:
        clone_repo(git_url, tmpdir)
        df = analyze_repository(tmpdir)
        plot_metrics(df)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Longitudinal Software Quality Analyzer")
    parser.add_argument("--url", type=str, required=True, help="GitHub repository URL to analyze")
    args = parser.parse_args()

    run_analysis_from_url(args.url)
