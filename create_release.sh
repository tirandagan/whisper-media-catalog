#!/bin/bash

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║                                                                                ║
# ║   Video Library Transcription & Management System                              ║
# ║                                                                                ║
# ║   Created by: Tiran Dagan                                                      ║
# ║   Copyright © 2023-2025 Tiran Dagan. All rights reserved.                      ║
# ║                                                                                ║
# ║   Script to create a release zip file of the project                           ║
# ║                                                                                ║
# ║   Repository: https://github.com/tirandagan/whisper-media-catalog              ║
# ║                                                                                ║
# ╚════════════════════════════════════════════════════════════════════════════════╝

# Set variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="video-library-transcription-system"
VERSION=$(grep "__version__" "${SCRIPT_DIR}/__init__.py" | cut -d'"' -f2 | head -n 1)
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
OUTPUT_FILE="${PROJECT_NAME}-${VERSION}-${TIMESTAMP}.zip"

# Print banner
echo "╔════════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                                ║"
echo "║   Creating release zip for Video Library Transcription & Management System     ║"
echo "║                                                                                ║"
echo "╚════════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Project directory: ${SCRIPT_DIR}"
echo "Version: ${VERSION}"
echo "Output file: ${OUTPUT_FILE}"
echo ""

# Check if zip is installed
if ! command -v zip &> /dev/null; then
    echo "Error: zip command not found. Please install zip."
    exit 1
fi

# Create a list of files to exclude
cat > "${SCRIPT_DIR}/.zipignore" << EOL
*.pyc
__pycache__/
*.db
*.sqlite
*.sqlite3
*.xlsx
*.log
venv/
.env
.git/
.gitignore
.cursorignore
.zipignore
*.zip
config.ini
EOL

# Create the zip file
echo "Creating zip file..."
(cd "${SCRIPT_DIR}" && zip -r "${OUTPUT_FILE}" . -x@.zipignore)

# Check if zip was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                                ║"
    echo "║   Zip file created successfully!                                               ║"
    echo "║                                                                                ║"
    echo "╚════════════════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Output file: ${SCRIPT_DIR}/${OUTPUT_FILE}"
    echo "File size: $(du -h "${SCRIPT_DIR}/${OUTPUT_FILE}" | cut -f1)"
    echo ""
    echo "The following files/directories were excluded:"
    cat "${SCRIPT_DIR}/.zipignore"
    echo ""
    echo "To install the package from the zip file:"
    echo "1. Unzip the file: unzip ${OUTPUT_FILE}"
    echo "2. Install dependencies: pip install -r requirements.txt"
    echo "3. Run the application: python main.py"
else
    echo "Error: Failed to create zip file."
    exit 1
fi

# Clean up
rm "${SCRIPT_DIR}/.zipignore"

exit 0 