"""
push_git.py
Executes Git add, commit, and push to https://github.com/Jagadishjm-git/Text_To_Plant.git via Python subprocess.
"""

import os
import subprocess
import sys

def push_to_github():
    repo_url = "https://github.com/Jagadishjm-git/Text_To_Plant.git"
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 70)
    print(f"PUSHING PROJECT TO: {repo_url}")
    print(f"Directory: {project_dir}")
    print("=" * 70)

    def run_cmd(cmd, check=True):
        print(f"\n> {' '.join(cmd)}")
        res = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True)
        if res.stdout:
            print(res.stdout.strip())
        if res.stderr:
            print(f"[STDERR] {res.stderr.strip()}")
        return res

    # 1. Git Init
    if not os.path.exists(os.path.join(project_dir, ".git")):
        run_cmd(["git", "init"])

    # 2. Git Add
    run_cmd(["git", "add", "."])

    # 3. Git Commit
    commit_msg = "feat: department authentication, 10454-record dataset, and calibrated hybrid confidence scoring"
    run_cmd(["git", "commit", "-m", commit_msg])

    # 4. Set Main Branch
    run_cmd(["git", "branch", "-M", "main"])

    # 5. Configure Remote
    run_cmd(["git", "remote", "remove", "origin"])
    run_cmd(["git", "remote", "add", "origin", repo_url])

    # 6. Git Push
    push_res = run_cmd(["git", "push", "-u", "origin", "main"])
    if push_res.returncode != 0:
        print("\nStandard push returned non-zero, trying force push...")
        run_cmd(["git", "push", "-u", "origin", "main", "--force"])

    print("\n" + "=" * 70)
    print("PUSH COMPLETED!")
    print("Repository URL: https://github.com/Jagadishjm-git/Text_To_Plant")
    print("=" * 70)

if __name__ == "__main__":
    push_to_github()
