#!/usr/bin/env python3
"""
Example: Loading and Using ATC Parquet Dataset

Demonstrates how to load and use the exported Parquet dataset.
"""

import pandas as pd
import pyarrow.parquet as pq
from io import BytesIO
import wave


def load_dataset(parquet_file: str):
    """
    Load the Parquet dataset.

    Args:
        parquet_file: Path to Parquet file

    Returns:
        pandas DataFrame
    """
    print(f"Loading dataset from: {parquet_file}")
    df = pd.read_parquet(parquet_file)
    print(f"Loaded {len(df):,} records")
    return df


def explore_dataset(df: pd.DataFrame):
    """
    Explore the dataset structure.

    Args:
        df: Dataset DataFrame
    """
    print("\n" + "="*70)
    print("DATASET OVERVIEW")
    print("="*70)

    print(f"\nTotal records: {len(df):,}")
    print(f"Columns: {list(df.columns)}")

    print("\nColumn types:")
    print(df.dtypes)

    print("\nFirst few records:")
    print(df[['audio_filename', 'video_id', 'transcription']].head())

    print("\nDataset info:")
    print(df.info())

    # Video statistics
    print("\nVideos in dataset:")
    video_counts = df['video_id'].value_counts()
    print(f"  Total videos: {len(video_counts)}")
    print(f"  Segments per video (avg): {len(df) / len(video_counts):.1f}")

    print("\nTop 5 videos by segment count:")
    print(video_counts.head())


def extract_audio_sample(df: pd.DataFrame, index: int = 0, output_file: str = "sample.wav"):
    """
    Extract a single audio sample from the dataset.

    Args:
        df: Dataset DataFrame
        index: Row index to extract
        output_file: Output WAV file path
    """
    print("\n" + "="*70)
    print("EXTRACTING AUDIO SAMPLE")
    print("="*70)

    if 'audio' not in df.columns:
        print("[!] No audio data in dataset (metadata-only export)")
        return

    row = df.iloc[index]

    print(f"\nExtracting record {index}:")
    print(f"  Filename: {row['audio_filename']}")
    print(f"  Video ID: {row['video_id']}")
    print(f"  Transcription: {row['transcription']}")

    if row['audio'] is None:
        print("[!] No audio data for this record")
        return

    # Write audio to file
    with open(output_file, 'wb') as f:
        f.write(row['audio'])

    print(f"\n[OK] Audio extracted to: {output_file}")

    # Get audio info
    with wave.open(output_file, 'rb') as wav:
        print(f"\nAudio properties:")
        print(f"  Channels: {wav.getnchannels()}")
        print(f"  Sample width: {wav.getsampwidth()} bytes")
        print(f"  Sample rate: {wav.getframerate()} Hz")
        print(f"  Frames: {wav.getnframes()}")
        print(f"  Duration: {wav.getnframes() / wav.getframerate():.2f} seconds")


def search_transcriptions(df: pd.DataFrame, query: str):
    """
    Search transcriptions for a query string.

    Args:
        df: Dataset DataFrame
        query: Search query
    """
    print("\n" + "="*70)
    print(f"SEARCHING FOR: '{query}'")
    print("="*70)

    # Case-insensitive search
    mask = df['transcription'].str.contains(query, case=False, na=False)
    results = df[mask]

    print(f"\nFound {len(results)} matches")

    if len(results) > 0:
        print("\nFirst 5 matches:")
        for i, row in results.head().iterrows():
            print(f"\n{i+1}. {row['audio_filename']}")
            print(f"   Transcription: {row['transcription']}")
            print(f"   Original: {row['original_transcription']}")


def filter_by_video(df: pd.DataFrame, video_id: str):
    """
    Filter dataset by video ID.

    Args:
        df: Dataset DataFrame
        video_id: Video ID to filter

    Returns:
        Filtered DataFrame
    """
    print("\n" + "="*70)
    print(f"FILTERING BY VIDEO ID: {video_id}")
    print("="*70)

    filtered = df[df['video_id'] == video_id]

    print(f"\nFound {len(filtered)} segments for video {video_id}")

    if len(filtered) > 0:
        print("\nSegments:")
        for _, row in filtered.iterrows():
            print(f"  {row['segment_num']:3d}. [{row['timestamp_range']}] {row['transcription'][:60]}...")

    return filtered


def analyze_transcriptions(df: pd.DataFrame):
    """
    Analyze transcription statistics.

    Args:
        df: Dataset DataFrame
    """
    print("\n" + "="*70)
    print("TRANSCRIPTION ANALYSIS")
    print("="*70)

    # Word count statistics
    df['word_count'] = df['transcription'].str.split().str.len()

    print(f"\nWord count statistics:")
    print(f"  Mean: {df['word_count'].mean():.1f} words")
    print(f"  Median: {df['word_count'].median():.1f} words")
    print(f"  Min: {df['word_count'].min()} words")
    print(f"  Max: {df['word_count'].max()} words")

    # Duration statistics
    print(f"\nDuration statistics:")
    print(f"  Mean: {df['duration'].mean():.2f} seconds")
    print(f"  Median: {df['duration'].median():.2f} seconds")
    print(f"  Min: {df['duration'].min():.2f} seconds")
    print(f"  Max: {df['duration'].max():.2f} seconds")
    print(f"  Total: {df['duration'].sum()/60:.1f} minutes")

    # Common words
    print(f"\nMost common words:")
    all_words = ' '.join(df['transcription']).split()
    from collections import Counter
    word_freq = Counter(all_words)
    for word, count in word_freq.most_common(10):
        print(f"  {word}: {count:,}")


def main():
    """Run example demonstrations."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python load_parquet_example.py <parquet_file>")
        print("\nExample:")
        print("  python load_parquet_example.py atc_dataset.parquet")
        return 1

    parquet_file = sys.argv[1]

    # Load dataset
    df = load_dataset(parquet_file)

    # Explore dataset
    explore_dataset(df)

    # Analyze transcriptions
    analyze_transcriptions(df)

    # Search example
    search_transcriptions(df, "TOWER")

    # Extract audio sample (if available)
    if len(df) > 0:
        extract_audio_sample(df, index=0, output_file="sample_audio.wav")

    # Filter by video (example with first video)
    if len(df) > 0:
        first_video = df.iloc[0]['video_id']
        filter_by_video(df, first_video)

    print("\n" + "="*70)
    print("EXAMPLE COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
