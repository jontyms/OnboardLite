import os
import subprocess
import sys


# Define the default command to run uvicorn with environment variables
def run_uvicorn():
    host = os.getenv("ONBOARD_HOST", "0.0.0.0")
    port = os.getenv("ONBOARD_PORT", "8000")
    command = [
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        port,
        "--workers",
        "2",
    ]
    subprocess.run(command)


def run_dev():
    host = os.getenv("ONBOARD_HOST", "0.0.0.0")
    port = os.getenv("ONBOARD_PORT", "8000")
    command = ["uvicorn", "app.main:app", "--host", host, "--port", port, "--reload"]
    subprocess.run(command)


# Define the migrate command
def run_migrate():
    os.chdir("./app")
    command = ["alembic", "upgrade", "head"]
    subprocess.run(command)


# Entry point
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "migrate":
        run_migrate()
    elif len(sys.argv) > 1 and sys.argv[1] == "dev":
        run_dev()
    else:
        run_uvicorn()
