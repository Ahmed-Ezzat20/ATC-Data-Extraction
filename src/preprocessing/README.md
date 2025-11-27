# ATC Text Preprocessing Module

This module provides comprehensive text normalization and filtering for ATC (Air Traffic Control) communications.

## Features

### Text Normalization (`normalizer.py`)

The `ATCTextNormalizer` class performs the following transformations:

1. **Uppercase Conversion**: All text converted to uppercase (ATC standard)
2. **Diacritic Normalization**: Removes accents and diacritical marks (e.g., "café" → "CAFE")
3. **Tag Removal**: Removes non-critical speaker/context tags (e.g., [GROUND], [AIR])
4. **Phonetic Letter Expansion**: Converts single letters to NATO phonetic alphabet
5. **Number Expansion**: Converts digits to words (digit-by-digit)
6. **Spelling Corrections**: Fixes common ATC terminology misspellings
7. **Punctuation Removal**: Removes all punctuation marks (e.g., commas, periods, exclamation marks)
8. **Whitespace Cleanup**: Normalizes spacing

### Transmission Filtering (`filters.py`)

The `TransmissionFilter` class excludes transmissions based on:

1. **Language Tags**: Non-English communications ([NO_ENG], [CZECH_], etc.)
2. **Quality Tags**: Poor quality audio ([UNINTELLIGIBLE], [CROSSTALK], etc.)
3. **Uncertainty Markers**: Uncertain transcriptions ([?], (?), <UNK>)
4. **Length Constraints**: Too short or too long transmissions
5. **Manual Exclusions**: Custom exclusion list

## Usage Examples

### Basic Normalization

```python
from preprocessing.normalizer import ATCTextNormalizer

normalizer = ATCTextNormalizer()

# Example 1: Number expansion
text = "American 123 contact tower 118.3"
normalized = normalizer.normalize_text(text)
print(normalized)
# Output: AMERICAN ONE TWO THREE CONTACT TOWER ONE ONE EIGHT DECIMAL THREE

# Example 2: Phonetic expansion
text = "N 1 2 3 cleared for takeoff"
normalized = normalizer.normalize_text(text)
print(normalized)
# Output: NOVEMBER ONE TWO THREE CLEARED FOR TAKEOFF

# Example 3: Runway designators
text = "Runway 27L taxi via Alpha"
normalized = normalizer.normalize_text(text)
print(normalized)
# Output: RUNWAY TWO SEVEN LEFT TAXI VIA ALPHA

# Example 4: Punctuation removal
text = "American 123, contact tower on 118.3!"
normalized = normalizer.normalize_text(text)
print(normalized)
# Output: AMERICAN ONE TWO THREE CONTACT TOWER ON ONE ONE EIGHT DECIMAL THREE
```

### Custom Configuration

```python
# Disable specific features
normalizer = ATCTextNormalizer(
    expand_phonetic_letters=False,  # Keep single letters as-is
    expand_numbers=False,            # Keep numbers as-is
    remove_punctuation=False,        # Keep punctuation
    uppercase=False                  # Preserve original case
)
```

### Filtering Transmissions

```python
from preprocessing.filters import TransmissionFilter

filter = TransmissionFilter(min_length=3)

# Example: Check if should exclude
text = "[NO_ENG] Non-English communication"
should_exclude, reason = filter.should_exclude(text)
print(f"Exclude: {should_exclude}, Reason: {reason}")
# Output: Exclude: True, Reason: exclusion_tag: \[NO_ENG\]

# Example: Filter a list
texts = [
    "American 123 contact tower",
    "[UNINTELLIGIBLE] ???",
    "Cleared for takeoff"
]
filtered = filter.filter_texts(texts)
print(filtered)
# Output: ['American 123 contact tower', 'Cleared for takeoff']
```

### Complete Pipeline

```python
from preprocessing.normalizer import ATCTextNormalizer
from preprocessing.filters import TransmissionFilter

normalizer = ATCTextNormalizer()
filter = TransmissionFilter()

texts = [
    "American 123 contact tower 118.3",
    "[NO_ENG] Non-English text",
    "N 4 5 6 taxi to runway 27L"
]

for text in texts:
    # Check if should be excluded
    should_exclude, reason = filter.should_exclude(text)

    if not should_exclude:
        # Normalize
        normalized = normalizer.normalize_text(text)
        print(f"Original:   {text}")
        print(f"Normalized: {normalized}\n")
    else:
        print(f"Filtered: {text} (Reason: {reason})\n")
```

## Normalization Details

### NATO Phonetic Alphabet

Single letters are expanded to their phonetic equivalents:

| Letter | Phonetic | Letter | Phonetic |
|--------|----------|--------|----------|
| A | ALPHA | N | NOVEMBER |
| B | BRAVO | O | OSCAR |
| C | CHARLIE | P | PAPA |
| D | DELTA | Q | QUEBEC |
| E | ECHO | R | ROMEO |
| F | FOXTROT | S | SIERRA |
| G | GOLF | T | TANGO |
| H | HOTEL | U | UNIFORM |
| I | INDIA | V | VICTOR |
| J | JULIET | W | WHISKEY |
| K | KILO | X | XRAY |
| L | LIMA | Y | YANKEE |
| M | MIKE | Z | ZULU |

**Important**: Only single-letter words are expanded. Letters within words are not affected.

### Number Expansion

Numbers are converted digit-by-digit:

| Digit | Word | Special |
|-------|------|---------|
| 0 | ZERO | |
| 1 | ONE | |
| 2 | TWO | |
| 3 | THREE | |
| 4 | FOUR | |
| 5 | FIVE | |
| 6 | SIX | |
| 7 | SEVEN | |
| 8 | EIGHT | |
| 9 | NINER | (Note: NINER not NINE) |

**Decimals**: "118.3" → "ONE ONE EIGHT DECIMAL THREE"

### Runway Designators

Runway designators like "27L", "09R" are handled specially:
- "27L" → "TWO SEVEN LEFT"
- "09R" → "ZERO NINER RIGHT"
- "18C" → "ONE EIGHT CENTER"

**Note**: Separate words "2 7 L" → "TWO SEVEN LIMA" (L is treated as single letter)

### Spelling Corrections

Common ATC misspellings are corrected:

| Incorrect | Correct |
|-----------|---------|
| RODGER | ROGER |
| WILKO | WILCO |
| AFIRMATIVE | AFFIRMATIVE |
| NEGITIVE | NEGATIVE |
| CLEARD | CLEARED |
| RUNAWAY | RUNWAY |
| TAXIE | TAXI |
| SQWAWK | SQUAWK |
| DECENT | DESCENT |
| APROACH | APPROACH |
| DEPATURE | DEPARTURE |
| MANTAIN | MAINTAIN |
| TRAFIC | TRAFFIC |
| CONTIUE | CONTINUE |

## Filter Configuration

### Default Exclusion Tags

The following tags trigger automatic exclusion:

**Language Tags**:
- `[NO_ENG]`, `[|_NO_ENG]` - Non-English
- `[CZECH_]`, `[FRENCH_]`, `[GERMAN_]`, `[SPANISH_]` - Specific languages

**Quality Tags**:
- `[UNINTELLIGIBLE]`, `[|_UNINTELLIGIBLE]` - Unclear audio
- `[CROSSTALK]` - Multiple speakers
- `[NOISE]`, `[STATIC]` - Audio issues
- `[UNCLEAR]` - Uncertain transcription
- `[REDACTED]` - Redacted content

**Uncertainty Markers**:
- `[?]`, `(?)` - Question marks in tags
- `<UNK>`, `<unk>` - Unknown tokens
- `***`, `---` - Missing/censored sections

### Custom Filtering

```python
# Add custom exclusion tags
filter = TransmissionFilter()
filter.add_exclusion_tag(r'\[PRIVATE\]')

# Set length constraints
filter = TransmissionFilter(
    min_length=5,   # Minimum 5 words
    max_length=50   # Maximum 50 words
)

# Load manual exclusions from file
filter = TransmissionFilter(
    manual_exclusions_file='config/manual_exclusions.txt'
)

# Add manual exclusion programmatically
filter.add_manual_exclusion("IGNORE THIS TEXT")
```

### Filtering Statistics

```python
texts = ["Text 1", "Text 2", "[NO_ENG] Text 3", "OK"]
stats = filter.filter_stats(texts)
print(stats)
# {
#     'total': 4,
#     'kept': 2,
#     'excluded': 2,
#     'exclusion_rate': 0.5,
#     'exclusion_reasons': {
#         'exclusion_tag: \\[NO_ENG\\]': 1,
#         'too_short: 1 words': 1
#     }
# }
```

## Command-Line Usage

Process all transcripts in a directory:

```bash
# Full preprocessing with all features
python preprocess_data.py --data-dir data --output-dir data/preprocessed

# Disable specific features
python preprocess_data.py --data-dir data \
    --no-phonetic-expansion \
    --no-number-expansion \
    --no-punctuation-removal

# Custom filtering
python preprocess_data.py --data-dir data \
    --min-length 5 \
    --max-length 100 \
    --manual-exclusions config/manual_exclusions.txt

# Minimal preprocessing (no filtering)
python preprocess_data.py --data-dir data \
    --no-filtering \
    --output-dir data/preprocessed_minimal
```

## Testing

Run the test suite to verify functionality:

```bash
python examples/test_preprocessing.py
```

This will test:
- Text normalization with various examples
- Transmission filtering with different scenarios
- Complete pipeline integration

## Output Format

Preprocessed transcripts include both original and normalized text:

```json
{
  "video_id": "VIDEO_ID",
  "segments": [
    {
      "segment_num": 1,
      "transcript": "AMERICAN ONE TWO THREE CONTACT TOWER",
      "original_transcript": "American 123 contact tower",
      "start_time": 5,
      "duration": 6
    }
  ],
  "total_segments": 10,
  "filtered_segments": 2,
  "preprocessing_date": "2024-01-15T10:30:00"
}
```

## Best Practices

1. **Test First**: Run `test_preprocessing.py` to understand the transformations
2. **Keep Originals**: The preprocessing script preserves original text in `original_transcript` field
3. **Review Report**: Check `preprocessing_report.txt` for statistics
4. **Iterative Refinement**: Start with default settings, then adjust based on results
5. **Manual Exclusions**: Use `config/manual_exclusions.txt` for dataset-specific exclusions
6. **Backup Data**: Preprocessing outputs to separate directory, original data unchanged
