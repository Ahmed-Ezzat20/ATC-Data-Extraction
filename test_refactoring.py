#!/usr/bin/env python3
"""
Test Script for Refactored Dataset Module

Tests the new src/dataset module to ensure all functions work correctly.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dataset import (
    load_transcripts,
    split_videos,
    load_audio_file,
    DatasetStatistics,
    check_authentication,
    generate_dataset_card,
)


def test_dataset_statistics():
    """Test DatasetStatistics class."""
    print("\n" + "="*70)
    print("TEST 1: DatasetStatistics")
    print("="*70)
    
    stats = DatasetStatistics()
    stats.total_videos = 10
    stats.total_segments = 100
    stats.train_segments = 95
    
    stats_dict = stats.to_dict()
    
    assert stats_dict['total_videos'] == 10
    assert stats_dict['total_segments'] == 100
    assert stats_dict['train_segments'] == 95
    
    print("[OK] DatasetStatistics class works correctly")


def test_load_transcripts():
    """Test load_transcripts function."""
    print("\n" + "="*70)
    print("TEST 2: load_transcripts")
    print("="*70)
    
    # Test with sample data if available
    sample_dir = Path("data/preprocessed/transcripts")
    
    if not sample_dir.exists():
        sample_dir = Path("data/preprocessed")
    
    if not sample_dir.exists():
        print("[SKIP] No sample data found at data/preprocessed")
        return
    
    # Test grouped return
    print("\nTesting grouped return (return_grouped=True)...")
    videos_data = load_transcripts(str(sample_dir), return_grouped=True, verbose=False)
    
    if videos_data:
        print(f"[OK] Loaded {len(videos_data)} videos (grouped)")
        
        # Test flat return
        print("\nTesting flat return (return_grouped=False)...")
        segments = load_transcripts(str(sample_dir), return_grouped=False, verbose=False)
        print(f"[OK] Loaded {len(segments)} segments (flat)")
        
        # Verify counts match
        grouped_count = sum(len(segs) for segs in videos_data.values())
        assert grouped_count == len(segments), "Segment counts don't match!"
        print(f"[OK] Segment counts match: {grouped_count}")
    else:
        print("[SKIP] No transcript files found")


def test_split_videos():
    """Test split_videos function."""
    print("\n" + "="*70)
    print("TEST 3: split_videos")
    print("="*70)
    
    # Create sample data
    sample_videos = {
        'video1': [{'segment_num': 1}, {'segment_num': 2}],
        'video2': [{'segment_num': 1}],
        'video3': [{'segment_num': 1}, {'segment_num': 2}, {'segment_num': 3}],
        'video4': [{'segment_num': 1}],
        'video5': [{'segment_num': 1}, {'segment_num': 2}],
    }
    
    train, val, test = split_videos(
        sample_videos,
        train_ratio=0.6,
        val_ratio=0.2,
        test_ratio=0.2,
        random_seed=42,
        verbose=False
    )
    
    # Verify all videos are assigned
    total_videos = len(train) + len(val) + len(test)
    assert total_videos == 5, f"Expected 5 videos, got {total_videos}"
    
    # Verify no overlap
    all_videos = set(train) | set(val) | set(test)
    assert len(all_videos) == 5, "Videos overlap between splits!"
    
    print(f"[OK] Split 5 videos into train={len(train)}, val={len(val)}, test={len(test)}")
    
    # Test reproducibility
    train2, val2, test2 = split_videos(
        sample_videos,
        train_ratio=0.6,
        val_ratio=0.2,
        test_ratio=0.2,
        random_seed=42,
        verbose=False
    )
    
    assert train == train2, "Split is not reproducible!"
    assert val == val2, "Split is not reproducible!"
    assert test == test2, "Split is not reproducible!"
    
    print("[OK] Split is reproducible with same random seed")


def test_load_audio_file():
    """Test load_audio_file function."""
    print("\n" + "="*70)
    print("TEST 4: load_audio_file")
    print("="*70)
    
    # Test with non-existent file
    audio_bytes = load_audio_file("/nonexistent/file.wav")
    assert audio_bytes is None, "Should return None for non-existent file"
    print("[OK] Returns None for non-existent file")
    
    # Test with existing file if available
    sample_audio_dir = Path("data/audio_segments")
    if sample_audio_dir.exists():
        audio_files = list(sample_audio_dir.glob("*.wav"))
        if audio_files:
            audio_bytes = load_audio_file(audio_files[0])
            assert audio_bytes is not None, "Should return bytes for existing file"
            assert isinstance(audio_bytes, bytes), "Should return bytes type"
            print(f"[OK] Loaded audio file: {len(audio_bytes)} bytes")
        else:
            print("[SKIP] No audio files found")
    else:
        print("[SKIP] No audio directory found")


def test_check_authentication():
    """Test check_authentication function."""
    print("\n" + "="*70)
    print("TEST 5: check_authentication")
    print("="*70)
    
    is_authenticated = check_authentication()
    
    if is_authenticated:
        print("[OK] Authenticated with Hugging Face")
    else:
        print("[INFO] Not authenticated with Hugging Face (this is OK for testing)")


def test_generate_dataset_card():
    """Test generate_dataset_card function."""
    print("\n" + "="*70)
    print("TEST 6: generate_dataset_card")
    print("="*70)
    
    # Create sample statistics
    sample_stats = {
        'total_videos': 10,
        'total_segments': 100,
        'train_videos': 8,
        'train_segments': 80,
        'val_videos': 1,
        'val_segments': 10,
        'test_videos': 1,
        'test_segments': 10,
    }
    
    # Generate dataset card
    output_file = "/tmp/test_dataset_card.md"
    result = generate_dataset_card(
        stats=sample_stats,
        output_file=output_file,
        has_audio=True,
        format_type="parquet",
        splits=['train', 'validation', 'test']
    )
    
    # Verify file was created
    assert Path(output_file).exists(), "Dataset card file not created"
    
    # Read and verify content
    with open(output_file, 'r') as f:
        content = f.read()
    
    assert "ATC Communications Dataset" in content
    assert "Total Audio Segments" in content
    assert "train" in content.lower()
    assert "validation" in content.lower()
    
    print(f"[OK] Generated dataset card: {len(content)} characters")
    
    # Clean up
    Path(output_file).unlink()


def main():
    """Run all tests."""
    print("="*70)
    print("TESTING REFACTORED DATASET MODULE")
    print("="*70)
    
    tests = [
        ("DatasetStatistics", test_dataset_statistics),
        ("load_transcripts", test_load_transcripts),
        ("split_videos", test_split_videos),
        ("load_audio_file", test_load_audio_file),
        ("check_authentication", test_check_authentication),
        ("generate_dataset_card", test_generate_dataset_card),
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test_name}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test_name}: {e}")
            failed += 1
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("="*70)
    
    if failed == 0:
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
