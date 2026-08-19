"""
push_git.py
Pushes to https://github.com/Jagadishjm-git/Text_To_Plant.git explicitly prompting for Jagadishjm-git credentials.
"""

import os
import subprocess
import sys

def push_to_github():
    repo_url = "https://Jagadishjm-git@github.com/Jagadishjm-git/Text_To_Plant.git"
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 70)
    print(f"PUSHING PROJECT TO: {repo_url}")
    print("=" * 70)

    def run_cmd(cmd):
        print(f"\n> {' '.join(cmd)}")
        return subprocess.run(cmd, cwd=project_dir)

    run_cmd(["git", "init"])
    run_cmd(["git", "add", "."])
    run_cmd(["git", "commit", "-m", "feat: complete department authentication, 10,454-record botanical dataset integration, and calibrated hybrid confidence scoring"])
    run_cmd(["git", "branch", "-M", "main"])
    run_cmd(["git", "remote", "remove", "origin"])
    run_cmd(["git", "remote", "add", "origin", repo_url])
    
    print("\nPushing to GitHub (please sign in as Jagadishjm-git when prompted)...")
    run_cmd(["git", "push", "-u", "origin", "main", "--force"])

if __name__ == "__main__":
    push_to_github()
