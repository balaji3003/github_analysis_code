import os

def search_keywords_in_json_text(file_path, keywords):
    results = []
    line_count = 0

    if file_path.endswith(".json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                repo_name = os.path.basename(file_path).replace(".json", "")
                
                for line in f:
                    line_count += 1
                    print(f"Reading line {line_count}", end='\r')  # Progress in terminal
                    
                    line_lower = line.lower()
                    for keyword in keywords:
                        if keyword.lower() in line_lower:
                            results.append({
                                "keyword": keyword,
                                "repository": repo_name,
                                "line": line_count,
                                "line_snippet": line.strip()[:120]  # short preview
                            })
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")

    print(f"\n📄 Finished reading {line_count} lines.")
    return results


def test_search_keywords():
    test_file = "Snailclimb_JavaGuide.json"
    test_keywords = ["unit"]

    results = search_keywords_in_json_text(test_file, test_keywords)

    if results:
        print(f"\n✅ Found {len(results)} matches:")
        for r in results[:10]:  # show top 10 matches
            print(f" - Line {r['line']}: [{r['keyword']}] → {r['line_snippet']}")
    else:
        print("❌ No matches found.")


if __name__ == "__main__":
    test_search_keywords()
