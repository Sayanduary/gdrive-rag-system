# Use Ubuntu 22.04 LTS as base image
FROM ubuntu:22.04

# Set non-interactive environment for apt
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies required by LM Studio CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    procps \
    libgomp1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install LM Studio CLI (lms)
RUN curl -fsSL https://lmstudio.ai/install.sh | bash

# Add lms CLI binary to PATH
ENV PATH="/root/.cache/lm-studio/bin:${PATH}"

WORKDIR /app

# Copy entrypoint script into container
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose LM Studio local server port
EXPOSE 1234

# Run entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
