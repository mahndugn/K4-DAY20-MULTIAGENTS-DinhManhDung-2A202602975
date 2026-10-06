# Build the original lab image first: docker build -t lab-deepagents .
# Then: docker build -f report/Dockerfile -t lab-deepagents-runner .
FROM lab-deepagents
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
RUN git config --global --add safe.directory /lab
ENV PYTHONWARNINGS=ignore
