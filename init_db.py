import os
import sys

inner_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Text_To_Plant-main")
if os.path.exists(inner_dir):
    os.chdir(inner_dir)
    sys.path.insert(0, inner_dir)

import init_db

if __name__ == "__main__":
    init_db.seed_database()
