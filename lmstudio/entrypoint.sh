#!/bin/bash
set -e

echo "Starting LM Studio local server on port 1234..."
# Start LM Studio headless server bound to 0.0.0.0
lms server start --host 0.0.0.0 --port 1234 &

# Wait for server process to initialize
echo "Waiting for LM Studio server to initialize..."
sleep 5

# Download and load configured models
echo "=========================================="
echo "Installing model: llama-3.2-3b-instruct"
echo "=========================================="
lms get lmstudio-community/Llama-3.2-3B-Instruct-GGUF --load || true

echo "=========================================="
echo "Installing vision model: qwen2.5-vl-3b-instruct"
echo "=========================================="
lms get Qwen/Qwen2.5-VL-3B-Instruct-GGUF --load || true

echo "LM Studio server ready and models loaded!"

# Keep container active
exec tail -f /dev/null
