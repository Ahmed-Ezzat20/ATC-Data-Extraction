#!/usr/bin/env python3
"""
Clean Dataset - Remove Filtered Segments

Removes segments listed in segments_to_filter.csv from:
- Transcript JSON files
- Audio WAV files
- Regenerates CSV and analysis files

Usage:
    python clean_dataset.py [--filter-file segments_to_filter.csv] [--data-dir data]
"""

import json
import csv
import argparse
import sys
from pathlib import Path
from datetime import datetime
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from analysis.analyzer import Analyzer
from analysis.visualizer import Visualizer


def load_segments_to_filter(filter_file):
    """
    Load segments to filter from CSV file.

    Args:
        filter_file: Path to CSV file with segments to filter

    Returns:
        Set of (video_id, segment_num) tuples
    """
    filter_path = Path(filter_file)

    if not filter_path.exists():
        print(f"[X] Filter file not found: {filter_file}")
        return None

    segments_to_remove = set()

    with open(filter_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        # Check available columns
        fieldnames = reader.fieldnames
        print(f"Filter file columns: {fieldnames}")

        # Determine format
        if 'audio_filename' in fieldnames:
            # Format: audio_filename
            for row in reader:
                audio_filename = row['audio_filename']
                # Parse filename: video_id_seg###.wav
                if '_seg' in audio_filename:
                    parts = audio_filename.replace('.wav', '').split('_seg')
                    video_id = parts[0]
                    segment_num = int(parts[1])
                    segments_to_remove.add((video_id, segment_num))

        elif 'video_id' in fieldnames and 'segment_num' in fieldnames:
            # Format: video_id, segment_num
            for row in reader:
                video_id = row['video_id']
                segment_num = int(row['segment_num'])
                segments_to_remove.add((video_id, segment_num))

        else:
            print(f"[X] Unknown CSV format. Expected columns:")
            print("    - 'audio_filename', OR")
            print("    - 'video_id' and 'segment_num'")
            return None

    print(f"Loaded {len(segments_to_remove)} segments to remove")
    return segments_to_remove


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
    backup_path = data_path.parent / f"{data_path.name}_backup_cleaned_{timestamp}"

    print(f"Creating backup: {backup_path}")
    shutil.copytree(data_path, backup_path, dirs_exist_ok=True)

    return backup_path


def clean_transcripts(data_dir, segments_to_remove):
    """
    Remove filtered segments from transcript files.

    Args:
        data_dir: Data directory
        segments_to_remove: Set of (video_id, segment_num) tuples

    Returns:
        Statistics dictionary
    """
    data_path = Path(data_dir)
    transcripts_dir = data_path / 'transcripts'

    transcript_files = sorted(transcripts_dir.glob('*.json'))
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
    print("CLEANING TRANSCRIPTS")
    print("=" * 70)

    for json_file in transcript_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        video_id = data['video_id']
        original_segments = data['segments']
        stats['videos_processed'] += 1
        stats['segments_before'] += len(original_segments)

        # Filter out segments to remove
        kept_segments = []
        removed_count = 0

        for seg in original_segments:
            seg_num = seg['segment_num']

            if (video_id, seg_num) in segments_to_remove:
                removed_count += 1
            else:
                kept_segments.append(seg)

        stats['segments_after'] += len(kept_segments)
        stats['segments_removed'] += removed_count

        # Handle the file based on what's left
        if len(kept_segments) == 0:
            # Remove transcript entirely
            print(f"[X] {video_id}: Removing entirely (all segments filtered)")
            json_file.unlink()
            stats['videos_removed'] += 1

        elif removed_count > 0:
            # Update transcript
            print(f"[~] {video_id}: Removed {removed_count} segments, kept {len(kept_segments)}")

            # Renumber segments sequentially
            for i, seg in enumerate(kept_segments, 1):
                seg['segment_num'] = i

            # Update data
            data['segments'] = kept_segments

            # Write back
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            stats['videos_modified'] += 1

        else:
            # No changes
            print(f"[OK] {video_id}: No segments filtered")

    return stats


def delete_audio_files(data_dir, segments_to_remove):
    """
    Delete audio files for filtered segments.

    Args:
        data_dir: Data directory
        segments_to_remove: Set of (video_id, segment_num) tuples

    Returns:
        Number of files deleted
    """
    data_path = Path(data_dir)
    audio_dir = data_path / 'audio_segments'

    print("\n" + "=" * 70)
    print("DELETING AUDIO FILES")
    print("=" * 70)

    deleted = 0

    for video_id, segment_num in segments_to_remove:
        audio_filename = f"{video_id}_seg{segment_num:03d}.wav"
        audio_path = audio_dir / audio_filename

        if audio_path.exists():
            audio_path.unlink()
            deleted += 1
            if deleted % 100 == 0:
                print(f"  Deleted {deleted} files...")

    print(f"[OK] Deleted {deleted} audio files")
    return deleted


def renumber_audio_files(data_dir):
    """
    Renumber audio files to match renumbered segments in transcripts.

    Args:
        data_dir: Data directory

    Returns:
        Number of files renamed
    """
    data_path = Path(data_dir)
    transcripts_dir = data_path / 'transcripts'
    audio_dir = data_path / 'audio_segments'

    print("\n" + "=" * 70)
    print("RENUMBERING AUDIO FILES")
    print("=" * 70)

    transcript_files = sorted(transcripts_dir.glob('*.json'))
    transcript_files = [f for f in transcript_files if not f.stem.endswith('_raw')]

    # Build mapping of old -> new segment numbers per video
    rename_map = {}

    for json_file in transcript_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        video_id = data['video_id']

        # Get all audio files for this video
        video_audio_files = sorted(audio_dir.glob(f"{video_id}_seg*.wav"))

        # Renumber them sequentially
        for new_num, audio_file in enumerate(video_audio_files, 1):
            # Extract old segment number
            old_filename = audio_file.name
            old_num = int(old_filename.split('_seg')[1].replace('.wav', ''))

            if old_num != new_num:
                new_filename = f"{video_id}_seg{new_num:03d}.wav"
                new_path = audio_dir / new_filename

                rename_map[audio_file] = new_path

    # Perform renames
    renamed = 0
    for old_path, new_path in rename_map.items():
        if not new_path.exists():
            old_path.rename(new_path)
            renamed += 1

    if renamed > 0:
        print(f"[OK] Renamed {renamed} audio files")
    else:
        print("[OK] No renaming needed")

    return renamed


def regenerate_outputs(data_dir):
    """
    Regenerate CSV files and analysis reports.

    Args:
        data_dir: Data directory
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
        description="Clean dataset by removing filtered segments"
    )
    parser.add_argument(
        '--filter-file',
        default='segments_to_filter.csv',
        help='CSV file with segments to filter (default: segments_to_filter.csv)'
    )
    parser.add_argument(
        '--data-dir',
        default='data',
        help='Data directory (default: data)'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup before cleaning (recommended)'
    )
    parser.add_argument(
        '--no-renumber',
        action='store_true',
        help='Skip renumbering segments (keep original numbers with gaps)'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("DATASET CLEANING")
    print("=" * 70)
    print(f"Filter file: {args.filter_file}")
    print(f"Data directory: {args.data_dir}")

    # Load segments to filter
    segments_to_remove = load_segments_to_filter(args.filter_file)
    if segments_to_remove is None:
        return 1

    if len(segments_to_remove) == 0:
        print("\n[OK] No segments to remove")
        return 0

    # Warning
    print("\n" + "!" * 70)
    print("WARNING: This will permanently delete filtered segments")
    print("         - Modify transcript files")
    print("         - Delete audio WAV files")
    print("         - Regenerate CSV and analysis files")
    print("!" * 70)

    response = input("\nProceed with cleaning? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cleaning cancelled.")
        return 0

    # Create backup if requested
    if args.backup:
        backup_path = backup_data(args.data_dir)
        print(f"[OK] Backup created: {backup_path}\n")

    # Step 1: Clean transcripts
    stats = clean_transcripts(args.data_dir, segments_to_remove)

    # Step 2: Delete audio files
    deleted = delete_audio_files(args.data_dir, segments_to_remove)
    stats['audio_deleted'] = deleted

    # Step 3: Renumber (optional)
    if not args.no_renumber:
        renamed = renumber_audio_files(args.data_dir)
        stats['audio_renamed'] = renamed

    # Step 4: Regenerate outputs
    duration_stats, vocab_stats = regenerate_outputs(args.data_dir)

    # Summary
    print("\n" + "=" * 70)
    print("CLEANING SUMMARY")
    print("=" * 70)

    print(f"\nTranscript Changes:")
    print(f"  Videos processed: {stats['videos_processed']}")
    print(f"  Videos modified: {stats['videos_modified']}")
    print(f"  Videos removed: {stats['videos_removed']}")
    print(f"  Remaining videos: {stats['videos_processed'] - stats['videos_removed']}")

    print(f"\nSegment Changes:")
    print(f"  Before cleaning: {stats['segments_before']:,}")
    print(f"  After cleaning: {stats['segments_after']:,}")
    print(f"  Removed: {stats['segments_removed']:,}")
    print(f"  Retention rate: {stats['segments_after']/stats['segments_before']*100:.1f}%")

    print(f"\nAudio Files:")
    print(f"  Deleted: {stats['audio_deleted']:,}")
    if not args.no_renumber:
        print(f"  Renamed: {stats.get('audio_renamed', 0):,}")

    print(f"\nFinal Statistics:")
    print(f"  Total videos: {duration_stats['total_videos']}")
    print(f"  Total segments: {duration_stats['total_segments']:,}")
    print(f"  Total duration: {duration_stats['total_duration_minutes']:.1f} minutes")
    print(f"  Total words: {vocab_stats['total_words']:,}")
    print(f"  Unique words: {vocab_stats['unique_words']:,}")

    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("\n1. Validate cleaned dataset:")
    print("   python validate_data.py")
    print("\n2. Review updated files:")
    print(f"   - {args.data_dir}/all_segments.csv")
    print(f"   - {args.data_dir}/all_segments_detailed.csv")

    if args.backup:
        print(f"\n3. If satisfied, delete backup:")
        print(f"   rm -rf {backup_path}")

    print("\n" + "=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
