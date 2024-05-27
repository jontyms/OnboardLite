import os
import sys
import subprocess

# Define the default command to run uvicorn with environment variables
def run_uvicorn():
    host = os.getenv('ONBOARD_HOST', '0.0.0.0')
    port = os.getenv('ONBOARD_PORT', '8000')
    command = ["uvicorn", "app.main:app", "--host", host, "--port", port]
    subprocess.run(command)

# Define the migrate command
def run_migrate():
    command = ["alembic", "upgrade", "head"]
    subprocess.run(command)

# Entry point
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "migrate":
        run_migrate()
    else:
        run_uvicorn()
