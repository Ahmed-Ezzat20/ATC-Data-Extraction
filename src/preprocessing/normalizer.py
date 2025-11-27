"""
ATC Text Normalizer

Provides comprehensive text normalization for ATC communications including:
- Spelling corrections
- Diacritic normalization
- Letter-to-phonetic word mappings (NATO alphabet)
- Number-to-word conversions
- Capitalization normalization
- Tag removal
"""

import re
import unicodedata
from typing import Dict, List, Optional, Set


class ATCTextNormalizer:
    """Normalize ATC transcription text according to standard conventions."""

    # NATO Phonetic Alphabet
    PHONETIC_ALPHABET = {
        'A': 'ALPHA', 'B': 'BRAVO', 'C': 'CHARLIE', 'D': 'DELTA',
        'E': 'ECHO', 'F': 'FOXTROT', 'G': 'GOLF', 'H': 'HOTEL',
        'I': 'INDIA', 'J': 'JULIET', 'K': 'KILO', 'L': 'LIMA',
        'M': 'MIKE', 'N': 'NOVEMBER', 'O': 'OSCAR', 'P': 'PAPA',
        'Q': 'QUEBEC', 'R': 'ROMEO', 'S': 'SIERRA', 'T': 'TANGO',
        'U': 'UNIFORM', 'V': 'VICTOR', 'W': 'WHISKEY', 'X': 'XRAY',
        'Y': 'YANKEE', 'Z': 'ZULU'
    }

    # Number to word mapping (0-9)
    NUMBER_WORDS = {
        '0': 'ZERO', '1': 'ONE', '2': 'TWO', '3': 'THREE', '4': 'FOUR',
        '5': 'FIVE', '6': 'SIX', '7': 'SEVEN', '8': 'EIGHT', '9': 'NINER'
    }

    # Common ATC spelling corrections
    SPELLING_CORRECTIONS = {
        'ROGER': 'ROGER',
        'RODGER': 'ROGER',
        'WILCO': 'WILCO',
        'WILKO': 'WILCO',
        'AFFIRMATIVE': 'AFFIRMATIVE',
        'AFIRMATIVE': 'AFFIRMATIVE',
        'NEGATIVE': 'NEGATIVE',
        'NEGITIVE': 'NEGATIVE',
        'CLEARED': 'CLEARED',
        'CLEARD': 'CLEARED',
        'RUNWAY': 'RUNWAY',
        'RUNAWAY': 'RUNWAY',
        'TAXI': 'TAXI',
        'TAXIE': 'TAXI',
        'CONTACT': 'CONTACT',
        'CONTACT': 'CONTACT',
        'FREQUENCY': 'FREQUENCY',
        'FREQ': 'FREQUENCY',
        'SQUAWK': 'SQUAWK',
        'SQWAWK': 'SQUAWK',
        'ALTITUDE': 'ALTITUDE',
        'ALT': 'ALTITUDE',
        'DESCENT': 'DESCENT',
        'DECENT': 'DESCENT',
        'APPROACH': 'APPROACH',
        'APROACH': 'APPROACH',
        'DEPARTURE': 'DEPARTURE',
        'DEPATURE': 'DEPARTURE',
        'MAINTAIN': 'MAINTAIN',
        'MANTAIN': 'MAINTAIN',
        'TRAFFIC': 'TRAFFIC',
        'TRAFIC': 'TRAFFIC',
        'CONTINUE': 'CONTINUE',
        'CONTIUE': 'CONTINUE',
    }

    # Non-critical tags to remove (these are removed in-place)
    REMOVABLE_TAGS = [
        r'\[GROUND\]',
        r'\[AIR\]',
        r'\[SPEAKER\]',
        r'\[PILOT\]',
        r'\[ATC\]',
        r'\[TOWER\]',
        r'\[CENTER\]',
        r'\[APPROACH\]',
        r'\[DEPARTURE\]',
        r'\[CLEARANCE\]',
    ]

    def __init__(
        self,
        apply_spelling_corrections: bool = True,
        normalize_diacritics: bool = True,
        expand_phonetic_letters: bool = True,
        expand_numbers: bool = True,
        uppercase: bool = True,
        remove_tags: bool = True,
        custom_corrections: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the ATC text normalizer.

        Args:
            apply_spelling_corrections: Apply spelling corrections
            normalize_diacritics: Remove diacritics (accents)
            expand_phonetic_letters: Convert single letters to NATO phonetic
            expand_numbers: Convert digits to words
            uppercase: Convert all text to uppercase
            remove_tags: Remove non-critical tags
            custom_corrections: Additional custom spelling corrections
        """
        self.apply_spelling_corrections = apply_spelling_corrections
        self.normalize_diacritics = normalize_diacritics
        self.expand_phonetic_letters = expand_phonetic_letters
        self.expand_numbers = expand_numbers
        self.uppercase = uppercase
        self.remove_tags = remove_tags

        # Merge custom corrections
        self.spelling_corrections = self.SPELLING_CORRECTIONS.copy()
        if custom_corrections:
            self.spelling_corrections.update(custom_corrections)

    def normalize_text(self, text: str) -> str:
        """
        Apply all normalization steps to text.

        Args:
            text: Input text

        Returns:
            Normalized text
        """
        if not text:
            return text

        # 1. Convert to uppercase first (makes pattern matching easier)
        if self.uppercase:
            text = text.upper()

        # 2. Normalize diacritics
        if self.normalize_diacritics:
            text = self._remove_diacritics(text)

        # 3. Remove non-critical tags
        if self.remove_tags:
            text = self._remove_tags(text)

        # 4. Expand phonetic letters (before spelling corrections)
        if self.expand_phonetic_letters:
            text = self._expand_phonetic_letters(text)

        # 5. Expand numbers to words
        if self.expand_numbers:
            text = self._expand_numbers(text)

        # 6. Apply spelling corrections
        if self.apply_spelling_corrections:
            text = self._apply_spelling_corrections(text)

        # 7. Clean up extra whitespace
        text = self._clean_whitespace(text)

        return text

    def _remove_diacritics(self, text: str) -> str:
        """
        Remove diacritics (accents) from text.

        Args:
            text: Input text

        Returns:
            Text with diacritics removed
        """
        # Normalize to NFD (canonical decomposition)
        nfd = unicodedata.normalize('NFD', text)
        # Filter out combining characters (diacritics)
        return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')

    def _remove_tags(self, text: str) -> str:
        """
        Remove non-critical tags from text.

        Args:
            text: Input text

        Returns:
            Text with tags removed
        """
        for tag_pattern in self.REMOVABLE_TAGS:
            text = re.sub(tag_pattern, '', text, flags=re.IGNORECASE)
        return text

    def _expand_phonetic_letters(self, text: str) -> str:
        """
        Expand single letters to NATO phonetic alphabet.

        Handles patterns like:
        - "N 1 2 3" → "NOVEMBER ONE TWO THREE"
        - "RUNWAY 2 7 L" → "RUNWAY TWO SEVEN LEFT"

        Args:
            text: Input text

        Returns:
            Text with letters expanded
        """
        # Pattern: single letter surrounded by spaces or at boundaries
        # But avoid expanding letters in known words
        words = text.split()
        result = []

        for word in words:
            # Only expand single-letter words
            if len(word) == 1 and word.isalpha() and word.upper() in self.PHONETIC_ALPHABET:
                result.append(self.PHONETIC_ALPHABET[word.upper()])
            # Handle runway designators like "27L", "09R"
            elif re.match(r'^\d{2}[LRC]$', word):
                # Keep the numbers, expand the letter
                numbers = word[:2]
                letter = word[2]
                letter_word = {
                    'L': 'LEFT',
                    'R': 'RIGHT',
                    'C': 'CENTER'
                }.get(letter, letter)
                # Will be processed by number expansion later
                result.append(numbers + ' ' + letter_word)
            else:
                result.append(word)

        return ' '.join(result)

    def _expand_numbers(self, text: str) -> str:
        """
        Expand numbers to words (digit by digit).

        Examples:
        - "350" → "THREE FIVE ZERO"
        - "27" → "TWO SEVEN"
        - "118.3" → "ONE ONE EIGHT DECIMAL THREE"

        Args:
            text: Input text

        Returns:
            Text with numbers expanded
        """
        def expand_number_match(match):
            number_str = match.group(0)

            # Handle decimals (frequencies)
            if '.' in number_str:
                parts = number_str.split('.')
                integer_part = ' '.join(self.NUMBER_WORDS.get(d, d) for d in parts[0])
                decimal_part = ' '.join(self.NUMBER_WORDS.get(d, d) for d in parts[1])
                return f"{integer_part} DECIMAL {decimal_part}"
            else:
                # Digit by digit
                return ' '.join(self.NUMBER_WORDS.get(d, d) for d in number_str)

        # Match numbers (including decimals)
        text = re.sub(r'\d+\.?\d*', expand_number_match, text)
        return text

    def _apply_spelling_corrections(self, text: str) -> str:
        """
        Apply spelling corrections.

        Args:
            text: Input text

        Returns:
            Text with corrections applied
        """
        words = text.split()
        corrected = []

        for word in words:
            # Check if word needs correction
            corrected_word = self.spelling_corrections.get(word, word)
            corrected.append(corrected_word)

        return ' '.join(corrected)

    def _clean_whitespace(self, text: str) -> str:
        """
        Clean up extra whitespace.

        Args:
            text: Input text

        Returns:
            Text with normalized whitespace
        """
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Strip leading/trailing whitespace
        text = text.strip()
        return text

    def batch_normalize(self, texts: List[str]) -> List[str]:
        """
        Normalize a batch of texts.

        Args:
            texts: List of input texts

        Returns:
            List of normalized texts
        """
        return [self.normalize_text(text) for text in texts]
