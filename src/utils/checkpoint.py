"""
Checkpoint Management Module

Handles saving and loading progress checkpoints for resuming interrupted operations.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
import logging

logger = logging.getLogger("atc_extraction")


class Checkpoint:
    """Manages checkpoint files for tracking processing progress."""

    def __init__(self, checkpoint_dir: str = "data/checkpoints"):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory to store checkpoint files
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, data: Dict) -> bool:
        """
        Save checkpoint data to file.

        Args:
            name: Checkpoint name (used as filename)
            data: Checkpoint data to save

        Returns:
            True if successful, False otherwise
        """
        try:
            checkpoint_file = self.checkpoint_dir / f"{name}.json"

            checkpoint_data = {
                'name': name,
                'timestamp': datetime.now().isoformat(),
                'data': data
            }

            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Checkpoint saved: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to save checkpoint {name}: {str(e)}")
            return False

    def load(self, name: str) -> Optional[Dict]:
        """
        Load checkpoint data from file.

        Args:
            name: Checkpoint name

        Returns:
            Checkpoint data if exists, None otherwise
        """
        try:
            checkpoint_file = self.checkpoint_dir / f"{name}.json"

            if not checkpoint_file.exists():
                return None

            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)

            logger.info(f"Checkpoint loaded: {name}")
            return checkpoint_data.get('data')

        except Exception as e:
            logger.error(f"Failed to load checkpoint {name}: {str(e)}")
            return None

    def exists(self, name: str) -> bool:
        """
        Check if checkpoint exists.

        Args:
            name: Checkpoint name

        Returns:
            True if checkpoint exists, False otherwise
        """
        checkpoint_file = self.checkpoint_dir / f"{name}.json"
        return checkpoint_file.exists()

    def delete(self, name: str) -> bool:
        """
        Delete checkpoint file.

        Args:
            name: Checkpoint name

        Returns:
            True if successful, False otherwise
        """
        try:
            checkpoint_file = self.checkpoint_dir / f"{name}.json"

            if checkpoint_file.exists():
                checkpoint_file.unlink()
                logger.info(f"Checkpoint deleted: {name}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete checkpoint {name}: {str(e)}")
            return False

    def list_checkpoints(self) -> List[str]:
        """
        List all available checkpoints.

        Returns:
            List of checkpoint names
        """
        return [f.stem for f in self.checkpoint_dir.glob("*.json")]


class ExtractionProgress:
    """Tracks progress for video extraction operations."""

    def __init__(self, checkpoint: Checkpoint, session_name: str):
        """
        Initialize extraction progress tracker.

        Args:
            checkpoint: Checkpoint manager instance
            session_name: Name for this extraction session
        """
        self.checkpoint = checkpoint
        self.session_name = session_name
        self.processed: Set[str] = set()
        self.failed: Set[str] = set()
        self.total_videos = 0

        # Load existing progress if available
        self._load_progress()

    def _load_progress(self):
        """Load existing progress from checkpoint."""
        data = self.checkpoint.load(self.session_name)

        if data:
            self.processed = set(data.get('processed', []))
            self.failed = set(data.get('failed', []))
            self.total_videos = data.get('total_videos', 0)
            logger.info(
                f"Resumed from checkpoint: {len(self.processed)} processed, "
                f"{len(self.failed)} failed"
            )

    def _save_progress(self):
        """Save current progress to checkpoint."""
        data = {
            'processed': list(self.processed),
            'failed': list(self.failed),
            'total_videos': self.total_videos
        }
        self.checkpoint.save(self.session_name, data)

    def set_total(self, total: int):
        """
        Set total number of videos to process.

        Args:
            total: Total video count
        """
        self.total_videos = total
        self._save_progress()

    def mark_processed(self, video_id: str):
        """
        Mark a video as successfully processed.

        Args:
            video_id: Video ID
        """
        self.processed.add(video_id)
        # Remove from failed if it was there
        self.failed.discard(video_id)
        self._save_progress()

    def mark_failed(self, video_id: str):
        """
        Mark a video as failed.

        Args:
            video_id: Video ID
        """
        self.failed.add(video_id)
        self._save_progress()

    def is_processed(self, video_id: str) -> bool:
        """
        Check if video has been processed.

        Args:
            video_id: Video ID

        Returns:
            True if processed, False otherwise
        """
        return video_id in self.processed

    def is_failed(self, video_id: str) -> bool:
        """
        Check if video has failed.

        Args:
            video_id: Video ID

        Returns:
            True if failed, False otherwise
        """
        return video_id in self.failed

    def get_remaining(self, all_video_ids: List[str]) -> List[str]:
        """
        Get list of videos that still need processing.

        Args:
            all_video_ids: Complete list of video IDs

        Returns:
            List of unprocessed video IDs
        """
        return [vid for vid in all_video_ids if not self.is_processed(vid)]

    def get_stats(self) -> Dict:
        """
        Get progress statistics.

        Returns:
            Dictionary with progress stats
        """
        return {
            'total': self.total_videos,
            'processed': len(self.processed),
            'failed': len(self.failed),
            'remaining': self.total_videos - len(self.processed),
            'success_rate': len(self.processed) / self.total_videos if self.total_videos > 0 else 0
        }

    def clear(self):
        """Clear all progress and delete checkpoint."""
        self.processed.clear()
        self.failed.clear()
        self.total_videos = 0
        self.checkpoint.delete(self.session_name)
