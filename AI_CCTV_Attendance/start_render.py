import os
import sys

from gunicorn.app.wsgiapp import run

if __name__ == "__main__":
    os.environ.setdefault("PORT", "10000")
    sys.argv[1:] = [
        "gunicorn",
        "--bind",
        f"0.0.0.0:{os.environ['PORT']}",
        "--workers",
        "1",
        "--threads",
        "4",
        "app:app",
    ]
    run()
