#!/usr/bin/env python3
"""
Add Audio Quality Metrics to Dataset

This script adds quality metrics (SNR, language, speech ratio) to existing
audio segments and optionally filters out low-quality segments.

Usage:
    python add_quality_metrics.py --data-dir data/preprocessed --audio-dir data/audio_segments [options]
"""

import argparse
import json
import sys
import yaml
from pathlib import Path
from typing import Dict, List
import numpy as np
import librosa
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.analysis.audio_quality import calculate_all_metrics, passes_quality_filters


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def process_segment(segment_data: dict, audio_dir: Path, config: dict) -> tuple:
    """
    Process a single segment and add quality metrics.
    
    Args:
        segment_data: Segment dictionary from JSON
        audio_dir: Directory containing audio files
        config: Configuration dictionary
        
    Returns:
        Tuple of (updated_segment, passes_filter)
    """
    # Load audio file
    audio_file = audio_dir / segment_data["audio_file"]
    
    if not audio_file.exists():
        print(f"Warning: Audio file not found: {audio_file}")
        return segment_data, False
    
    try:
        # Load audio
        audio, sr = librosa.load(audio_file, sr=16000, mono=True)
        
        # Get text (use normalized if available, otherwise original)
        text = segment_data.get("normalized_text", segment_data.get("text", ""))
        
        # Calculate quality metrics
        metrics = calculate_all_metrics(audio, text, sr)
        
        # Add metrics to segment data
        segment_data["quality"] = metrics
        
        # Check if passes filters
        quality_config = config.get("quality_filtering", {})
        if quality_config.get("enabled", True):
            passes = passes_quality_filters(
                metrics,
                min_snr_db=quality_config.get("min_snr_db", 15.0),
                required_language=quality_config.get("required_language", "en"),
                min_language_confidence=quality_config.get("min_language_confidence", 0.8),
                min_speech_ratio=quality_config.get("min_speech_ratio", 0.6)
            )
        else:
            passes = True
        
        return segment_data, passes
        
    except Exception as e:
        print(f"Error processing {audio_file}: {e}")
        return segment_data, False


def main():
    parser = argparse.ArgumentParser(description="Add quality metrics to audio segments")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/preprocessed",
        help="Directory containing preprocessed JSON files"
    )
    parser.add_argument(
        "--audio-dir",
        type=str,
        default="data/audio_segments",
        help="Directory containing audio segment files"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (defaults to data-dir)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--filter",
        action="store_true",
        help="Remove segments that don't pass quality filters"
    )
    parser.add_argument(
        "--stats-file",
        type=str,
        default="quality_stats.json",
        help="Output file for quality statistics"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Setup directories
    data_dir = Path(args.data_dir)
    audio_dir = Path(args.audio_dir)
    output_dir = Path(args.output_dir) if args.output_dir else data_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all JSON files
    json_files = list(data_dir.glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {data_dir}")
        return
    
    print(f"Found {len(json_files)} JSON files")
    print(f"Audio directory: {audio_dir}")
    print(f"Output directory: {output_dir}")
    
    # Statistics
    stats = {
        "total_segments": 0,
        "segments_with_metrics": 0,
        "segments_passed": 0,
        "segments_filtered": 0,
        "avg_snr": 0.0,
        "avg_speech_ratio": 0.0,
        "language_distribution": {},
    }
    
    snr_values = []
    speech_ratios = []
    
    # Process each file
    for json_file in tqdm(json_files, desc="Processing files"):
        # Load JSON
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Process segments
        updated_segments = []
        
        for segment in tqdm(data.get("segments", []), desc=f"  {json_file.name}", leave=False):
            stats["total_segments"] += 1
            
            # Process segment
            updated_segment, passes = process_segment(segment, audio_dir, config)
            
            # Update statistics
            if "quality" in updated_segment:
                stats["segments_with_metrics"] += 1
                snr_values.append(updated_segment["quality"]["snr_db"])
                speech_ratios.append(updated_segment["quality"]["speech_ratio"])
                
                # Track language distribution
                lang = updated_segment["quality"]["language"]
                stats["language_distribution"][lang] = stats["language_distribution"].get(lang, 0) + 1
                
                if passes:
                    stats["segments_passed"] += 1
                    updated_segments.append(updated_segment)
                else:
                    stats["segments_filtered"] += 1
                    if not args.filter:
                        # Keep segment even if it doesn't pass (just add metrics)
                        updated_segments.append(updated_segment)
            else:
                # Keep segment if metrics couldn't be calculated
                updated_segments.append(updated_segment)
        
        # Update data with processed segments
        data["segments"] = updated_segments
        
        # Save to output directory
        output_file = output_dir / json_file.name
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    # Calculate averages
    if snr_values:
        stats["avg_snr"] = round(float(np.mean(snr_values)), 2)
        stats["avg_speech_ratio"] = round(float(np.mean(speech_ratios)), 3)
    
    # Save statistics
    with open(args.stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("Quality Metrics Summary")
    print("="*60)
    print(f"Total segments: {stats['total_segments']}")
    print(f"Segments with metrics: {stats['segments_with_metrics']}")
    print(f"Segments passed filters: {stats['segments_passed']}")
    print(f"Segments filtered out: {stats['segments_filtered']}")
    print(f"Average SNR: {stats['avg_snr']} dB")
    print(f"Average speech ratio: {stats['avg_speech_ratio']}")
    print(f"\nLanguage distribution:")
    for lang, count in sorted(stats["language_distribution"].items(), key=lambda x: x[1], reverse=True):
        print(f"  {lang}: {count} ({100*count/stats['segments_with_metrics']:.1f}%)")
    print(f"\nStatistics saved to: {args.stats_file}")
    print("="*60)


if __name__ == "__main__":
    main()
