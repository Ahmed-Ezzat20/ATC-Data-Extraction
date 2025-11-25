#!/usr/bin/env python3
"""
Enhanced Example - Using All New Features

This example demonstrates how to use the enhanced features:
- Logging
- Configuration
- Validation
- Retry logic
- Checkpoints
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils import (
    setup_logger,
    Config,
    validate_youtube_url,
    validate_playlist_url,
    Checkpoint,
    ExtractionProgress,
    ValidationError
)
from extraction import GeminiExtractor, get_playlist_videos
from segmentation import AudioSegmenter
from analysis import Analyzer, Visualizer


def main():
    # ========================================================================
    # 1. SETUP LOGGING
    # ========================================================================
    logger = setup_logger(
        name="atc_extraction",
        log_file="logs/extraction.log",
        console=True
    )
    logger.info("="*70)
    logger.info("ENHANCED ATC DATA EXTRACTION DEMO")
    logger.info("="*70)

    # ========================================================================
    # 2. LOAD CONFIGURATION
    # ========================================================================
    try:
        # Try to load from config.yaml
        config = Config.from_yaml("config.yaml")
        logger.info("Loaded configuration from config.yaml")
    except FileNotFoundError:
        # Fall back to defaults
        config = Config.from_defaults()
        logger.warning("config.yaml not found, using defaults")

    # Display configuration
    logger.info(f"API Model: {config.gemini.model}")
    logger.info(f"Request Delay: {config.gemini.request_delay}s")
    logger.info(f"Max Retries: {config.gemini.max_retries}")
    logger.info(f"Transcripts Dir: {config.paths.transcripts}")

    # ========================================================================
    # 3. INPUT VALIDATION
    # ========================================================================
    # Sample videos (replace with your own)
    sample_playlist = "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID"
    sample_videos = [
        "https://www.youtube.com/watch?v=94VPOXc2bEM",  # Emirates 521
    ]

    # Validate inputs
    logger.info("\nValidating inputs...")
    try:
        if validate_playlist_url(sample_playlist):
            logger.info(f"✓ Valid playlist URL: {sample_playlist}")
    except ValidationError as e:
        logger.warning(f"✗ Invalid playlist URL: {e}")

    for video_url in sample_videos:
        if validate_youtube_url(video_url):
            logger.info(f"✓ Valid video URL: {video_url}")
        else:
            logger.error(f"✗ Invalid video URL: {video_url}")
            return

    # ========================================================================
    # 4. CHECKPOINT SETUP (Progress Tracking)
    # ========================================================================
    logger.info("\nSetting up progress tracking...")
    checkpoint = Checkpoint(checkpoint_dir=config.paths.checkpoints)
    session_name = "demo_extraction"
    progress = ExtractionProgress(checkpoint, session_name)

    # Check if we're resuming
    stats = progress.get_stats()
    if stats['processed'] > 0:
        logger.info(f"Resuming session: {stats['processed']} videos already processed")
    else:
        logger.info("Starting new extraction session")

    # ========================================================================
    # 5. EXTRACTION WITH RETRY & VALIDATION
    # ========================================================================
    logger.info("\n[PHASE 1] Extracting subtitles with automatic retry...")

    try:
        # Initialize extractor with configuration
        extractor = GeminiExtractor(
            api_key=config.gemini.api_key,
            model=config.gemini.model,
            max_retries=config.gemini.max_retries
        )

        # Set total for progress tracking
        progress.set_total(len(sample_videos))

        # Extract videos
        results = []
        for video_url in sample_videos:
            video_id = extractor.extract_video_id(video_url)

            # Check if already processed
            if progress.is_processed(video_id):
                logger.info(f"Video {video_id} already processed, skipping")
                continue

            try:
                # Extract with automatic retry on failure
                result = extractor.extract_subtitles(
                    video_url,
                    output_dir=config.paths.transcripts
                )
                results.append(result)

                # Mark as processed
                progress.mark_processed(video_id)
                logger.info(f"✓ Extracted {result['total_segments']} segments")

            except Exception as e:
                logger.error(f"✗ Failed to extract {video_id}: {e}")
                progress.mark_failed(video_id)
                continue

        logger.info(f"\nExtraction complete: {len(results)} videos processed")

        # Show progress statistics
        stats = progress.get_stats()
        logger.info(f"Total: {stats['total']}")
        logger.info(f"Processed: {stats['processed']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info(f"Success Rate: {stats['success_rate']*100:.1f}%")

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return

    # ========================================================================
    # 6. AUDIO PROCESSING
    # ========================================================================
    logger.info("\n[PHASE 2] Processing audio...")

    try:
        segmenter = AudioSegmenter(
            transcripts_dir=config.paths.transcripts,
            raw_audio_dir=config.paths.raw_audio,
            segments_dir=config.paths.segments
        )

        seg_results = segmenter.process_all(download=True)

        total_segments = sum(r['segments_created'] for r in seg_results)
        logger.info(f"✓ Created {total_segments} audio segments")

    except Exception as e:
        logger.error(f"Audio processing failed: {e}")

    # ========================================================================
    # 7. ANALYSIS
    # ========================================================================
    logger.info("\n[PHASE 3] Analyzing data...")

    try:
        analyzer = Analyzer(transcripts_dir=config.paths.transcripts)

        # Duration analysis
        duration_stats = analyzer.analyze_duration()
        logger.info(f"\nDuration Statistics:")
        logger.info(f"  Total videos: {duration_stats['total_videos']}")
        logger.info(f"  Total segments: {duration_stats['total_segments']:,}")
        logger.info(f"  Total duration: {duration_stats['total_duration_minutes']:.1f} minutes")

        # Vocabulary analysis
        vocab_stats = analyzer.analyze_vocabulary()
        logger.info(f"\nVocabulary Statistics:")
        logger.info(f"  Total words: {vocab_stats['total_words']:,}")
        logger.info(f"  Unique words: {vocab_stats['unique_words']:,}")
        logger.info(f"  Vocabulary richness: {vocab_stats['vocabulary_richness']*100:.2f}%")

        # Generate reports
        logger.info("\nGenerating reports...")
        analyzer.generate_report(output_file="data/analysis_report.txt")
        analyzer.generate_csv(output_file="data/all_segments.csv", detailed=False)
        analyzer.generate_csv(output_file="data/all_segments_detailed.csv", detailed=True)

        # Create visualizations
        logger.info("\nCreating visualizations...")
        visualizer = Visualizer(output_dir=config.paths.visualizations)
        visualizer.create_all_visualizations()

    except Exception as e:
        logger.error(f"Analysis failed: {e}")

    # ========================================================================
    # 8. CLEANUP
    # ========================================================================
    logger.info("\n" + "="*70)
    logger.info("PROCESSING COMPLETE")
    logger.info("="*70)
    logger.info("\nOutput files:")
    logger.info(f"  - {config.paths.transcripts}/*.json")
    logger.info(f"  - {config.paths.segments}/*.wav")
    logger.info(f"  - data/all_segments.csv")
    logger.info(f"  - data/analysis_report.txt")
    logger.info(f"  - {config.paths.visualizations}/*.png")
    logger.info(f"  - logs/extraction.log")

    # Optional: Clear checkpoint after successful completion
    # progress.clear()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Progress has been saved.")
        print("Run again to resume from checkpoint.")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        raise
