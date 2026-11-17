"""Development entry point: `python run.py` then open http://127.0.0.1:5000."""

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    preferred = int(os.environ.get("PORT", "5000"))
    tried = []
    for port in (preferred, 5077, 5001):
        if port in tried:
            continue
        tried.append(port)
        try:
            app.run(host="127.0.0.1", port=port, debug=True)
            break
        except OSError as error:
            print(f"Port {port} is unavailable ({error}). Trying another port...")
    print("Open one of these addresses in your browser: "
          + ", ".join(f"http://127.0.0.1:{port}" for port in tried))
