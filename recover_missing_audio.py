#!/usr/bin/env python3
"""
Recovery Script for Missing Audio Segments

Regenerates missing audio segments by re-segmenting from raw audio
or re-downloading and segmenting if raw audio is unavailable.

Usage:
    python recover_missing_audio.py [--data-dir DATA_DIR] [--force-download]
"""

import json
import argparse
import sys
from pathlib import Path
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from segmentation.audio_segmenter import AudioSegmenter


def identify_missing_segments(data_dir='data'):
    """
    Identify videos with missing audio segments.

    Args:
        data_dir: Base data directory

    Returns:
        Tuple of (videos_to_recover, missing_count)
    """
    data_path = Path(data_dir)
    transcripts_dir = data_path / 'transcripts'
    audio_segments_dir = data_path / 'audio_segments'
    raw_audio_dir = data_path / 'raw_audio'

    transcript_files = sorted(transcripts_dir.glob("*.json"))
    transcript_files = [f for f in transcript_files if not f.stem.endswith('_raw')]

    videos_to_recover = []
    total_missing = 0

    # Check raw audio availability
    raw_audio_files = {}
    if raw_audio_dir.exists():
        for audio_file in raw_audio_dir.glob("*"):
            if audio_file.suffix in ['.webm', '.wav', '.mp3', '.m4a']:
                video_id = audio_file.stem
                raw_audio_files[video_id] = audio_file

    print("Scanning for missing segments...")

    for json_file in transcript_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        video_id = data['video_id']
        segments = data['segments']

        missing_segments = []

        for seg in segments:
            seg_num = seg['segment_num']
            audio_filename = f"{video_id}_seg{seg_num:03d}.wav"
            audio_path = audio_segments_dir / audio_filename

            if not audio_path.exists():
                missing_segments.append(seg_num)

        if missing_segments:
            has_raw_audio = video_id in raw_audio_files
            videos_to_recover.append({
                'video_id': video_id,
                'missing_segments': missing_segments,
                'missing_count': len(missing_segments),
                'total_segments': len(segments),
                'has_raw_audio': has_raw_audio
            })
            total_missing += len(missing_segments)

    return videos_to_recover, total_missing


def recover_segments(videos_to_recover, data_dir='data', force_download=False):
    """
    Recover missing audio segments.

    Args:
        videos_to_recover: List of video dictionaries with missing segments
        data_dir: Base data directory
        force_download: Force re-download even if raw audio exists

    Returns:
        Recovery statistics
    """
    segmenter = AudioSegmenter(
        transcripts_dir=str(Path(data_dir) / 'transcripts'),
        raw_audio_dir=str(Path(data_dir) / 'raw_audio'),
        segments_dir=str(Path(data_dir) / 'audio_segments')
    )

    stats = {
        'attempted': 0,
        'successful': 0,
        'failed': 0,
        'segments_recovered': 0
    }

    # Separate videos by whether they have raw audio
    with_raw_audio = [v for v in videos_to_recover if v['has_raw_audio'] and not force_download]
    need_download = [v for v in videos_to_recover if not v['has_raw_audio'] or force_download]

    print("\n" + "=" * 70)
    print("RECOVERY PROCESS")
    print("=" * 70)

    # Process videos with raw audio (faster)
    if with_raw_audio:
        print(f"\n[Phase 1] Re-segmenting from existing raw audio ({len(with_raw_audio)} videos)...")
        print("-" * 70)

        for i, video_info in enumerate(with_raw_audio, 1):
            video_id = video_info['video_id']
            stats['attempted'] += 1

            print(f"[{i}/{len(with_raw_audio)}] {video_id} "
                  f"({video_info['missing_count']}/{video_info['total_segments']} missing)...")

            try:
                result = segmenter.process_video(video_id, download=False)
                stats['successful'] += 1
                stats['segments_recovered'] += result['segments_created']
                print(f"  [OK] Recovered {result['segments_created']} segments")
            except Exception as e:
                stats['failed'] += 1
                print(f"  [X] Error: {e}")

    # Process videos needing download (slower)
    if need_download:
        print(f"\n[Phase 2] Re-downloading and segmenting ({len(need_download)} videos)...")
        print("-" * 70)
        print("NOTE: This may take a while depending on video sizes and network speed.")

        for i, video_info in enumerate(need_download, 1):
            video_id = video_info['video_id']
            stats['attempted'] += 1

            print(f"[{i}/{len(need_download)}] {video_id} "
                  f"({video_info['missing_count']}/{video_info['total_segments']} missing)...")

            try:
                result = segmenter.process_video(video_id, download=True)
                stats['successful'] += 1
                stats['segments_recovered'] += result['segments_created']
                print(f"  [OK] Downloaded and recovered {result['segments_created']} segments")
            except Exception as e:
                stats['failed'] += 1
                print(f"  [X] Error: {e}")

    return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Recover missing audio segments"
    )
    parser.add_argument(
        '--data-dir',
        default='data',
        help='Base data directory (default: data)'
    )
    parser.add_argument(
        '--force-download',
        action='store_true',
        help='Force re-download even if raw audio exists'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually doing it'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("AUDIO SEGMENT RECOVERY")
    print("=" * 70)
    print(f"Data directory: {args.data_dir}")
    print(f"Force download: {args.force_download}")
    print(f"Dry run: {args.dry_run}")

    # Identify missing segments
    videos_to_recover, total_missing = identify_missing_segments(args.data_dir)

    if not videos_to_recover:
        print("\n[OK] No missing segments found. All audio is synchronized!")
        return 0

    print(f"\nFound {len(videos_to_recover)} videos with missing segments")
    print(f"Total missing segments: {total_missing:,}")

    # Categorize
    with_raw = sum(1 for v in videos_to_recover if v['has_raw_audio'])
    without_raw = len(videos_to_recover) - with_raw

    print(f"\nRecovery strategy:")
    print(f"  - Re-segment from raw audio: {with_raw} videos")
    print(f"  - Re-download and segment: {without_raw} videos")

    if args.dry_run:
        print("\n[DRY RUN] Would recover segments from these videos:")
        for video_info in videos_to_recover[:10]:
            method = "re-segment" if video_info['has_raw_audio'] else "re-download"
            print(f"  - {video_info['video_id']}: {video_info['missing_count']} segments ({method})")
        if len(videos_to_recover) > 10:
            print(f"  ... and {len(videos_to_recover) - 10} more")
        return 0

    # Confirm
    print("\n" + "-" * 70)
    response = input("Proceed with recovery? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Recovery cancelled.")
        return 0

    # Recover
    stats = recover_segments(videos_to_recover, args.data_dir, args.force_download)

    # Summary
    print("\n" + "=" * 70)
    print("RECOVERY SUMMARY")
    print("=" * 70)
    print(f"Videos attempted: {stats['attempted']}")
    print(f"Videos successful: {stats['successful']}")
    print(f"Videos failed: {stats['failed']}")
    print(f"Segments recovered: {stats['segments_recovered']:,}")

    if stats['failed'] > 0:
        print(f"\n[!] {stats['failed']} videos failed to recover.")
        print("    Run the diagnostic script to identify issues:")
        print("    python diagnose_missing_audio.py --export-list")

    print("\nRun validation again to verify:")
    print("    python validate_data.py")

    return 0 if stats['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
