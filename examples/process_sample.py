#!/usr/bin/env python3
"""
Sample Processing Script

Demonstrates how to process a small sample of ATC videos.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from extraction.gemini_extractor import GeminiExtractor
from segmentation.audio_segmenter import AudioSegmenter
from analysis.analyzer import Analyzer
from analysis.visualizer import Visualizer


def main():
    # Sample video URLs (replace with your own)
    sample_videos = [
        "https://www.youtube.com/watch?v=94VPOXc2bEM",  # Emirates 521
        "https://www.youtube.com/watch?v=P6jjY-AW4LE",
    ]
    
    print("="*70)
    print("SAMPLE ATC DATA EXTRACTION")
    print("="*70)
    
    # Phase 1: Extract subtitles
    print("\n[Phase 1] Extracting subtitles...")
    extractor = GeminiExtractor()
    results = extractor.extract_batch(sample_videos, delay=2.0)
    
    total_segments = sum(r['total_segments'] for r in results)
    print(f"✓ Extracted {total_segments} segments from {len(results)} videos")
    
    # Phase 2: Download and segment audio
    print("\n[Phase 2] Processing audio...")
    segmenter = AudioSegmenter()
    seg_results = segmenter.process_all(download=True)
    
    total_audio_segments = sum(r['segments_created'] for r in seg_results)
    print(f"✓ Created {total_audio_segments} audio segments")
    
    # Phase 3: Analysis
    print("\n[Phase 3] Analyzing data...")
    analyzer = Analyzer()
    
    duration_stats = analyzer.analyze_duration()
    vocab_stats = analyzer.analyze_vocabulary()
    
    print(f"\nResults:")
    print(f"  Total duration: {duration_stats['total_duration_minutes']:.1f} minutes")
    print(f"  Total words: {vocab_stats['total_words']:,}")
    print(f"  Unique words: {vocab_stats['unique_words']:,}")
    print(f"  Top 5 words:")
    for word, count in vocab_stats['top_words'][:5]:
        print(f"    - {word}: {count}")
    
    # Generate reports
    analyzer.generate_report()
    analyzer.generate_csv()
    
    # Create visualizations
    print("\n[Phase 4] Creating visualizations...")
    visualizer = Visualizer()
    visualizer.create_all_visualizations()
    
    print("\n" + "="*70)
    print("✓ Sample processing complete!")
    print("="*70)
    print("\nOutput files:")
    print("  - data/transcripts/*.json")
    print("  - data/audio_segments/*.wav")
    print("  - data/all_segments.csv")
    print("  - data/analysis_report.txt")
    print("  - data/visualizations/*.png")


if __name__ == "__main__":
    main()
