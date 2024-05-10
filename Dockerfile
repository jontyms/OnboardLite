# Use the official Python base image
FROM python:3.11-bookworm

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to the container
COPY requirements.txt .

# Install build-essential
RUN apt-get update && apt-get install -y build-essential

# Clean up
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

ADD https://github.com/bitwarden/sdk/releases/download/bws-v0.4.0/bws-x86_64-unknown-linux-gnu-0.4.0.zip /tmp

RUN unzip /tmp/bws-x86_64-unknown-linux-gnu-0.4.0.zip

RUN mv bws /usr/local/bin

RUN rm -r /tmp/

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code to the container
COPY . .

# Expose the port that the FastAPI application will run on
EXPOSE 8000

# Start the FastAPI application
CMD ["uvicorn", "index:app", "--host", "0.0.0.0", "--port", "8000"]
