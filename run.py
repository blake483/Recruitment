"""Start the CV search app:  python run.py   then open http://127.0.0.1:5000"""

import os
import webbrowser

from cvsearch.app import create_app

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  CV Search running at http://127.0.0.1:{port}  (Ctrl+C to stop)\n")
    if not os.environ.get("NO_BROWSER"):
        webbrowser.open(f"http://127.0.0.1:{port}")
    # 127.0.0.1 = only reachable from this computer. CVs never leave your machine.
    app.run(host="127.0.0.1", port=port, debug=False)
