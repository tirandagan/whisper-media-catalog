import os
import json
import subprocess
import logging
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import ffmpeg

from lib.database.models import Video, Transcription

logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self, config_manager):
        """
        Initialize the video processor
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.input_folder = self.config_manager.get_input_folder()
        
        # Initialize database connection
        db_path = self.config_manager.get_database_path()
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.Session = sessionmaker(bind=self.engine)
        
        # Expose models for external access
        self.Video = Video
        self.Transcription = Transcription
    
    def scan_input_folder(self):
        """
        Scan the input folder for video files and process new ones
        
        Returns:
            list: List of video IDs added to the database
        """
        if not os.path.exists(self.input_folder):
            logger.error(f"Input folder does not exist: {self.input_folder}")
            raise FileNotFoundError(f"Input folder does not exist: {self.input_folder}")
        
        # Get list of supported video file extensions
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v']
        
        # Find all video files in the input folder
        video_files = []
        for root, _, files in os.walk(self.input_folder):
            for file in files:
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    video_files.append(os.path.join(root, file))
        
        # Build a set of filepaths for quick lookup
        found_filepaths = set(video_files)
        
        # Process each video file
        new_video_ids = []
        with self.Session() as session:
            # First check for existing videos and update their status if missing
            self.check_missing_videos(session, found_filepaths)
            
            for video_path in video_files:
                # Check if video is already in the database
                filename = os.path.basename(video_path)
                existing_video = session.query(Video).filter_by(filename=filename).first()
                
                if existing_video:
                    # Video exists - check if it was previously marked as missing
                    if existing_video.status == "Missing":
                        logger.info(f"Video was previously missing but now found: {filename}")
                        existing_video.status = "New"
                        existing_video.filepath = video_path  # Update the path in case it changed
                        session.commit()
                    
                    logger.debug(f"Video already in database: {filename}")
                    continue
                
                # Extract metadata and add to database
                try:
                    video_metadata = self.extract_metadata(video_path)
                    
                    # Skip if we couldn't extract proper video metadata
                    if not video_metadata.get('width') or not video_metadata.get('height'):
                        logger.warning(f"Skipping {filename}: Could not extract valid video dimensions")
                        continue
                        
                    new_video = Video(
                        filename=filename,
                        filepath=video_path,
                        filesize=video_metadata.get('filesize', 0),
                        duration=video_metadata.get('duration', 0),
                        encoding=video_metadata.get('codec_name', ''),
                        resolution=f"{video_metadata.get('width', 0)}x{video_metadata.get('height', 0)}",
                        width=video_metadata.get('width', 0),
                        height=video_metadata.get('height', 0),
                        bitrate=video_metadata.get('bitrate', 0),
                        fps=video_metadata.get('fps', 0),
                        status="New"  # Set initial status
                    )
                    
                    # Create an empty transcription record
                    transcription = Transcription(
                        is_transcribed=False
                    )
                    
                    new_video.transcription = transcription
                    session.add(new_video)
                    session.commit()
                    
                    # Store only the ID, not the object itself
                    new_video_ids.append(new_video.id)
                    logger.info(f"Added new video to database: {filename}")
                except Exception as e:
                    logger.error(f"Error processing video {filename}: {e}")
                    continue
        
        # Return video IDs instead of detached objects
        return new_video_ids
    
    def check_missing_videos(self, session, found_filepaths=None):
        """
        Check for videos in database that are missing from the file system
        
        Args:
            session: SQLAlchemy session
            found_filepaths: Optional set of file paths found in the input folder
            
        Returns:
            int: Number of videos marked as missing
        """
        if found_filepaths is None:
            # If no filepaths provided, scan the input folder
            found_filepaths = set()
            if os.path.exists(self.input_folder):
                video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v']
                for root, _, files in os.walk(self.input_folder):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in video_extensions):
                            found_filepaths.add(os.path.join(root, file))
        
        # Get all videos from database
        all_videos = session.query(Video).all()
        missing_count = 0
        
        for video in all_videos:
            if video.status == "Missing":
                # Already marked as missing, check if it's been restored
                if video.filepath in found_filepaths or os.path.exists(video.filepath):
                    video.status = "New" if not video.transcription.is_transcribed else "Transcribed"
                    logger.info(f"Video previously marked as missing has been restored: {video.filename}")
            else:
                # Check if the file exists
                if video.filepath not in found_filepaths and not os.path.exists(video.filepath):
                    video.status = "Missing"
                    logger.warning(f"Video file is missing: {video.filename} (path: {video.filepath})")
                    missing_count += 1
        
        # Commit changes
        if missing_count > 0 or any(v.status == "Missing" for v in all_videos):
            session.commit()
            logger.info(f"Updated status for {missing_count} videos marked as missing")
        
        return missing_count
    
    def get_video_by_id(self, video_id):
        """
        Get a video by its ID with a fresh session
        
        Args:
            video_id: ID of the video to retrieve
            
        Returns:
            Video: The video object or None if not found
        """
        if not video_id:
            logger.error("Invalid video ID: None or empty")
            return None
            
        try:
            with self.Session() as session:
                video = session.query(Video).filter_by(id=video_id).first()
                if video:
                    # Check if the file exists
                    if not os.path.exists(video.filepath):
                        video.status = "Missing"
                        session.commit()
                        logger.warning(f"Video file not found for ID {video_id}: {video.filepath}")
                    return video
                else:
                    logger.error(f"No video found with ID {video_id}")
                    return None
        except Exception as e:
            logger.error(f"Error retrieving video with ID {video_id}: {e}")
            return None
    
    def extract_metadata(self, video_path):
        """
        Extract metadata from a video file using ffmpeg
        
        Args:
            video_path: Path to the video file
            
        Returns:
            dict: Video metadata
        """
        try:
            # Check if file exists
            if not os.path.exists(video_path):
                logger.error(f"Video file does not exist: {video_path}")
                return {'filesize': 0}
                
            # Get file size
            filesize = os.path.getsize(video_path)
            
            try:
                # Get video info using ffprobe
                probe = ffmpeg.probe(video_path)
                
                # Find the video stream
                video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
                
                if video_stream is None:
                    logger.error(f"No video stream found in {video_path}")
                    print(f"No video stream found in {video_path}")
                    return {
                        'filesize': filesize,
                        'codec_name': 'unknown',
                        'width': 0,
                        'height': 0,
                        'duration': 0,
                        'bitrate': 0,
                        'fps': 0
                    }
                
                # Extract relevant metadata
                metadata = {
                    'filesize': filesize,
                    'codec_name': video_stream.get('codec_name', ''),
                    'width': int(video_stream.get('width', 0)),
                    'height': int(video_stream.get('height', 0)),
                    'duration': float(video_stream.get('duration', 0)) if 'duration' in video_stream else 0,
                    'bitrate': int(video_stream.get('bit_rate', 0)) if 'bit_rate' in video_stream else 0
                }
                
                # Calculate FPS
                if 'avg_frame_rate' in video_stream:
                    fps_parts = video_stream['avg_frame_rate'].split('/')
                    if len(fps_parts) == 2 and int(fps_parts[1]) != 0:
                        metadata['fps'] = round(float(int(fps_parts[0]) / int(fps_parts[1])), 2)
                    else:
                        metadata['fps'] = 0
                
                return metadata
                
            except (ffmpeg.Error, FileNotFoundError) as e:
                # If ffprobe is not available, return just the file size
                logger.error(f"FFmpeg error for {video_path}: {str(e)}")
                return {
                    'filesize': filesize,
                    'codec_name': 'unknown',
                    'width': 0,
                    'height': 0,
                    'duration': 0,
                    'bitrate': 0,
                    'fps': 0
                }
                
        except Exception as e:
            logger.error(f"Error extracting metadata for {video_path}: {str(e)}")
            return {
                'filesize': 0,
                'codec_name': 'unknown',
                'width': 0,
                'height': 0,
                'duration': 0,
                'bitrate': 0,
                'fps': 0
            }
    
    def get_untranscribed_videos(self):
        """
        Get list of videos that haven't been transcribed yet
        
        Returns:
            list: List of video IDs
        """
        try:
            with self.Session() as session:
                # First check for missing videos
                self.check_missing_videos(session)
                
                # Only return videos that are not missing
                untranscribed_videos = session.query(Video).join(Transcription).filter(
                    Transcription.is_transcribed == False,
                    Video.status != "Missing"  # Skip missing videos
                ).all()
                
                # Return only the IDs to avoid session issues
                return [video.id for video in untranscribed_videos]
        except Exception as e:
            logger.error(f"Error getting untranscribed videos: {e}")
            return [] 