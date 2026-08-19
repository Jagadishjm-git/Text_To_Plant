import os
import sys

inner_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Text_To_Plant-main")
if os.path.exists(inner_dir):
    os.chdir(inner_dir)
    sys.path.insert(0, inner_dir)

from main import app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
