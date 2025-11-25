#!/usr/bin/env python3
"""
Extract subtitles from all videos in a YouTube playlist.

Usage:
    python extract_playlist.py --playlist-url "PLAYLIST_URL" [--output-dir DIR] [--delay SECONDS]
"""

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from .gemini_extractor import GeminiExtractor


def get_playlist_videos(playlist_url: str) -> list:
    """
    Extract all video URLs from a YouTube playlist.
    
    Args:
        playlist_url: YouTube playlist URL
        
    Returns:
        List of video URLs
    """
    print("Extracting video URLs from playlist...")
    
    try:
        result = subprocess.run(
            ['yt-dlp', '--flat-playlist', '--get-id', playlist_url],
            capture_output=True,
            text=True,
            check=True
        )
        
        video_ids = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        video_urls = [f"https://www.youtube.com/watch?v={vid}" for vid in video_ids]
        
        print(f"✓ Found {len(video_urls)} videos in playlist")
        return video_urls
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Error extracting playlist: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Extract subtitles from YouTube playlist using Gemini API"
    )
    parser.add_argument(
        '--playlist-url',
        required=True,
        help='YouTube playlist URL'
    )
    parser.add_argument(
        '--output-dir',
        default='data/transcripts',
        help='Output directory for transcripts (default: data/transcripts)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay in seconds between API requests (default: 2.0)'
    )
    parser.add_argument(
        '--api-key',
        help='Gemini API key (default: reads from GEMINI_API_KEY env var)'
    )
    
    args = parser.parse_args()
    
    # Get playlist videos
    video_urls = get_playlist_videos(args.playlist_url)
    
    # Initialize extractor
    extractor = GeminiExtractor(api_key=args.api_key)
    
    # Create output directory
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    # Process videos
    print(f"\n{'='*70}")
    print(f"PROCESSING {len(video_urls)} VIDEOS")
    print(f"{'='*70}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Output directory: {args.output_dir}")
    print(f"Delay between requests: {args.delay}s")
    print(f"{'='*70}\n")
    
    start_time = datetime.now()
    
    results = extractor.extract_batch(
        video_urls,
        delay=args.delay,
        output_dir=args.output_dir
    )
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    # Summary
    total_segments = sum(r['total_segments'] for r in results)
    
    print(f"\n{'='*70}")
    print("EXTRACTION COMPLETE")
    print(f"{'='*70}")
    print(f"Total videos: {len(video_urls)}")
    print(f"Successfully processed: {len(results)}")
    print(f"Total segments: {total_segments:,}")
    print(f"Duration: {duration}")
    print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
