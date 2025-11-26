#!/usr/bin/env python3
"""
Diagnostic Script for Missing Audio Segments

Identifies which audio segments are missing and provides recovery options.

Usage:
    python diagnose_missing_audio.py [--data-dir DATA_DIR] [--export-list]
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict


def diagnose_missing_segments(data_dir='data'):
    """
    Diagnose missing audio segments.

    Args:
        data_dir: Base data directory

    Returns:
        Dictionary with diagnostic information
    """
    data_path = Path(data_dir)
    transcripts_dir = data_path / 'transcripts'
    audio_segments_dir = data_path / 'audio_segments'
    raw_audio_dir = data_path / 'raw_audio'

    # Load all transcripts
    transcript_files = sorted(transcripts_dir.glob("*.json"))
    transcript_files = [f for f in transcript_files if not f.stem.endswith('_raw')]

    print("=" * 70)
    print("MISSING AUDIO SEGMENTS DIAGNOSTIC")
    print("=" * 70)
    print(f"\nData directory: {data_path.absolute()}")
    print(f"Transcript files: {len(transcript_files)}")

    # Track missing segments by video
    missing_by_video = defaultdict(list)
    videos_with_missing = []
    videos_complete = []
    total_expected = 0
    total_missing = 0

    # Check raw audio availability
    raw_audio_files = {}
    if raw_audio_dir.exists():
        for audio_file in raw_audio_dir.glob("*.wav"):
            video_id = audio_file.stem
            raw_audio_files[video_id] = audio_file

    print("\n" + "-" * 70)
    print("Analyzing segments by video...")
    print("-" * 70)

    for json_file in transcript_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        video_id = data['video_id']
        segments = data['segments']

        missing_segments = []

        for seg in segments:
            total_expected += 1
            seg_num = seg['segment_num']
            audio_filename = f"{video_id}_seg{seg_num:03d}.wav"
            audio_path = audio_segments_dir / audio_filename

            if not audio_path.exists():
                total_missing += 1
                missing_segments.append({
                    'segment_num': seg_num,
                    'audio_filename': audio_filename,
                    'start_time': seg['start_time'],
                    'duration': seg['duration']
                })

        if missing_segments:
            has_raw_audio = video_id in raw_audio_files
            missing_by_video[video_id] = {
                'missing_segments': missing_segments,
                'total_segments': len(segments),
                'missing_count': len(missing_segments),
                'has_raw_audio': has_raw_audio,
                'raw_audio_path': str(raw_audio_files.get(video_id, 'N/A'))
            }
            videos_with_missing.append(video_id)
        else:
            videos_complete.append(video_id)

    # Print summary
    print(f"\nTotal expected segments: {total_expected:,}")
    print(f"Total missing segments: {total_missing:,}")
    print(f"Videos complete: {len(videos_complete)}")
    print(f"Videos with missing segments: {len(videos_with_missing)}")

    # Detailed breakdown
    if missing_by_video:
        print("\n" + "=" * 70)
        print("VIDEOS WITH MISSING SEGMENTS")
        print("=" * 70)

        # Sort by missing count
        sorted_videos = sorted(
            missing_by_video.items(),
            key=lambda x: x[1]['missing_count'],
            reverse=True
        )

        for video_id, info in sorted_videos[:20]:  # Show top 20
            print(f"\n{video_id}:")
            print(f"  Missing: {info['missing_count']}/{info['total_segments']} segments")
            print(f"  Raw audio available: {'YES' if info['has_raw_audio'] else 'NO'}")

            if info['missing_count'] <= 5:
                print(f"  Missing segment numbers: {[s['segment_num'] for s in info['missing_segments']]}")

        if len(sorted_videos) > 20:
            print(f"\n... and {len(sorted_videos) - 20} more videos")

    # Recovery analysis
    print("\n" + "=" * 70)
    print("RECOVERY ANALYSIS")
    print("=" * 70)

    can_recover_with_raw = sum(
        1 for v in missing_by_video.values() if v['has_raw_audio']
    )
    cannot_recover = sum(
        1 for v in missing_by_video.values() if not v['has_raw_audio']
    )

    print(f"\nVideos that can be recovered (have raw audio): {can_recover_with_raw}")
    print(f"Videos that need re-download (no raw audio): {cannot_recover}")

    if cannot_recover > 0:
        print("\nVideos requiring re-download:")
        for video_id, info in missing_by_video.items():
            if not info['has_raw_audio']:
                print(f"  - {video_id} ({info['missing_count']} segments)")

    return {
        'total_expected': total_expected,
        'total_missing': total_missing,
        'videos_complete': videos_complete,
        'videos_with_missing': videos_with_missing,
        'missing_by_video': missing_by_video,
        'can_recover_with_raw': can_recover_with_raw,
        'cannot_recover': cannot_recover
    }


def export_missing_list(missing_by_video, output_file='missing_segments.txt'):
    """
    Export list of missing segments to file.

    Args:
        missing_by_video: Dictionary of missing segments by video
        output_file: Output file path
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Missing Audio Segments\n")
        f.write("=" * 70 + "\n\n")

        for video_id, info in sorted(missing_by_video.items()):
            f.write(f"\n{video_id}\n")
            f.write(f"  Total segments: {info['total_segments']}\n")
            f.write(f"  Missing: {info['missing_count']}\n")
            f.write(f"  Raw audio: {info['raw_audio_path']}\n")
            f.write(f"  Missing segment files:\n")

            for seg in info['missing_segments']:
                f.write(f"    - {seg['audio_filename']} (seg#{seg['segment_num']}, "
                       f"start={seg['start_time']:.2f}s, dur={seg['duration']:.2f}s)\n")

    print(f"\nDetailed list exported to: {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Diagnose missing audio segments"
    )
    parser.add_argument(
        '--data-dir',
        default='data',
        help='Base data directory (default: data)'
    )
    parser.add_argument(
        '--export-list',
        action='store_true',
        help='Export detailed list of missing segments to file'
    )

    args = parser.parse_args()

    # Run diagnostics
    results = diagnose_missing_segments(args.data_dir)

    # Export if requested
    if args.export_list:
        export_missing_list(
            results['missing_by_video'],
            'missing_segments.txt'
        )

    # Print recommendations
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)

    if results['cannot_recover'] > 0:
        print("\n[1] Re-download and segment the affected videos:")
        print("    This is required for videos without raw audio files.")
        print("\n    Create a file 'videos_to_reprocess.txt' with video IDs")
        print("    and use the recovery script (see below).")

    if results['can_recover_with_raw'] > 0:
        print("\n[2] Re-segment from existing raw audio:")
        print("    For videos with raw audio available, just re-run segmentation:")
        print("\n    python main.py --playlist-url 'URL' \\")
        print("               --skip-extraction --skip-download")

    print("\n[3] Generate recovery script:")
    print("    python generate_recovery_script.py")
    print("    This will create targeted recovery scripts for missing segments.")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
