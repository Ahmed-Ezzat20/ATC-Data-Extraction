#!/usr/bin/env python3
"""
Debug Download Issues

Tests yt-dlp downloads and shows detailed error messages.

Usage:
    python debug_downloads.py [--data-dir DATA_DIR] [--test-count N]
"""

import json
import subprocess
import argparse
from pathlib import Path


def test_video_download(video_id, video_url):
    """
    Test downloading a single video and show detailed error.

    Args:
        video_id: Video ID
        video_url: Video URL

    Returns:
        Tuple of (success, error_message)
    """
    # Try to get video info first (faster than download)
    cmd = [
        'yt-dlp',
        '--dump-json',
        '--no-playlist',
        video_url
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return True, None
    except subprocess.TimeoutExpired:
        return False, "Timeout (30s exceeded)"
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else "Unknown error"
        return False, error_msg


def check_failed_videos(data_dir='data', test_count=None):
    """
    Check which videos are failing to download and why.

    Args:
        data_dir: Base data directory
        test_count: Number of failed videos to test (None = all)
    """
    data_path = Path(data_dir)
    transcripts_dir = data_path / 'transcripts'
    audio_segments_dir = data_path / 'audio_segments'

    print("=" * 70)
    print("DOWNLOAD DEBUG TOOL")
    print("=" * 70)

    # Find videos with missing segments
    transcript_files = sorted(transcripts_dir.glob("*.json"))
    transcript_files = [f for f in transcript_files if not f.stem.endswith('_raw')]

    failed_videos = []

    print("\nScanning for videos with missing segments...")

    for json_file in transcript_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        video_id = data['video_id']
        video_url = data['video_url']
        segments = data['segments']

        # Check if any segments are missing
        missing = False
        for seg in segments:
            seg_num = seg['segment_num']
            audio_filename = f"{video_id}_seg{seg_num:03d}.wav"
            audio_path = audio_segments_dir / audio_filename

            if not audio_path.exists():
                missing = True
                break

        if missing:
            failed_videos.append({
                'video_id': video_id,
                'video_url': video_url,
                'segments': len(segments)
            })

    if not failed_videos:
        print("\n[OK] No videos with missing segments found!")
        return

    print(f"Found {len(failed_videos)} videos with missing segments")

    # Test downloads
    test_videos = failed_videos[:test_count] if test_count else failed_videos

    print(f"\nTesting {len(test_videos)} video downloads...")
    print("-" * 70)

    results = {
        'available': [],
        'unavailable': [],
        'private': [],
        'deleted': [],
        'other_error': []
    }

    for i, video_info in enumerate(test_videos, 1):
        video_id = video_info['video_id']
        video_url = video_info['video_url']

        print(f"[{i}/{len(test_videos)}] Testing {video_id}... ", end='', flush=True)

        success, error = test_video_download(video_id, video_url)

        if success:
            print("[OK] Available")
            results['available'].append(video_info)
        else:
            error_lower = error.lower() if error else ""

            if 'private' in error_lower or 'members-only' in error_lower:
                print("[X] Private/Members-only")
                results['private'].append({**video_info, 'error': error})
            elif 'unavailable' in error_lower or 'deleted' in error_lower or 'removed' in error_lower:
                print("[X] Deleted/Unavailable")
                results['unavailable'].append({**video_info, 'error': error})
            elif 'video id' in error_lower:
                print("[X] Invalid Video ID")
                results['deleted'].append({**video_info, 'error': error})
            else:
                print(f"[X] Error: {error[:50]}...")
                results['other_error'].append({**video_info, 'error': error})

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"\nTotal tested: {len(test_videos)}")
    print(f"  Available: {len(results['available'])}")
    print(f"  Private/Members-only: {len(results['private'])}")
    print(f"  Deleted/Unavailable: {len(results['unavailable'])}")
    print(f"  Invalid Video ID: {len(results['deleted'])}")
    print(f"  Other errors: {len(results['other_error'])}")

    # Show details
    if results['private']:
        print(f"\n[!] PRIVATE/MEMBERS-ONLY VIDEOS ({len(results['private'])}):")
        for vid in results['private'][:10]:
            print(f"  - {vid['video_id']} ({vid['segments']} segments)")
            print(f"    URL: {vid['video_url']}")
            print(f"    Error: {vid['error'][:100]}")
        if len(results['private']) > 10:
            print(f"  ... and {len(results['private']) - 10} more")

    if results['unavailable']:
        print(f"\n[!] DELETED/UNAVAILABLE VIDEOS ({len(results['unavailable'])}):")
        for vid in results['unavailable'][:10]:
            print(f"  - {vid['video_id']} ({vid['segments']} segments)")
            print(f"    URL: {vid['video_url']}")
        if len(results['unavailable']) > 10:
            print(f"  ... and {len(results['unavailable']) - 10} more")

    if results['other_error']:
        print(f"\n[!] OTHER ERRORS ({len(results['other_error'])}):")
        for vid in results['other_error'][:5]:
            print(f"  - {vid['video_id']} ({vid['segments']} segments)")
            print(f"    Error: {vid['error']}")
        if len(results['other_error']) > 5:
            print(f"  ... and {len(results['other_error']) - 5} more")

    # Recommendations
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)

    if results['available']:
        print(f"\n[1] {len(results['available'])} videos are available and can be downloaded")
        print("    Issue might be:")
        print("    - yt-dlp needs updating: pip install -U yt-dlp")
        print("    - Rate limiting from YouTube")
        print("    - Network issues")

    if results['private'] or results['unavailable']:
        total_lost = len(results['private']) + len(results['unavailable']) + len(results['deleted'])
        lost_segments = sum(v['segments'] for v in results['private'] + results['unavailable'] + results['deleted'])
        print(f"\n[2] {total_lost} videos are permanently unavailable ({lost_segments} segments)")
        print("    These cannot be recovered. Options:")
        print("    - Remove their transcripts and accept the data loss")
        print("    - Keep transcripts but document missing audio")

    if results['other_error']:
        print(f"\n[3] {len(results['other_error'])} videos have other errors")
        print("    Try:")
        print("    - Update yt-dlp: pip install -U yt-dlp")
        print("    - Check network connection")
        print("    - Run with --verbose to see full errors")

    print("\n" + "=" * 70)

    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Debug video download issues"
    )
    parser.add_argument(
        '--data-dir',
        default='data',
        help='Base data directory (default: data)'
    )
    parser.add_argument(
        '--test-count',
        type=int,
        help='Number of failed videos to test (default: all)'
    )
    parser.add_argument(
        '--export',
        action='store_true',
        help='Export list of unavailable videos to file'
    )

    args = parser.parse_args()

    results = check_failed_videos(args.data_dir, args.test_count)

    if args.export and results:
        output_file = 'unavailable_videos.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("Unavailable Videos\n")
            f.write("=" * 70 + "\n\n")

            all_unavailable = results['private'] + results['unavailable'] + results['deleted']

            for vid in all_unavailable:
                f.write(f"Video ID: {vid['video_id']}\n")
                f.write(f"URL: {vid['video_url']}\n")
                f.write(f"Segments: {vid['segments']}\n")
                f.write(f"Error: {vid.get('error', 'N/A')}\n")
                f.write("-" * 70 + "\n\n")

        print(f"\nExported unavailable videos to: {output_file}")


if __name__ == "__main__":
    main()
