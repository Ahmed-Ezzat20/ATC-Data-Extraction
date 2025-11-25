"""
Gemini API Extractor for ATC Video Subtitles

This module handles the extraction of on-screen subtitles from ATC videos
using Google's Gemini 2.5 Pro API.
"""

import os
import re
import json
from typing import Dict, List, Optional
from google import genai
from google.genai import types


class GeminiExtractor:
    """Extract subtitles from ATC videos using Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-pro"):
        """
        Initialize the Gemini extractor.
        
        Args:
            api_key: Gemini API key. If None, reads from GEMINI_API_KEY env var.
            model: Gemini model to use. Default is "gemini-2.5-pro".
        """
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("API key must be provided or set in GEMINI_API_KEY environment variable")
        
        self.model = f"models/{model}"
        self.client = genai.Client(api_key=self.api_key)
        
        self.prompt = """Analyze this video carefully and extract ALL on-screen text/subtitles with their timestamps.

The video shows ATC (Air Traffic Control) communications with text overlays showing what is being said.

For each piece of text that appears on screen, provide:
1. The timestamp range in format [MM:SS - MM:SS]
2. The exact text content

Format your response as a structured list like this:
[00:05 - 00:11]
[exact text content here]

[00:12 - 00:14]
[exact text content here]

Extract EVERY text segment that appears in the video. Be thorough and accurate with timestamps."""
    
    def extract_video_id(self, url: str) -> str:
        """
        Extract video ID from YouTube URL.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Video ID string
        """
        if "v=" in url:
            return url.split("v=")[1].split("&")[0]
        else:
            return url.split("/")[-1]
    
    def parse_response(self, response_text: str) -> List[Dict]:
        """
        Parse Gemini API response to extract structured segments.
        
        Args:
            response_text: Raw text response from Gemini API
            
        Returns:
            List of segment dictionaries
        """
        segments = []
        lines = response_text.strip().split('\n')
        
        i = 0
        segment_num = 1
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Match timestamp pattern [MM:SS - MM:SS]
            timestamp_match = re.match(r'\[(\d+):(\d+)\s*-\s*(\d+):(\d+)\]', line)
            
            if timestamp_match:
                start_min, start_sec, end_min, end_sec = map(int, timestamp_match.groups())
                start_time = start_min * 60 + start_sec
                end_time = end_min * 60 + end_sec
                
                # Collect transcript lines until next timestamp
                transcript_lines = []
                i += 1
                while i < len(lines) and not re.match(r'\[(\d+):(\d+)\s*-\s*(\d+):(\d+)\]', lines[i].strip()):
                    if lines[i].strip():
                        transcript_lines.append(lines[i].strip())
                    i += 1
                
                transcript = ' '.join(transcript_lines)
                
                segments.append({
                    'segment_num': segment_num,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': end_time - start_time,
                    'timestamp_range': f"[{start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d}]",
                    'transcript': transcript
                })
                segment_num += 1
            else:
                i += 1
        
        return segments
    
    def extract_subtitles(self, video_url: str, save_raw: bool = True, output_dir: str = "data/transcripts") -> Dict:
        """
        Extract subtitles from a YouTube video.
        
        Args:
            video_url: YouTube video URL
            save_raw: Whether to save raw API response
            output_dir: Directory to save output files
            
        Returns:
            Dictionary containing video_id, video_url, total_segments, and segments list
        """
        video_id = self.extract_video_id(video_url)
        
        # Call Gemini API
        response = self.client.models.generate_content(
            model=self.model,
            contents=types.Content(
                parts=[
                    types.Part(file_data=types.FileData(file_uri=video_url)),
                    types.Part(text=self.prompt)
                ]
            )
        )
        
        # Save raw response if requested
        if save_raw:
            os.makedirs(output_dir, exist_ok=True)
            raw_file = os.path.join(output_dir, f"{video_id}_raw.txt")
            with open(raw_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
        
        # Parse response
        segments = self.parse_response(response.text)
        
        # Create result dictionary
        result = {
            'video_id': video_id,
            'video_url': video_url,
            'total_segments': len(segments),
            'segments': segments
        }
        
        # Save JSON
        os.makedirs(output_dir, exist_ok=True)
        json_file = os.path.join(output_dir, f"{video_id}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        return result
    
    def extract_batch(self, video_urls: List[str], delay: float = 2.0, 
                     output_dir: str = "data/transcripts") -> List[Dict]:
        """
        Extract subtitles from multiple videos.
        
        Args:
            video_urls: List of YouTube video URLs
            delay: Delay in seconds between API requests
            output_dir: Directory to save output files
            
        Returns:
            List of result dictionaries
        """
        import time
        
        results = []
        
        for i, url in enumerate(video_urls, 1):
            video_id = self.extract_video_id(url)
            
            # Skip if already processed
            json_file = os.path.join(output_dir, f"{video_id}.json")
            if os.path.exists(json_file):
                print(f"[{i}/{len(video_urls)}] {video_id} - SKIPPED (already processed)")
                with open(json_file, 'r') as f:
                    results.append(json.load(f))
                continue
            
            print(f"[{i}/{len(video_urls)}] Processing {video_id}...")
            
            try:
                result = self.extract_subtitles(url, output_dir=output_dir)
                results.append(result)
                print(f"  ✓ Extracted {result['total_segments']} segments")
                
                # Delay between requests
                if i < len(video_urls):
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"  ✗ ERROR: {str(e)}")
                continue
        
        return results


if __name__ == "__main__":
    # Example usage
    extractor = GeminiExtractor()
    
    # Single video
    result = extractor.extract_subtitles("https://www.youtube.com/watch?v=94VPOXc2bEM")
    print(f"Extracted {result['total_segments']} segments from {result['video_id']}")
