# Video Library

A Python application for transcribing and organizing video files using OpenAI Whisper with SQLite storage.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![OpenAI](https://img.shields.io/badge/AI-OpenAI%20Whisper-orange.svg)

## Features

- **Video Processing**
  - Automatically scan folders for video files
  - Extract video metadata (resolution, bitrate, encoding, duration, etc.)
  - Track file status (New, Transcribed, Missing, Error Transcribing)
  - Detect missing videos and update their status

- **Transcription**
  - Transcribe videos using OpenAI Whisper
  - Generate intelligent titles and summaries using OpenAI GPT-4o
  - Create keyword tags for content categorization
  - Preserve special casing for company names (AT&T, T-Mobile, etc.)
  - Create formatted markdown transcript files

- **Database**
  - Store all information in SQLite database
  - Support for many-to-many relationships between transcriptions and keywords
  - Automatic database migrations
  - Export to formatted Excel reports

- **Excel Reports**
  - Multi-sheet formatted exports with tables and filtering
  - Color-coding for video status
  - Join view with all related data
  - Keywords usage statistics
  - Word-wrapping for long text with reasonable height limits

## Screenshots

### Excel Report - Main View
![Excel Main View](screenshots/2025-05-21_13-34-53.png)
*The main Videos with Transcripts view showing video metadata, transcription details, and associated keywords*

### Excel Report - Keywords Usage
![Keywords Usage](screenshots/2025-05-21_13-35-02.png)
*Keywords usage statistics showing frequency and associated videos*

### Excel Report - Info Sheet
![Info Sheet](screenshots/2025-05-21_13-35-14.png)
*Documentation sheet with field descriptions and usage tips*

### Markdown Transcript
![Markdown Transcript](screenshots/2025-05-21_13-35-23.png)
*Example of a generated markdown transcript with video metadata, summary, and keywords*

## Requirements

- Python 3.8+
- FFmpeg installed on your system
- CUDA-compatible GPU (optional, for faster transcription)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/tirandagan/whisper-media-catalog.git
   cd whisper-media-catalog
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Install FFmpeg:
   - Ubuntu/Debian: `sudo apt install ffmpeg`
   - macOS: `brew install ffmpeg`
   - Windows: [Download from FFmpeg website](https://www.ffmpeg.org/download.html)

## Configuration

Create or edit the config.ini file:

```ini
[secrets]
openai_api_key = your_openai_api_key_here

[folders]
input = /path/to/your/videos/
database = /path/to/your/database/
transcripts = /path/to/your/transcripts/

[database]
filename = video_library.db

[whisper]
model_size = base
language = en
```

You can also set the OpenAI API key using an environment variable:
```
export OPENAI_API_KEY=your_api_key_here
```

## Quick Start

```bash
# Clone the repository
git clone https://github.com/tirandagan/whisper-media-catalog.git
cd whisper-media-catalog

# Install dependencies
pip install -r requirements.txt

# Edit config.ini with your OpenAI API key and folders
# Then run
python main.py --verbose
```

## Usage

1. Make sure the input, database, and transcripts folders in your config.ini exist.

2. Run the application:
   ```
   python main.py
   ```

### Command Line Options

- `--config` or `-c`: Specify a custom config file path
  ```
  python main.py --config /path/to/custom_config.ini
  ```

- `--scan-only`: Only scan for videos and extract metadata, skip transcription
  ```
  python main.py --scan-only
  ```

- `--transcribe-only`: Only transcribe videos that have been scanned but not transcribed
  ```
  python main.py --transcribe-only
  ```

- `--single_file`: Process only one new file and then exit
  ```
  python main.py --single_file
  ```

- `--no-excel`: Skip exporting database to Excel at the end
  ```
  python main.py --no-excel
  ```

- `--verbose` or `-v`: Enable verbose output (INFO-level logging)
  ```
  python main.py --verbose
  ```

## Database Schema

The application uses a SQLite database with the following structure:

- `videos`: Stores video file information and technical metadata
  - Tracks file status (New, Transcribed, Missing, Error Transcribing)
  - Contains technical metadata like resolution, encoding, duration

- `transcriptions`: Stores transcription data
  - Full text transcription
  - AI-generated title and summary
  - Path to markdown transcript file

- `keywords`: Reusable content keywords
  - Unique keywords with proper casing rules
  - Used for categorizing content topics

- `transcription_keywords`: Association table for the many-to-many relationship

## Output Files

### Markdown Transcripts

For each transcribed video, a markdown file is created with:
- Title and summary
- File information (duration, resolution, etc.)
- Keywords
- Full transcript text

### Excel Reports

An Excel workbook with multiple sheets is generated:
- Info: Field descriptions and usage tips
- Videos_With_Transcripts: Main view with joined data
- Keywords_Usage: Keyword frequency statistics
- Raw data tables for each database table

## Migration

To update an existing database to the latest schema:

```
python migrate_database.py
```

This ensures all tables and columns are properly created or updated.

## License

MIT