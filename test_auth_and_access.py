import os
import sys

inner_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Text_To_Plant-main")
if os.path.exists(inner_dir):
    os.chdir(inner_dir)
    sys.path.insert(0, inner_dir)

import test_auth_and_access

if __name__ == "__main__":
    success = test_auth_and_access.run_all_acceptance_tests()
    sys.exit(0 if success else 1)
