#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Additional build steps can go here
echo "Build completed successfully!"
