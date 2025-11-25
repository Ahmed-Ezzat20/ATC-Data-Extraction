"""
Audio Segmentation Module

Handles downloading and segmenting audio files based on extracted timestamps.
"""

import os
import json
import subprocess
from typing import Dict, List, Optional
from pathlib import Path


class AudioSegmenter:
    """Segment audio files based on transcript timestamps."""
    
    def __init__(self, 
                 transcripts_dir: str = "data/transcripts",
                 raw_audio_dir: str = "data/raw_audio",
                 segments_dir: str = "data/audio_segments"):
        """
        Initialize the audio segmenter.
        
        Args:
            transcripts_dir: Directory containing transcript JSON files
            raw_audio_dir: Directory containing raw audio files
            segments_dir: Directory to save segmented audio files
        """
        self.transcripts_dir = Path(transcripts_dir)
        self.raw_audio_dir = Path(raw_audio_dir)
        self.segments_dir = Path(segments_dir)
        
        # Create directories
        self.raw_audio_dir.mkdir(parents=True, exist_ok=True)
        self.segments_dir.mkdir(parents=True, exist_ok=True)
    
    def download_audio(self, video_url: str, video_id: str) -> str:
        """
        Download audio from YouTube video.
        
        Args:
            video_url: YouTube video URL
            video_id: Video ID
            
        Returns:
            Path to downloaded audio file
        """
        output_path = self.raw_audio_dir / f"{video_id}.webm"
        
        # Skip if already downloaded
        if output_path.exists():
            return str(output_path)
        
        cmd = [
            'yt-dlp',
            '-f', 'bestaudio',
            '-o', str(output_path),
            video_url
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return str(output_path)
    
    def segment_audio(self, 
                     audio_file: str,
                     video_id: str,
                     segments: List[Dict],
                     audio_format: str = "wav",
                     sample_rate: int = 44100,
                     channels: int = 2) -> List[str]:
        """
        Segment audio file based on timestamps.
        
        Args:
            audio_file: Path to input audio file
            video_id: Video ID
            segments: List of segment dictionaries with timing info
            audio_format: Output audio format (default: wav)
            sample_rate: Sample rate in Hz (default: 44100)
            channels: Number of audio channels (default: 2)
            
        Returns:
            List of paths to created segment files
        """
        output_files = []
        
        for seg in segments:
            segment_num = seg['segment_num']
            start_time = seg['start_time']
            duration = seg['duration']
            
            output_filename = f"{video_id}_seg{segment_num:03d}.{audio_format}"
            output_path = self.segments_dir / output_filename
            
            # Skip if already exists
            if output_path.exists():
                output_files.append(str(output_path))
                continue
            
            # FFmpeg command
            cmd = [
                'ffmpeg',
                '-i', audio_file,
                '-ss', str(start_time),
                '-t', str(duration),
                '-acodec', 'pcm_s16le',
                '-ar', str(sample_rate),
                '-ac', str(channels),
                str(output_path),
                '-y',
                '-loglevel', 'error'
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=30)
                output_files.append(str(output_path))
            except subprocess.TimeoutExpired:
                print(f"  ✗ Timeout segmenting {output_filename}")
            except subprocess.CalledProcessError as e:
                print(f"  ✗ Error segmenting {output_filename}: {e}")
        
        return output_files
    
    def process_video(self, video_id: str, download: bool = True) -> Dict:
        """
        Process a single video: download audio and segment.
        
        Args:
            video_id: Video ID
            download: Whether to download audio (default: True)
            
        Returns:
            Dictionary with processing results
        """
        # Load transcript
        transcript_file = self.transcripts_dir / f"{video_id}.json"
        
        if not transcript_file.exists():
            raise FileNotFoundError(f"Transcript not found: {transcript_file}")
        
        with open(transcript_file, 'r') as f:
            data = json.load(f)
        
        video_url = data['video_url']
        segments = data['segments']
        
        # Download audio if needed
        if download:
            audio_file = self.download_audio(video_url, video_id)
        else:
            audio_file = str(self.raw_audio_dir / f"{video_id}.webm")
            if not Path(audio_file).exists():
                raise FileNotFoundError(f"Audio file not found: {audio_file}")
        
        # Segment audio
        output_files = self.segment_audio(audio_file, video_id, segments)
        
        return {
            'video_id': video_id,
            'audio_file': audio_file,
            'segments_created': len(output_files),
            'total_segments': len(segments),
            'output_files': output_files
        }
    
    def process_all(self, download: bool = True) -> List[Dict]:
        """
        Process all videos in transcripts directory.
        
        Args:
            download: Whether to download audio (default: True)
            
        Returns:
            List of processing result dictionaries
        """
        transcript_files = sorted(self.transcripts_dir.glob("*.json"))
        # Exclude raw files
        transcript_files = [f for f in transcript_files if not f.stem.endswith('_raw')]
        
        results = []
        
        for i, transcript_file in enumerate(transcript_files, 1):
            video_id = transcript_file.stem
            
            print(f"[{i}/{len(transcript_files)}] Processing {video_id}...")
            
            try:
                result = self.process_video(video_id, download=download)
                results.append(result)
                print(f"  ✓ Created {result['segments_created']}/{result['total_segments']} segments")
            except Exception as e:
                print(f"  ✗ Error: {e}")
                continue
        
        return results


if __name__ == "__main__":
    # Example usage
    segmenter = AudioSegmenter()
    
    # Process single video
    result = segmenter.process_video("94VPOXc2bEM", download=True)
    print(f"Created {result['segments_created']} segments")
