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

    # Contraction expansions (applied before punctuation removal)
    CONTRACTIONS = {
        # Common contractions
        "I'M": "I AM",
        "I'VE": "I HAVE",
        "I'LL": "I WILL",
        "I'D": "I WOULD",
        "YOU'RE": "YOU ARE",
        "YOU'VE": "YOU HAVE",
        "YOU'LL": "YOU WILL",
        "YOU'D": "YOU WOULD",
        "HE'S": "HE IS",
        "HE'LL": "HE WILL",
        "HE'D": "HE WOULD",
        "SHE'S": "SHE IS",
        "SHE'LL": "SHE WILL",
        "SHE'D": "SHE WOULD",
        "IT'S": "IT IS",
        "IT'LL": "IT WILL",
        "IT'D": "IT WOULD",
        "WE'RE": "WE ARE",
        "WE'VE": "WE HAVE",
        "WE'LL": "WE WILL",
        "WE'D": "WE WOULD",
        "THEY'RE": "THEY ARE",
        "THEY'VE": "THEY HAVE",
        "THEY'LL": "THEY WILL",
        "THEY'D": "THEY WOULD",
        "THAT'S": "THAT IS",
        "THAT'LL": "THAT WILL",
        "THAT'D": "THAT WOULD",
        "WHO'S": "WHO IS",
        "WHO'LL": "WHO WILL",
        "WHO'D": "WHO WOULD",
        "WHAT'S": "WHAT IS",
        "WHAT'LL": "WHAT WILL",
        "WHAT'D": "WHAT WOULD",
        "WHERE'S": "WHERE IS",
        "WHERE'LL": "WHERE WILL",
        "WHERE'D": "WHERE WOULD",
        "WHEN'S": "WHEN IS",
        "WHEN'LL": "WHEN WILL",
        "WHEN'D": "WHEN WOULD",
        "WHY'S": "WHY IS",
        "WHY'LL": "WHY WILL",
        "WHY'D": "WHY WOULD",
        "HOW'S": "HOW IS",
        "HOW'LL": "HOW WILL",
        "HOW'D": "HOW WOULD",
        # Negative contractions
        "CAN'T": "CANNOT",
        "WON'T": "WILL NOT",
        "DON'T": "DO NOT",
        "DOESN'T": "DOES NOT",
        "DIDN'T": "DID NOT",
        "HAVEN'T": "HAVE NOT",
        "HASN'T": "HAS NOT",
        "HADN'T": "HAD NOT",
        "AREN'T": "ARE NOT",
        "ISN'T": "IS NOT",
        "WASN'T": "WAS NOT",
        "WEREN'T": "WERE NOT",
        "SHOULDN'T": "SHOULD NOT",
        "WOULDN'T": "WOULD NOT",
        "COULDN'T": "COULD NOT",
        "MIGHTN'T": "MIGHT NOT",
        "MUSTN'T": "MUST NOT",
        "NEEDN'T": "NEED NOT",
        # Modal contractions
        "'LL": "WILL",
        "'VE": "HAVE",
        "'RE": "ARE",
        "'D": "WOULD",
        # Other common forms
        "LET'S": "LET US",
        "AIN'T": "IS NOT",
    }

    def __init__(
        self,
        apply_spelling_corrections: bool = True,
        normalize_diacritics: bool = True,
        expand_phonetic_letters: bool = True,
        expand_numbers: bool = True,
        expand_contractions: bool = True,
        uppercase: bool = True,
        remove_tags: bool = True,
        remove_punctuation: bool = True,
        output_case: str = "upper",
        custom_corrections: Optional[Dict[str, str]] = None,
        custom_contractions: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the ATC text normalizer.

        Args:
            apply_spelling_corrections: Apply spelling corrections
            normalize_diacritics: Remove diacritics (accents)
            expand_phonetic_letters: Convert single letters to NATO phonetic
            expand_numbers: Convert digits to words
            expand_contractions: Expand contractions (e.g., I'M -> I AM)
            uppercase: Convert all text to uppercase
            remove_tags: Remove non-critical tags
            remove_punctuation: Remove punctuation marks
            output_case: Final case handling ('upper', 'lower', 'preserve')
            custom_corrections: Additional custom spelling corrections
            custom_contractions: Additional custom contraction expansions
        """
        self.apply_spelling_corrections = apply_spelling_corrections
        self.normalize_diacritics = normalize_diacritics
        self.expand_phonetic_letters = expand_phonetic_letters
        self.expand_numbers = expand_numbers
        self.expand_contractions = expand_contractions
        self.uppercase = uppercase
        self.remove_tags = remove_tags
        self.remove_punctuation = remove_punctuation
        self.output_case = output_case.lower() if output_case else "upper"

        # Merge custom corrections
        self.spelling_corrections = self.SPELLING_CORRECTIONS.copy()
        if custom_corrections:
            self.spelling_corrections.update(custom_corrections)
        
        # Merge custom contractions
        self.contractions = self.CONTRACTIONS.copy()
        if custom_contractions:
            self.contractions.update(custom_contractions)

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

        # 6. Expand contractions (before punctuation removal)
        if self.expand_contractions:
            text = self._expand_contractions(text)

        # 7. Apply spelling corrections
        if self.apply_spelling_corrections:
            text = self._apply_spelling_corrections(text)

        # 8. Remove punctuation
        if self.remove_punctuation:
            text = self._remove_punctuation(text)

        # 9. Normalize whitespace
        text = self._clean_whitespace(text)

        # 10. Final case handling (overrides uppercase setting if needed)
        if self.output_case == "lower":
            text = text.lower()
        elif self.output_case == "upper":
            text = text.upper()
        # else: "preserve" - keep as-is

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
        - "B6" → "BRAVO 6" (taxiway/gate identifiers)
        - "C4" → "CHARLIE 4" (taxiway/gate identifiers)
        - "C," → "CHARLIE," (handles punctuation)

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
            # Strip trailing punctuation for pattern matching, but preserve it
            trailing_punct = ''
            clean_word = word
            while clean_word and not clean_word[-1].isalnum():
                trailing_punct = clean_word[-1] + trailing_punct
                clean_word = clean_word[:-1]
            
            if not clean_word:
                result.append(word)
                continue
            
            # Only expand single-letter words
            if len(clean_word) == 1 and clean_word.isalpha() and clean_word.upper() in self.PHONETIC_ALPHABET:
                result.append(self.PHONETIC_ALPHABET[clean_word.upper()] + trailing_punct)
            # Handle runway designators like "27L", "09R"
            elif re.match(r'^\d{2}[LRC]$', clean_word):
                # Keep the numbers, expand the letter
                numbers = clean_word[:2]
                letter = clean_word[2]
                letter_word = {
                    'L': 'LEFT',
                    'R': 'RIGHT',
                    'C': 'CENTER'
                }.get(letter, letter)
                # Will be processed by number expansion later
                result.append(numbers + ' ' + letter_word + trailing_punct)
            # Handle alphanumeric identifiers like "B6", "C4", "A12" (taxiway/gate)
            # Pattern: Single letter followed by one or more digits
            elif re.match(r'^[A-Z]\d+$', clean_word):
                letter = clean_word[0]
                numbers = clean_word[1:]
                # Expand letter to phonetic, keep numbers for later expansion
                phonetic = self.PHONETIC_ALPHABET.get(letter, letter)
                result.append(phonetic + ' ' + numbers + trailing_punct)
            # Handle reverse pattern: digits followed by single letter (e.g., "6B")
            elif re.match(r'^\d+[A-Z]$', clean_word):
                numbers = clean_word[:-1]
                letter = clean_word[-1]
                phonetic = self.PHONETIC_ALPHABET.get(letter, letter)
                result.append(numbers + ' ' + phonetic + trailing_punct)
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
        # Pattern: match actual decimals (123.45) OR integers (123)
        # This prevents matching periods that are just punctuation (e.g., "118.")
        text = re.sub(r'\d+\.\d+|\d+', expand_number_match, text)
        return text

    def _expand_contractions(self, text: str) -> str:
        """
        Expand contractions to their full forms.

        Examples:
        - "I'M" -> "I AM"
        - "CAN'T" -> "CANNOT"
        - "WE'RE" -> "WE ARE"

        Note: Possessives (e.g., "PILOT'S") are preserved and handled
        by punctuation removal later.

        Args:
            text: Input text

        Returns:
            Text with contractions expanded
        """
        words = text.split()
        expanded = []

        for word in words:
            # Check if word is a known contraction
            if word in self.contractions:
                expanded.append(self.contractions[word])
            # Check for possessives (word ending in 'S after removing apostrophe)
            # These should NOT be expanded (e.g., PILOT'S should stay as is)
            elif "'S" in word and word.endswith("'S"):
                # This is likely a possessive, not a contraction
                # Keep it as is for now (punctuation removal will handle it)
                expanded.append(word)
            else:
                # Not a contraction, keep as is
                expanded.append(word)

        return ' '.join(expanded)

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

    def _remove_punctuation(self, text: str) -> str:
        """
        Remove punctuation marks from text.

        Args:
            text: Input text

        Returns:
            Text with punctuation removed
        """
        # Remove all punctuation except spaces
        # Keep alphanumeric characters and spaces only
        text = re.sub(r'[^\w\s]', '', text)
        return text

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
