"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                                                                                ║
║   Video Library Transcription & Management System                              ║
║                                                                                ║
║   Created by: Tiran Dagan                                                      ║
║   Copyright © 2023-2025 Tiran Dagan. All rights reserved.                      ║
║                                                                                ║
║   Transcription module that uses OpenAI Whisper to transcribe video files.     ║
║   This module also handles generating titles, summaries, and keywords using    ║
║   OpenAI GPT-4o, and creating formatted markdown transcripts.                  ║
║                                                                                ║
║   Repository: https://github.com/tirandagan/whisper-media-catalog              ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

import os
import whisper
import logging
import json
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func
from tqdm import tqdm
import openai

from lib.database.models import Video, Transcription, Keyword

logger = logging.getLogger(__name__)

class VideoTranscriber:
    def __init__(self, config_manager):
        """
        Initialize the video transcriber
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.whisper_config = self.config_manager.get_whisper_config()
        self.transcripts_folder = self.config_manager.get_transcripts_folder()
        
        # Initialize database connection
        db_path = self.config_manager.get_database_path()
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.Session = sessionmaker(bind=self.engine)
        
        # Set up OpenAI API
        openai_api_key = self.config_manager.get_openai_api_key()
        if openai_api_key:
            self.client = openai.OpenAI(api_key=openai_api_key)
        else:
            logger.warning("OpenAI API key not found. Title and summary generation will use fallback method.")
            self.client = None
        
        # Load Whisper model
        self.model = None  # Lazy-loaded when needed
    
    def load_model(self):
        """Load the Whisper model if not already loaded"""
        if self.model is None:
            model_size = self.whisper_config.get('model_size', 'base')
            logger.info(f"Loading Whisper model: {model_size}")
            self.model = whisper.load_model(model_size)
            logger.info(f"Whisper model loaded successfully")
    
    def generate_keywords(self, transcript_text, session):
        """
        Generate relevant keywords for a transcription
        
        Args:
            transcript_text: The transcribed text to analyze
            session: SQLAlchemy session to use for database queries
            
        Returns:
            list: List of Keyword objects
        """
        if not transcript_text or not self.client:
            return []
            
        try:
            # Get existing keywords from the database
            existing_keywords = session.query(Keyword).all()
            existing_keyword_names = [k.name.lower() for k in existing_keywords]
            existing_keyword_dict = {k.name.lower(): k for k in existing_keywords}
            # Create lookup dict with original casing
            existing_keywords_original_case = {k.name.lower(): k.name for k in existing_keywords}
            
            # Truncate transcript if too long (to fit within API limits)
            max_tokens = 14000  # Safe limit for o4 model
            truncated_transcript = transcript_text[:max_tokens] if len(transcript_text) > max_tokens else transcript_text
            
            logger.info("Generating keywords using OpenAI")
            
            prompt = f"""
            Here is a transcript of a video. Please generate up to 5 keywords that best represent the main topics.
            
            Here is a list of existing keywords in our database:
            {', '.join(existing_keyword_names) if existing_keyword_names else 'No existing keywords yet'}
            
            If possible, choose from the existing keywords first. Only create new keywords if no existing keywords are appropriate.
            Each keyword should be a single word or short phrase (2-3 words max).
            Format your response as a comma-separated list without numbers or bullet points: keyword1, keyword2, keyword3
            
            Transcript:
            {truncated_transcript}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a media cataloging specialist who assigns relevant keywords to content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            result = response.choices[0].message.content.strip()
            
            # Parse the keywords
            raw_keywords = [k.strip() for k in result.split(',')]
            raw_keywords = [k for k in raw_keywords if k]  # Remove any empty strings
            
            # Limit to 5 keywords
            raw_keywords = raw_keywords[:5]
            
            # Process each keyword for proper casing
            keywords = []
            for keyword in raw_keywords:
                k_lower = keyword.lower()
                
                # Check if this keyword exists in our database (use existing case)
                if k_lower in existing_keywords_original_case:
                    keywords.append(existing_keywords_original_case[k_lower])
                else:
                    # Apply proper casing rules for new keywords
                    formatted_keyword = self.format_keyword_case(keyword)
                    keywords.append(formatted_keyword)
            
            logger.debug(f"Generated keywords: {', '.join(keywords)}")
            
            # Convert to Keyword objects, reusing existing ones where possible
            keyword_objects = []
            for k in keywords:
                k_lower = k.lower()
                if k_lower in existing_keyword_dict:
                    # Use existing keyword with original casing
                    keyword_objects.append(existing_keyword_dict[k_lower])
                else:
                    # Create new keyword with proper casing
                    new_keyword = Keyword(name=k)
                    session.add(new_keyword)
                    # We need to flush to get the ID
                    session.flush()
                    keyword_objects.append(new_keyword)
                    # Add to our dictionary so we can reuse it if it appears again
                    existing_keyword_dict[k_lower] = new_keyword
                    # Also add to our original case dictionary
                    existing_keywords_original_case[k_lower] = k
            
            return keyword_objects
            
        except Exception as e:
            logger.error(f"Error generating keywords: {str(e)}")
            return []
            
    def format_keyword_case(self, keyword):
        """
        Format keyword with proper casing rules:
        - Company names with known abbreviations keep their special casing
        - Other keywords use proper casing (first letter of each word capitalized)
        
        Args:
            keyword: The keyword to format
            
        Returns:
            str: Properly formatted keyword
        """
        # Known company abbreviations/special casings to preserve
        special_cases = {
            "at&t": "AT&T",
            "t-mobile": "T-Mobile",
            "pse&g": "PSE&G",
            "verizon": "Verizon",
            "at": "AT",  # For AT Corporation
            "aol": "AOL",
            "ibm": "IBM",
            "hp": "HP",
            "fcc": "FCC",
            "nasa": "NASA",
            "cnn": "CNN",
            "bbc": "BBC",
            "nbc": "NBC",
            "abc": "ABC",
            "cbs": "CBS",
            "espn": "ESPN",
            "fbi": "FBI",
            "cia": "CIA",
            "dea": "DEA",
            "atm": "ATM",
            "html": "HTML",
            "css": "CSS",
            "php": "PHP",
            "usa": "USA",
            "uk": "UK",
            "un": "UN",
            "eu": "EU",
            "msnbc": "MSNBC",
            "tv": "TV",
            "gps": "GPS",
            "hbo": "HBO",
            "wifi": "WiFi",
            "vpn": "VPN",
            "sms": "SMS",
            "mms": "MMS"
        }
        
        # Check for exact match with special cases (case insensitive)
        keyword_lower = keyword.lower()
        if keyword_lower in special_cases:
            return special_cases[keyword_lower]
        
        # For compound words with special cases
        words = keyword_lower.split()
        for i, word in enumerate(words):
            if word in special_cases:
                words[i] = special_cases[word]
            else:
                # Apply title case for regular words
                words[i] = word.capitalize()
        
        # Handle hyphenated words
        result = ' '.join(words)
        
        # Process hyphenated parts
        if '-' in result:
            parts = result.split('-')
            processed_parts = []
            
            for part in parts:
                part_lower = part.lower()
                if part_lower in special_cases:
                    processed_parts.append(special_cases[part_lower])
                else:
                    processed_parts.append(part.capitalize())
            
            result = '-'.join(processed_parts)
        
        # Handle special case of '&' (ensure words after & are capitalized)
        if '&' in result:
            parts = result.split('&')
            processed_parts = [parts[0]]
            
            for part in parts[1:]:
                if part and part[0] != ' ':
                    processed_parts.append('&' + part.capitalize())
                else:
                    # Handle case with space after '&'
                    words_after_amp = part.split()
                    if words_after_amp:
                        words_after_amp[0] = words_after_amp[0].capitalize()
                    processed_parts.append('&' + ' '.join(words_after_amp))
            
            result = ''.join(processed_parts)
        
        return result
    
    def transcribe_videos(self, video_ids=None):
        """
        Transcribe videos that haven't been transcribed yet
        
        Args:
            video_ids: List of video IDs to transcribe (if None, get untranscribed videos from DB)
        
        Returns:
            int: Number of videos transcribed
        """
        # Load model if needed
        self.load_model()
        
        # If no video IDs provided, get untranscribed videos from database
        if video_ids is None:
            with self.Session() as session:
                videos = session.query(Video).join(Transcription).filter(
                    Transcription.is_transcribed == False
                ).all()
                video_ids = [v.id for v in videos]
        
        if not video_ids:
            logger.info("No videos to transcribe")
            return 0
        
        logger.info(f"Found {len(video_ids)} videos to transcribe")
        
        # For non-verbose mode, print a minimal message
        if logging.getLogger().level > logging.INFO and video_ids:
            print(f"Transcribing {len(video_ids)} video(s)...")
        
        # Transcribe each video
        transcribed_count = 0
        
        # Get logger's level to determine if we're in verbose mode
        is_verbose = logging.getLogger().level <= logging.INFO
        
        # Work with one video at a time to avoid session issues
        for video_id in tqdm(
            video_ids, 
            desc="Transcribing videos",
            disable=not is_verbose and len(video_ids) == 1  # Hide progress for single file in quiet mode
        ):
            try:
                # Get a fresh copy of the video from the database
                with self.Session() as session:
                    video = session.query(Video).filter(Video.id == video_id).first()
                    if not video:
                        logger.error(f"Could not find video with ID {video_id}")
                        continue
                    
                    # Transcribe video
                    logger.info(f"Transcribing video: {video.filename}")
                    
                    # Ensure the transcript folder exists
                    os.makedirs(self.transcripts_folder, exist_ok=True)
                    
                    # Check if the video file exists
                    if not os.path.exists(video.filepath):
                        logger.error(f"Video file not found: {video.filepath}")
                        # Update status to Missing
                        video.status = "Missing"
                        session.commit()
                        continue
                    
                    # Perform transcription using Whisper
                    result = self.model.transcribe(
                        video.filepath,
                        language=self.whisper_config.get('language'),
                        verbose=False
                    )
                    
                    transcript_text = result.get('text', '')
                    
                    # Generate title and summary based on transcript
                    title, summary = self.generate_title_and_summary(transcript_text, video.filename)
                    
                    # Generate keywords for the transcription
                    keywords = self.generate_keywords(transcript_text, session)
                    keyword_names = [k.name for k in keywords]
                    
                    # Save transcript to file as markdown
                    transcript_filename = f"{os.path.splitext(video.filename)[0]}.md"
                    transcript_path = os.path.join(self.transcripts_folder, transcript_filename)
                    
                    # Format creation date in a readable format
                    created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Format file size as a human-readable value
                    def format_filesize(size_bytes):
                        if size_bytes < 1024:
                            return f"{size_bytes} B"
                        elif size_bytes < 1024 * 1024:
                            return f"{size_bytes/1024:.1f} KB"
                        elif size_bytes < 1024 * 1024 * 1024:
                            return f"{size_bytes/(1024*1024):.1f} MB"
                        else:
                            return f"{size_bytes/(1024*1024*1024):.2f} GB"
                    
                    # Format duration as hours:minutes:seconds
                    def format_duration(seconds):
                        hours = int(seconds // 3600)
                        minutes = int((seconds % 3600) // 60)
                        secs = int(seconds % 60)
                        if hours > 0:
                            return f"{hours}:{minutes:02d}:{secs:02d}"
                        else:
                            return f"{minutes}:{secs:02d}"
                    
                    # Create a nicely formatted markdown file
                    with open(transcript_path, 'w', encoding='utf-8') as f:
                        # Title with heading level 1
                        f.write(f"# {title}\n\n")
                        
                        # File information section
                        f.write("## File Information\n\n")
                        f.write(f"- **Filename:** {video.filename}\n")
                        f.write(f"- **Duration:** {format_duration(video.duration)}\n")
                        f.write(f"- **Resolution:** {video.resolution}\n")
                        f.write(f"- **Size:** {format_filesize(video.filesize)}\n")
                        f.write(f"- **Codec:** {video.encoding}\n")
                        f.write(f"- **Transcribed:** {created_date}\n\n")
                        
                        # Summary section
                        f.write("## Summary\n\n")
                        f.write(f"{summary}\n\n")
                        
                        # Keywords section
                        f.write("## Keywords\n\n")
                        if keyword_names:
                            f.write(", ".join(keyword_names) + "\n\n")
                        else:
                            f.write("No keywords available\n\n")
                        
                        # Transcript section
                        f.write("## Transcript\n\n")
                        f.write(f"{transcript_text}\n")
                    
                    # Update the database record
                    try:
                        # Update with all fields including summary and keywords
                        video.transcription.is_transcribed = True
                        video.transcription.transcribed_at = datetime.now()
                        video.transcription.transcript_text = transcript_text
                        video.transcription.transcript_file = transcript_path
                        video.transcription.suggested_title = title
                        video.transcription.summary = summary
                        
                        # Set keywords
                        video.transcription.keywords = keywords
                        
                        # Update video status to Transcribed
                        video.status = "Transcribed"
                        
                        session.commit()
                        logger.info(f"Updated transcription with summary and keywords")
                    except Exception as update_error:
                        # If that fails, try without the summary field
                        logger.warning(f"Error updating with summary and keywords, trying without: {str(update_error)}")
                        session.rollback()
                        
                        video.transcription.is_transcribed = True
                        video.transcription.transcribed_at = datetime.now()
                        video.transcription.transcript_text = transcript_text
                        video.transcription.transcript_file = transcript_path
                        video.transcription.suggested_title = title
                        # Skip the summary and keywords fields
                        session.commit()
                        logger.info(f"Updated transcription without summary and keywords")
                    
                    logger.info(f"Transcription complete for {video.filename}")
                    logger.info(f"Suggested title: {title}")
                    if hasattr(video.transcription, 'summary'):
                        logger.info(f"Summary length: {len(summary)} characters")
                    if keyword_names:
                        logger.info(f"Keywords: {', '.join(keyword_names)}")
                    
                    transcribed_count += 1
                    
            except Exception as e:
                logger.error(f"Error transcribing video with ID {video_id}: {e}")
                # Update status to Error Transcribing
                try:
                    with self.Session() as error_session:
                        error_video = error_session.query(Video).filter(Video.id == video_id).first()
                        if error_video:
                            error_video.status = "Error Transcribing"
                            error_session.commit()
                            logger.info(f"Updated status to 'Error Transcribing' for video ID {video_id}")
                except Exception as status_error:
                    logger.error(f"Could not update status for video ID {video_id}: {status_error}")
                continue
        
        return transcribed_count
    
    def generate_title_and_summary(self, transcript_text, filename):
        """
        Generate a suggested title and summary based on the transcript text
        
        Args:
            transcript_text: The transcribed text
            filename: Original filename for fallback
            
        Returns:
            tuple: (title, summary)
        """
        if not transcript_text:
            return "Untitled Video", "No transcript available"
        
        # Use OpenAI API if available
        if self.client:
            try:
                # Truncate transcript if too long (to fit within API limits)
                max_tokens = 14000  # Safe limit for o4 model
                truncated_transcript = transcript_text[:max_tokens] if len(transcript_text) > max_tokens else transcript_text
                
                logger.info("Generating title and summary using OpenAI")
                
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a media cataloging specialist who creates concise titles and informative summaries for video transcripts."},
                        {"role": "user", "content": f"Here is a transcript of a video. Please provide a short, meaningful title (max 10 words) and a very concise summary (30 words or less) that captures the essence of the content. Format your response exactly as: TITLE: [your title]\nSUMMARY: [your summary]\n\nTranscript:\n{truncated_transcript}"}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                
                result = response.choices[0].message.content.strip()
                
                # Parse the result to extract title and summary
                try:
                    # Extract title and summary from the response
                    title_part = result.split("TITLE:", 1)[1].split("SUMMARY:", 1)[0].strip()
                    summary_part = result.split("SUMMARY:", 1)[1].strip()
                    
                    # Ensure summary is 30 words or less
                    summary_words = summary_part.split()
                    if len(summary_words) > 30:
                        summary_part = " ".join(summary_words[:30]) + "..."
                    
                    return title_part, summary_part
                except (IndexError, AttributeError):
                    logger.warning("Could not parse OpenAI response properly, using fallback method")
                    logger.debug(f"OpenAI response: {result}")
                    # If parsing fails, use the whole response as title
                    lines = result.splitlines()
                    if len(lines) > 1:
                        return lines[0], "\n".join(lines[1:])
                    return result[:50] + "...", result
                    
            except Exception as e:
                logger.error(f"Error calling OpenAI API: {str(e)}")
                # Fall back to the basic method
        
        # Fallback method for title generation
        words = transcript_text.split()
        title_words = words[:7] if len(words) > 7 else words
        title = " ".join(title_words)
        
        if len(words) > 7:
            title += "..."
        
        # Remove trailing punctuation and capitalize
        title = title.rstrip(',.!?:;')
        if title:
            title = title[0].upper() + title[1:]
        
        # Generate a simple summary - limited to 30 words
        sentences = transcript_text.split('.')
        summary = ""
        word_count = 0
        
        for sentence in sentences:
            sentence_words = sentence.split()
            if word_count + len(sentence_words) <= 30:
                if summary and not summary.endswith('.'):
                    summary += '. '
                summary += sentence.strip()
                word_count += len(sentence_words)
            else:
                remaining_words = 30 - word_count
                if remaining_words > 0:
                    summary += " " + " ".join(sentence_words[:remaining_words]) + "..."
                break
        
        if summary and not summary.endswith('.') and not summary.endswith('...'):
            summary += '.'
        
        return title, summary
    
    def generate_title(self, transcript_text):
        """
        Legacy method for backwards compatibility
        """
        title, _ = self.generate_title_and_summary(transcript_text, "")
        return title 