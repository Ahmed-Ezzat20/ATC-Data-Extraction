#!/usr/bin/env python3
"""
Test Preprocessing Functions

Demonstrates the ATC text normalization and filtering capabilities.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from preprocessing.normalizer import ATCTextNormalizer
from preprocessing.filters import TransmissionFilter


def test_normalizer():
    """Test text normalization."""
    print("="*70)
    print("TESTING ATC TEXT NORMALIZER")
    print("="*70)

    normalizer = ATCTextNormalizer()

    test_cases = [
        # Original text
        ("American 123 contact tower 118.3",
         "Basic communication"),

        ("N 1 2 3 cleared for takeoff runway 2 7 L",
         "Letter and number expansion"),

        ("Runway 09R taxi via Alpha Bravo",
         "Runway designator with letters"),

        ("Descend and maintain 350",
         "Altitude with numbers"),

        ("Contact departure on 121.9",
         "Frequency with decimal"),

        ("[GROUND] American 456 roger wilco",
         "Tag removal"),

        ("café Naïve résumé",
         "Diacritic normalization"),

        ("rodger that, cleard for aproach",
         "Spelling corrections"),

        ("American 123, contact tower on 118.3!",
         "Punctuation removal"),

        ("Roger that... cleared for takeoff???",
         "Multiple punctuation marks"),
    ]

    for i, (text, description) in enumerate(test_cases, 1):
        normalized = normalizer.normalize_text(text)

        print(f"\nTest {i}: {description}")
        print(f"  Original:   {text}")
        print(f"  Normalized: {normalized}")


def test_filter():
    """Test transmission filtering."""
    print("\n" + "="*70)
    print("TESTING TRANSMISSION FILTER")
    print("="*70)

    filter = TransmissionFilter(min_length=3)

    test_cases = [
        ("American 123 contact tower", False, "Valid transmission"),
        ("[NO_ENG] Non-English text here", True, "Non-English tag"),
        ("[UNINTELLIGIBLE] ???", True, "Unintelligible tag"),
        ("OK", True, "Too short"),
        ("Normal communication here", False, "Valid communication"),
        ("[UNCLEAR] Not sure what was said", True, "Quality issue"),
    ]

    for i, (text, should_exclude, description) in enumerate(test_cases, 1):
        excluded, reason = filter.should_exclude(text)

        status = "[EXCLUDED]" if excluded else "[KEPT]"
        expected = "[CORRECT]" if excluded == should_exclude else "[WRONG]"

        print(f"\nTest {i}: {description}")
        print(f"  Text: {text}")
        print(f"  Result: {status} {expected}")
        if excluded:
            print(f"  Reason: {reason}")


def test_complete_pipeline():
    """Test complete preprocessing pipeline."""
    print("\n" + "="*70)
    print("TESTING COMPLETE PIPELINE")
    print("="*70)

    normalizer = ATCTextNormalizer()
    filter = TransmissionFilter()

    test_texts = [
        "American 123 contact tower 118.3",
        "[GROUND] N 4 5 6 taxi to runway 27L",
        "[NO_ENG] Non-English communication",
        "Descent and maintain flight level 350",
        "[UNINTELLIGIBLE] ???",
        "Delta 789 cleared for takeoff runway 09R",
        "OK",  # Too short
        "Contact departure on 121.9",
    ]

    print(f"\nProcessing {len(test_texts)} test transmissions...\n")

    kept = 0
    filtered = 0

    for i, text in enumerate(test_texts, 1):
        # Check if should be filtered
        should_exclude, reason = filter.should_exclude(text)

        if should_exclude:
            filtered += 1
            print(f"{i}. FILTERED: {text}")
            print(f"   Reason: {reason}\n")
        else:
            kept += 1
            # Normalize
            normalized = normalizer.normalize_text(text)
            print(f"{i}. KEPT:")
            print(f"   Original:   {text}")
            print(f"   Normalized: {normalized}\n")

    print(f"Summary:")
    print(f"  Total: {len(test_texts)}")
    print(f"  Kept: {kept}")
    print(f"  Filtered: {filtered}")
    print(f"  Filtering rate: {filtered/len(test_texts)*100:.1f}%")


def main():
    """Run all tests."""
    test_normalizer()
    test_filter()
    test_complete_pipeline()

    print("\n" + "="*70)
    print("ALL TESTS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
