#!/usr/bin/env python3
"""
Main Pipeline Script

Complete end-to-end pipeline for ATC data extraction and analysis.

Usage:
    python main.py --playlist-url "PLAYLIST_URL" [options]
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from extraction.extract_playlist import get_playlist_videos
from extraction.gemini_extractor import GeminiExtractor
from segmentation.audio_segmenter import AudioSegmenter
from analysis.analyzer import Analyzer
from analysis.visualizer import Visualizer


def main():
    parser = argparse.ArgumentParser(
        description="Complete ATC data extraction and analysis pipeline"
    )
    parser.add_argument(
        '--playlist-url',
        help='YouTube playlist URL (optional if --video-urls provided)'
    )
    parser.add_argument(
        '--video-urls',
        nargs='+',
        help='List of YouTube video URLs'
    )
    parser.add_argument(
        '--skip-extraction',
        action='store_true',
        help='Skip subtitle extraction (use existing transcripts)'
    )
    parser.add_argument(
        '--skip-download',
        action='store_true',
        help='Skip audio download (use existing audio files)'
    )
    parser.add_argument(
        '--skip-segmentation',
        action='store_true',
        help='Skip audio segmentation'
    )
    parser.add_argument(
        '--skip-analysis',
        action='store_true',
        help='Skip analysis and visualization'
    )
    parser.add_argument(
        '--output-dir',
        default='data',
        help='Base output directory (default: data)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay between API requests in seconds (default: 2.0)'
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.skip_extraction and not args.playlist_url and not args.video_urls:
        parser.error("Either --playlist-url or --video-urls must be provided")
    
    start_time = datetime.now()
    
    print("="*70)
    print("ATC DATA EXTRACTION PIPELINE")
    print("="*70)
    print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Phase 1: Extract subtitles
    if not args.skip_extraction:
        print("\n[PHASE 1] EXTRACTING SUBTITLES")
        print("-"*70)
        
        if args.playlist_url:
            video_urls = get_playlist_videos(args.playlist_url)
        else:
            video_urls = args.video_urls
        
        extractor = GeminiExtractor()
        transcripts_dir = Path(args.output_dir) / 'transcripts'
        
        results = extractor.extract_batch(
            video_urls,
            delay=args.delay,
            output_dir=str(transcripts_dir)
        )
        
        print(f"\n✓ Extracted subtitles from {len(results)} videos")
    else:
        print("\n[PHASE 1] SKIPPED - Using existing transcripts")
    
    # Phase 2: Download and segment audio
    if not args.skip_segmentation:
        print("\n[PHASE 2] DOWNLOADING AND SEGMENTING AUDIO")
        print("-"*70)
        
        segmenter = AudioSegmenter(
            transcripts_dir=str(Path(args.output_dir) / 'transcripts'),
            raw_audio_dir=str(Path(args.output_dir) / 'raw_audio'),
            segments_dir=str(Path(args.output_dir) / 'audio_segments')
        )
        
        download = not args.skip_download
        results = segmenter.process_all(download=download)
        
        total_segments = sum(r['segments_created'] for r in results)
        print(f"\n✓ Created {total_segments:,} audio segments from {len(results)} videos")
    else:
        print("\n[PHASE 2] SKIPPED - Audio segmentation disabled")
    
    # Phase 3: Analysis and visualization
    if not args.skip_analysis:
        print("\n[PHASE 3] ANALYSIS AND VISUALIZATION")
        print("-"*70)
        
        analyzer = Analyzer(
            transcripts_dir=str(Path(args.output_dir) / 'transcripts')
        )
        
        # Duration analysis
        duration_stats = analyzer.analyze_duration()
        print(f"\nDuration Statistics:")
        print(f"  Total videos: {duration_stats['total_videos']}")
        print(f"  Total segments: {duration_stats['total_segments']:,}")
        print(f"  Total duration: {duration_stats['total_duration_minutes']:.1f} minutes")
        
        # Vocabulary analysis
        vocab_stats = analyzer.analyze_vocabulary()
        print(f"\nVocabulary Statistics:")
        print(f"  Total words: {vocab_stats['total_words']:,}")
        print(f"  Unique words: {vocab_stats['unique_words']:,}")
        print(f"  Vocabulary richness: {vocab_stats['vocabulary_richness']*100:.2f}%")
        
        # Generate reports
        print(f"\nGenerating reports...")
        analyzer.generate_report(
            output_file=str(Path(args.output_dir) / 'analysis_report.txt')
        )
        analyzer.generate_csv(
            output_file=str(Path(args.output_dir) / 'all_segments.csv'),
            detailed=False
        )
        analyzer.generate_csv(
            output_file=str(Path(args.output_dir) / 'all_segments_detailed.csv'),
            detailed=True
        )
        
        # Create visualizations
        print(f"\nCreating visualizations...")
        visualizer = Visualizer(
            output_dir=str(Path(args.output_dir) / 'visualizations')
        )
        visualizer.create_all_visualizations()
        
        print(f"\n✓ Analysis complete")
    else:
        print("\n[PHASE 3] SKIPPED - Analysis disabled")
    
    # Summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("\n" + "="*70)
    print("PIPELINE COMPLETE")
    print("="*70)
    print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total duration: {duration}")
    print(f"Output directory: {args.output_dir}")
    print("="*70)


if __name__ == "__main__":
    main()
