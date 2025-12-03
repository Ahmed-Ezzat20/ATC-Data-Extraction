"""
Dataset Utilities

Shared functions for loading transcripts, splitting datasets, and handling audio files.
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from tqdm import tqdm


class DatasetStatistics:
    """Track dataset statistics across operations."""
    
    def __init__(self):
        self.total_videos = 0
        self.total_segments = 0
        self.train_videos = 0
        self.train_segments = 0
        self.val_videos = 0
        self.val_segments = 0
        self.test_videos = 0
        self.test_segments = 0
        self.missing_audio = 0
        self.total_audio_size_mb = 0.0
    
    def to_dict(self) -> Dict:
        """Convert statistics to dictionary."""
        return {
            'total_videos': self.total_videos,
            'total_segments': self.total_segments,
            'train_videos': self.train_videos,
            'train_segments': self.train_segments,
            'val_videos': self.val_videos,
            'val_segments': self.val_segments,
            'test_videos': self.test_videos,
            'test_segments': self.test_segments,
            'missing_audio': self.missing_audio,
            'total_audio_size_mb': self.total_audio_size_mb,
        }


def load_transcripts(
    transcripts_dir: str,
    return_grouped: bool = True,
    verbose: bool = True
) -> Dict[str, List[Dict]] | List[Dict]:
    """
    Load all transcript files from a directory.
    
    Args:
        transcripts_dir: Directory containing transcript JSON files
        return_grouped: If True, returns dict grouped by video_id. If False, returns flat list.
        verbose: Whether to print progress information
        
    Returns:
        Dictionary mapping video_id to list of segments (if return_grouped=True)
        OR flat list of all segments with video_id added (if return_grouped=False)
    """
    transcripts_path = Path(transcripts_dir)
    
    if verbose:
        print("\n" + "="*70)
        print("LOADING TRANSCRIPTS")
        print("="*70)
    
    # Find all JSON files, excluding raw files
    transcript_files = sorted(transcripts_path.glob("*.json"))
    transcript_files = [f for f in transcript_files if not f.stem.endswith('_raw')]
    
    if not transcript_files:
        if verbose:
            print("[!] No transcript files found")
        return {} if return_grouped else []
    
    if verbose:
        print(f"Found {len(transcript_files)} transcript files")
    
    if return_grouped:
        # Return grouped by video
        videos_data = {}
        
        iterator = tqdm(transcript_files, desc="Loading transcripts") if verbose else transcript_files
        
        for transcript_file in iterator:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            video_id = data['video_id']
            videos_data[video_id] = data['segments']
        
        total_segments = sum(len(segments) for segments in videos_data.values())
        
        if verbose:
            print(f"Loaded {len(videos_data)} videos with {total_segments:,} total segments")
        
        return videos_data
    
    else:
        # Return flat list with video_id added to each segment
        all_segments = []
        
        iterator = tqdm(transcript_files, desc="Loading transcripts") if verbose else transcript_files
        
        for transcript_file in iterator:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            video_id = data['video_id']
            
            for segment in data['segments']:
                segment_data = {
                    'audio_filename': f"{video_id}_seg{segment['segment_num']:03d}.wav",
                    'video_id': video_id,
                    'segment_num': segment['segment_num'],
                    'transcription': segment['transcript'],
                    'original_transcription': segment.get('original_transcript', segment['transcript']),
                    'start_time': segment['start_time'],
                    'duration': segment['duration'],
                    'timestamp_range': segment['timestamp_range'],
                }
                all_segments.append(segment_data)
        
        if verbose:
            print(f"Loaded {len(all_segments):,} segments from {len(transcript_files)} videos")
        
        return all_segments


def split_videos(
    videos_data: Dict[str, List[Dict]],
    train_ratio: float = 0.95,
    val_ratio: float = 0.025,
    test_ratio: float = 0.025,
    random_seed: int = 42,
    verbose: bool = True
) -> Tuple[List[str], List[str], List[str]]:
    """
    Split videos into train/validation/test sets.
    
    Args:
        videos_data: Dictionary mapping video_id to list of segments
        train_ratio: Ratio for training set (default: 0.95)
        val_ratio: Ratio for validation set (default: 0.025)
        test_ratio: Ratio for test set (default: 0.025)
        random_seed: Random seed for reproducibility
        verbose: Whether to print split information
        
    Returns:
        Tuple of (train_video_ids, val_video_ids, test_video_ids)
    """
    # Validate split ratios
    total_ratio = train_ratio + val_ratio + test_ratio
    if not (0.99 < total_ratio < 1.01):  # Allow small floating point errors
        raise ValueError(f"Split ratios must sum to 1.0, got {total_ratio}")
    
    if verbose:
        print("\n" + "="*70)
        print("SPLITTING DATASET")
        print("="*70)
    
    # Set random seed for reproducibility
    random.seed(random_seed)
    
    # Shuffle video IDs
    video_ids = list(videos_data.keys())
    random.shuffle(video_ids)
    
    # Calculate split sizes
    n_videos = len(video_ids)
    n_train = int(n_videos * train_ratio)
    n_val = int(n_videos * val_ratio)
    
    # Split videos
    train_videos = video_ids[:n_train]
    val_videos = video_ids[n_train:n_train + n_val]
    test_videos = video_ids[n_train + n_val:]
    
    if verbose:
        # Calculate segment counts
        train_segments = sum(len(videos_data[vid]) for vid in train_videos)
        val_segments = sum(len(videos_data[vid]) for vid in val_videos)
        test_segments = sum(len(videos_data[vid]) for vid in test_videos)
        
        print(f"\nSplit configuration:")
        print(f"  Random seed: {random_seed}")
        print(f"  Train ratio: {train_ratio:.1%}")
        print(f"  Validation ratio: {val_ratio:.1%}")
        print(f"  Test ratio: {test_ratio:.1%}")
        
        print(f"\nSplit results:")
        print(f"  Train: {len(train_videos)} videos, {train_segments:,} segments")
        print(f"  Validation: {len(val_videos)} videos, {val_segments:,} segments")
        print(f"  Test: {len(test_videos)} videos, {test_segments:,} segments")
    
    return train_videos, val_videos, test_videos


def load_audio_file(audio_path: str | Path) -> Optional[bytes]:
    """
    Load audio file as binary data.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Audio file bytes or None if not found
    """
    audio_file = Path(audio_path)
    
    if not audio_file.exists():
        return None
    
    with open(audio_file, 'rb') as f:
        return f.read()
