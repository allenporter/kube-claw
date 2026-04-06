#!/usr/bin/env python3
"""
Repository Health Monitor
Polls GitHub for CI status, PR age, and Issue counts to generate a health summary.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import yaml

def run_gh(args):
    """Run a gh CLI command and return the JSON output."""
    cmd = ["gh"] + args + ["--json", "name,url,isArchived,pushedAt,repositoryTopics", "--limit", "300"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running gh: {result.stderr}", file=sys.stderr)
        return []
    return json.loads(result.stdout)

def get_repo_details(repo_full_name):
    """Get specific health metrics for a repository."""
    # Check PRs - including isDraft, author, and review status
    pr_cmd = ["gh", "pr", "list", "--repo", repo_full_name, "--json", "number,title,updatedAt,isDraft,author,reviewDecision"]
    prs = json.loads(subprocess.run(pr_cmd, capture_output=True, text=True).stdout or "[]")
    
    # Check last CI run
    ci_cmd = ["gh", "api", f"repos/{repo_full_name}/actions/runs?per_page=1"]
    ci_data = json.loads(subprocess.run(ci_cmd, capture_output=True, text=True).stdout or "{}")
    last_run = ci_data.get("workflow_runs", [{}])[0]
    
    return {
        "prs": prs,
        "last_ci": last_run.get("conclusion", "N/A"),
        "ci_url": last_run.get("html_url", "#")
    }

def main():
    manifest_path = Path("src/repo-conformance/manifest.yaml")
    if not manifest_path.exists():
        print("Manifest not found. Run in workspace root.")
        return

    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    
    target_repos = [repo["name"] for repo in manifest.get("repos", []) if isinstance(repo, dict)]
    owner = manifest.get("user", "allenporter")

    report = []
    report.append("# Repository Health Dashboard")
    report.append(f"**Last Updated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    report.append("| Repository | CI Status | Open PRs | Priority Action | Your Stale | Total Stale |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- |")

    now = datetime.now(timezone.utc)
    for repo_name in target_repos:
        full_name = f"{owner}/{repo_name}"
        details = get_repo_details(full_name)
        
        ci_icon = "✅" if details["last_ci"] == "success" else "❌" if details["last_ci"] == "failure" else "⚪"
        pr_count = len(details["prs"])
        
        # Calculate categories
        stale_count = 0
        draft_count = 0
        priority_action = 0  # PRs from others, non-draft, not approved
        your_stale = 0       # Your own PRs, non-draft, older than 14d
        
        for pr in details["prs"]:
            is_draft = pr.get("isDraft")
            author = pr.get("author", {}).get("login")
            updated_at = datetime.fromisoformat(pr["updatedAt"].replace("Z", "+00:00"))
            days_old = (now - updated_at).days
            review_decision = pr.get("reviewDecision")
            
            if is_draft:
                draft_count += 1
                continue
            
            # Priority 1: Awesome contributors waiting on you
            if author != owner and review_decision != "APPROVED":
                priority_action += 1
            
            # Priority 2: Your own stuff you might have forgotten
            if author == owner and days_old > 14:
                your_stale += 1

            # General Staleness (everyone else's approved or older stuff)
            if days_old > 14:
                stale_count += 1
        
        report.append(f"| [{repo_name}](https://github.com/{full_name}) | {ci_icon} | {pr_count} | {priority_action} | {your_stale} | {stale_count} |")

    output_path = Path("reports/repo-health/SUMMARY.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(report))
    
    print(f"Health report updated at {output_path}")

if __name__ == "__main__":
    main()
