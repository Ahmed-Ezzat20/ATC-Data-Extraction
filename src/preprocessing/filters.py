"""
Transmission Filtering Module

Handles exclusion of transmissions based on tags, conditions, and manual rules.
"""

import re
from typing import List, Set, Optional, Callable
from pathlib import Path


class TransmissionFilter:
    """Filter transmissions based on tags and conditions."""

    # Default exclusion tags
    DEFAULT_EXCLUSION_TAGS = [
        r'\[NO_ENG\]',           # Non-English
        r'\[\|_NO_ENG\]',        # Non-English variant
        r'\[CZECH_\]',           # Czech language
        r'\[FRENCH_\]',          # French language
        r'\[GERMAN_\]',          # German language
        r'\[SPANISH_\]',         # Spanish language
        r'\[UNINTELLIGIBLE\]',   # Unintelligible audio
        r'\[\|_UNINTELLIGIBLE\]',# Unintelligible variant
        r'\[CROSSTALK\]',        # Multiple speakers
        r'\[NOISE\]',            # Excessive noise
        r'\[STATIC\]',           # Radio static
        r'\[REDACTED\]',         # Redacted content
        r'\[UNCLEAR\]',          # Unclear audio
    ]

    # Patterns that indicate low-quality transcriptions
    QUALITY_PATTERNS = [
        r'\[.*\?\]',             # Question marks in tags indicate uncertainty
        r'\(\?\)',               # Uncertainty markers
        r'<UNK>',                # Unknown tokens
        r'<unk>',                # Unknown tokens (lowercase)
        r'\*\*\*',               # Censored/unclear parts
        r'---',                  # Missing sections
    ]

    def __init__(
        self,
        exclusion_tags: Optional[List[str]] = None,
        exclude_quality_issues: bool = True,
        min_length: int = 3,
        max_length: Optional[int] = None,
        custom_filter: Optional[Callable[[str], bool]] = None,
        manual_exclusions_file: Optional[str] = None
    ):
        """
        Initialize the transmission filter.

        Args:
            exclusion_tags: List of regex patterns for tags to exclude
            exclude_quality_issues: Exclude transmissions with quality markers
            min_length: Minimum text length (words) to keep
            max_length: Maximum text length (words) to keep (None = no limit)
            custom_filter: Custom filter function (return True to keep)
            manual_exclusions_file: Path to file with manual exclusions (one per line)
        """
        # Use default tags if none provided
        if exclusion_tags is None:
            self.exclusion_tags = self.DEFAULT_EXCLUSION_TAGS.copy()
        else:
            self.exclusion_tags = exclusion_tags

        self.exclude_quality_issues = exclude_quality_issues
        self.min_length = min_length
        self.max_length = max_length
        self.custom_filter = custom_filter

        # Load manual exclusions
        self.manual_exclusions: Set[str] = set()
        if manual_exclusions_file:
            self._load_manual_exclusions(manual_exclusions_file)

        # Compile regex patterns for efficiency
        self.exclusion_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.exclusion_tags
        ]

        if self.exclude_quality_issues:
            self.quality_patterns = [
                re.compile(pattern, re.IGNORECASE) for pattern in self.QUALITY_PATTERNS
            ]
        else:
            self.quality_patterns = []

    def _load_manual_exclusions(self, file_path: str):
        """
        Load manual exclusions from file.

        Args:
            file_path: Path to exclusions file
        """
        path = Path(file_path)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.manual_exclusions.add(line.upper())

    def should_exclude(self, text: str, context: Optional[dict] = None) -> tuple[bool, str]:
        """
        Determine if a transmission should be excluded.

        Args:
            text: Transmission text
            context: Optional context (video_id, segment_num, etc.)

        Returns:
            Tuple of (should_exclude, reason)
        """
        if not text or not text.strip():
            return (True, "empty")

        # Check manual exclusions
        if text.upper() in self.manual_exclusions:
            return (True, "manual_exclusion")

        # Check exclusion tags
        for pattern in self.exclusion_patterns:
            if pattern.search(text):
                return (True, f"exclusion_tag: {pattern.pattern}")

        # Check quality patterns
        for pattern in self.quality_patterns:
            if pattern.search(text):
                return (True, f"quality_issue: {pattern.pattern}")

        # Check length constraints
        word_count = len(text.split())

        if word_count < self.min_length:
            return (True, f"too_short: {word_count} words")

        if self.max_length and word_count > self.max_length:
            return (True, f"too_long: {word_count} words")

        # Apply custom filter if provided
        if self.custom_filter and not self.custom_filter(text):
            return (True, "custom_filter")

        return (False, "")

    def filter_texts(
        self,
        texts: List[str],
        return_reasons: bool = False
    ) -> List[str] | List[tuple[str, str]]:
        """
        Filter a list of texts.

        Args:
            texts: List of input texts
            return_reasons: If True, return (text, reason) tuples for excluded items

        Returns:
            Filtered list of texts, or list of (text, exclusion_reason) tuples
        """
        if return_reasons:
            results = []
            for text in texts:
                should_exclude, reason = self.should_exclude(text)
                if should_exclude:
                    results.append((text, reason))
            return results
        else:
            return [
                text for text in texts
                if not self.should_exclude(text)[0]
            ]

    def filter_stats(self, texts: List[str]) -> dict:
        """
        Get filtering statistics.

        Args:
            texts: List of input texts

        Returns:
            Dictionary with filtering statistics
        """
        total = len(texts)
        excluded = 0
        reasons = {}

        for text in texts:
            should_exclude, reason = self.should_exclude(text)
            if should_exclude:
                excluded += 1
                reasons[reason] = reasons.get(reason, 0) + 1

        return {
            'total': total,
            'kept': total - excluded,
            'excluded': excluded,
            'exclusion_rate': excluded / total if total > 0 else 0,
            'exclusion_reasons': reasons
        }

    def add_exclusion_tag(self, tag_pattern: str):
        """
        Add a new exclusion tag pattern.

        Args:
            tag_pattern: Regex pattern for tag
        """
        self.exclusion_tags.append(tag_pattern)
        self.exclusion_patterns.append(re.compile(tag_pattern, re.IGNORECASE))

    def add_manual_exclusion(self, text: str):
        """
        Add a manual exclusion.

        Args:
            text: Text to exclude
        """
        self.manual_exclusions.add(text.upper())

    def save_manual_exclusions(self, file_path: str):
        """
        Save manual exclusions to file.

        Args:
            file_path: Output file path
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            f.write("# Manual Exclusions - One per line\n")
            f.write("# Lines starting with # are comments\n\n")
            for exclusion in sorted(self.manual_exclusions):
                f.write(f"{exclusion}\n")
