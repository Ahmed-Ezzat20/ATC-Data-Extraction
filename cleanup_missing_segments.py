#!/usr/bin/env python3
"""
Cleanup Missing Segments

Removes segments from transcripts that don't have corresponding audio files,
then regenerates CSV files and analysis reports to sync all components.

This accepts data loss for unavailable videos and ensures all components
are synchronized.

Usage:
    python cleanup_missing_segments.py [--data-dir DATA_DIR] [--backup]
"""

import json
import shutil
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from analysis.analyzer import Analyzer
from analysis.visualizer import Visualizer


def backup_data(data_dir):
    """
    Create backup of data directory.

    Args:
        data_dir: Data directory path

    Returns:
        Path to backup directory
    """
    data_path = Path(data_dir)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = data_path.parent / f"{data_path.name}_backup_{timestamp}"

    print(f"Creating backup: {backup_path}")
    shutil.copytree(data_path, backup_path, dirs_exist_ok=True)

    return backup_path


def cleanup_transcripts(data_dir='data'):
    """
    Remove segments from transcripts that don't have audio files.

    Args:
        data_dir: Base data directory

    Returns:
        Dictionary with cleanup statistics
    """
    data_path = Path(data_dir)
    transcripts_dir = data_path / 'transcripts'
    audio_segments_dir = data_path / 'audio_segments'

    transcript_files = sorted(transcripts_dir.glob("*.json"))
    transcript_files = [f for f in transcript_files if not f.stem.endswith('_raw')]

    stats = {
        'videos_processed': 0,
        'videos_modified': 0,
        'videos_removed': 0,
        'segments_before': 0,
        'segments_after': 0,
        'segments_removed': 0
    }

    print("\n" + "=" * 70)
    print("CLEANING UP TRANSCRIPTS")
    print("=" * 70)
    print(f"\nProcessing {len(transcript_files)} transcript files...")
    print("-" * 70)

    for json_file in transcript_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        video_id = data['video_id']
        original_segments = data['segments']
        stats['videos_processed'] += 1
        stats['segments_before'] += len(original_segments)

        # Filter segments that have audio files
        kept_segments = []
        removed_segments = []

        for seg in original_segments:
            seg_num = seg['segment_num']
            audio_filename = f"{video_id}_seg{seg_num:03d}.wav"
            audio_path = audio_segments_dir / audio_filename

            if audio_path.exists():
                kept_segments.append(seg)
            else:
                removed_segments.append(seg_num)

        # Update statistics
        stats['segments_after'] += len(kept_segments)
        stats['segments_removed'] += len(removed_segments)

        # Handle the file based on what's left
        if len(kept_segments) == 0:
            # Remove transcript entirely if no segments have audio
            print(f"[X] {video_id}: Removing (0/{len(original_segments)} segments have audio)")
            json_file.unlink()
            stats['videos_removed'] += 1

        elif len(removed_segments) > 0:
            # Update transcript with only kept segments
            print(f"[~] {video_id}: Keeping {len(kept_segments)}/{len(original_segments)} segments")

            # Renumber segments sequentially
            for i, seg in enumerate(kept_segments, 1):
                seg['segment_num'] = i

            # Update data
            data['segments'] = kept_segments

            # Write back to file
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            stats['videos_modified'] += 1

        else:
            # All segments present, no changes needed
            print(f"[OK] {video_id}: All {len(original_segments)} segments present")

    return stats


def rename_audio_files(data_dir='data'):
    """
    Rename audio files to match renumbered segments.

    Args:
        data_dir: Base data directory

    Returns:
        Number of files renamed
    """
    data_path = Path(data_dir)
    transcripts_dir = data_path / 'transcripts'
    audio_segments_dir = data_path / 'audio_segments'

    transcript_files = sorted(transcripts_dir.glob("*.json"))
    transcript_files = [f for f in transcript_files if not f.stem.endswith('_raw')]

    print("\n" + "=" * 70)
    print("RENAMING AUDIO FILES")
    print("=" * 70)

    renamed_count = 0

    for json_file in transcript_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        video_id = data['video_id']
        segments = data['segments']

        # Check if renaming is needed
        for new_num, seg in enumerate(segments, 1):
            old_num = seg.get('original_segment_num', seg['segment_num'])

            if old_num != new_num:
                old_filename = f"{video_id}_seg{old_num:03d}.wav"
                new_filename = f"{video_id}_seg{new_num:03d}.wav"

                old_path = audio_segments_dir / old_filename
                new_path = audio_segments_dir / new_filename

                if old_path.exists() and not new_path.exists():
                    old_path.rename(new_path)
                    renamed_count += 1

    if renamed_count > 0:
        print(f"Renamed {renamed_count} audio files to match new segment numbers")
    else:
        print("No renaming needed")

    return renamed_count


def regenerate_outputs(data_dir='data'):
    """
    Regenerate CSV files and analysis reports.

    Args:
        data_dir: Base data directory
    """
    print("\n" + "=" * 70)
    print("REGENERATING OUTPUTS")
    print("=" * 70)

    data_path = Path(data_dir)

    # Initialize analyzer
    analyzer = Analyzer(transcripts_dir=str(data_path / 'transcripts'))

    # Generate CSV files
    print("\nGenerating CSV files...")
    analyzer.generate_csv(
        output_file=str(data_path / 'all_segments.csv'),
        detailed=False
    )
    print("  [OK] all_segments.csv")

    analyzer.generate_csv(
        output_file=str(data_path / 'all_segments_detailed.csv'),
        detailed=True
    )
    print("  [OK] all_segments_detailed.csv")

    # Generate analysis report
    print("\nGenerating analysis report...")
    analyzer.generate_report(
        output_file=str(data_path / 'analysis_report.txt')
    )
    print("  [OK] analysis_report.txt")

    # Regenerate visualizations
    print("\nRegenerating visualizations...")
    visualizer = Visualizer(
        output_dir=str(data_path / 'visualizations')
    )
    visualizer.create_all_visualizations()
    print("  [OK] Visualizations created")

    # Get final statistics
    duration_stats = analyzer.analyze_duration()
    vocab_stats = analyzer.analyze_vocabulary()

    return duration_stats, vocab_stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cleanup missing segments and sync all components"
    )
    parser.add_argument(
        '--data-dir',
        default='data',
        help='Base data directory (default: data)'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup before cleanup (recommended)'
    )
    parser.add_argument(
        '--no-rename',
        action='store_true',
        help='Skip renaming audio files (keep original segment numbers)'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("CLEANUP MISSING SEGMENTS")
    print("=" * 70)
    print(f"\nData directory: {args.data_dir}")
    print(f"Backup: {'Yes' if args.backup else 'No'}")

    # Warning
    print("\n" + "!" * 70)
    print("WARNING: This will modify your transcript files")
    print("         Segments without audio will be removed")
    print("         This operation cannot be undone without a backup")
    print("!" * 70)

    response = input("\nProceed with cleanup? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cleanup cancelled.")
        return 0

    # Create backup if requested
    if args.backup:
        backup_path = backup_data(args.data_dir)
        print(f"[OK] Backup created at: {backup_path}\n")

    # Step 1: Clean up transcripts
    stats = cleanup_transcripts(args.data_dir)

    # Step 2: Rename audio files (optional)
    if not args.no_rename:
        renamed = rename_audio_files(args.data_dir)
        stats['files_renamed'] = renamed

    # Step 3: Regenerate outputs
    duration_stats, vocab_stats = regenerate_outputs(args.data_dir)

    # Final summary
    print("\n" + "=" * 70)
    print("CLEANUP SUMMARY")
    print("=" * 70)

    print(f"\nTranscript Changes:")
    print(f"  Videos processed: {stats['videos_processed']}")
    print(f"  Videos modified: {stats['videos_modified']}")
    print(f"  Videos removed: {stats['videos_removed']}")
    print(f"  Remaining videos: {stats['videos_processed'] - stats['videos_removed']}")

    print(f"\nSegment Changes:")
    print(f"  Before cleanup: {stats['segments_before']:,}")
    print(f"  After cleanup: {stats['segments_after']:,}")
    print(f"  Removed: {stats['segments_removed']:,}")
    print(f"  Retention rate: {stats['segments_after']/stats['segments_before']*100:.1f}%")

    print(f"\nFinal Statistics:")
    print(f"  Total videos: {duration_stats['total_videos']}")
    print(f"  Total segments: {duration_stats['total_segments']:,}")
    print(f"  Total duration: {duration_stats['total_duration_minutes']:.1f} minutes")
    print(f"  Total words: {vocab_stats['total_words']:,}")
    print(f"  Unique words: {vocab_stats['unique_words']:,}")

    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("\n1. Validate synchronization:")
    print("   python validate_data.py")
    print("\n2. Review updated files:")
    print(f"   - {args.data_dir}/all_segments.csv")
    print(f"   - {args.data_dir}/all_segments_detailed.csv")
    print(f"   - {args.data_dir}/analysis_report.txt")

    if args.backup:
        print(f"\n3. If satisfied, you can delete the backup:")
        print(f"   rm -rf {backup_path}")

    print("\n" + "=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
