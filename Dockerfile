# Use the official Python base image
FROM python:3.13-bookworm AS base

# Set the working directory in the container
WORKDIR /src

# Install build-essential
RUN apt-get update && apt-get install -y build-essential

# Clean up
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

ADD https://github.com/bitwarden/sdk/releases/download/bws-v0.4.0/bws-x86_64-unknown-linux-gnu-0.4.0.zip /tmp

RUN unzip /tmp/bws-x86_64-unknown-linux-gnu-0.4.0.zip

RUN mv bws /usr/local/bin

RUN rm -r /tmp/



FROM base AS dev

COPY . .

RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements-dev.txt

EXPOSE 8000

ENTRYPOINT ["python3", "app/entry.py" ]

CMD dev



FROM dev AS test

CMD ["pytest"]



FROM base as prod

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

COPY ./app ./app

EXPOSE 8000

# Start the FastAPI application
ENTRYPOINT ["/bin/python3", "app/entry.py"]

CMD []
