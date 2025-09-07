#!/bin/bash
# Setup script for Pentest-R1 Docker environment

echo "Setting up Pentest-R1 Docker environment..."

# Create cache directories on host if they don't exist
echo "Creating cache directories..."
mkdir -p ~/.cache/huggingface/hub
mkdir -p ~/.cache/triton
mkdir -p ~/.cache/torch_extensions

# Build the Docker image
echo "Building Docker image (this may take 5-10 minutes)..."
docker build -t pentest-r1:ubuntu22.04 .

if [ $? -eq 0 ]; then
    echo "✓ Docker image built successfully!"
    echo ""
    echo "You can now run the container with optimized cache mounting:"
    echo "  docker run --rm -it \\"
    echo "    --name pentest-r1 \\"
    echo "    -v \"\$(pwd)\":/root/Pentest-R1 \\"
    echo "    -v ~/.cache/huggingface:/root/.cache/huggingface \\"
    echo "    -v ~/.cache/triton:/root/.cache/triton \\"
    echo "    -v ~/.cache/torch_extensions:/root/.cache/torch_extensions \\"
    echo "    -w /root/Pentest-R1 \\"
    echo "    --gpus all \\"
    echo "    --net=host \\"
    echo "    pentest-r1:ubuntu22.04"
else
    echo "✗ Docker build failed. Please check the error messages above."
    exit 1
fi