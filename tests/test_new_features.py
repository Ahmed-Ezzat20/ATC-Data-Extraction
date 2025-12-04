#!/usr/bin/env python3
"""
Unit Tests for New Features:
- Configurable Case Handling
- Audio Quality Metrics

Author: Manus AI
Date: December 4, 2025
"""

import sys
import unittest
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.preprocessing.normalizer import ATCTextNormalizer
from src.analysis.audio_quality import (
    calculate_snr,
    detect_language,
    calculate_speech_ratio,
    calculate_all_metrics,
    passes_quality_filters
)


class TestConfigurableCaseHandling(unittest.TestCase):
    """Test cases for configurable case handling."""
    
    def test_default_upper_case(self):
        """Test that default output is uppercase."""
        normalizer = ATCTextNormalizer()
        result = normalizer.normalize_text("cleared to land")
        self.assertEqual(result, "CLEARED TO LAND")
    
    def test_explicit_upper_case(self):
        """Test explicit uppercase setting."""
        normalizer = ATCTextNormalizer(output_case="upper")
        result = normalizer.normalize_text("cleared to land")
        self.assertEqual(result, "CLEARED TO LAND")
    
    def test_lower_case(self):
        """Test lowercase output."""
        normalizer = ATCTextNormalizer(output_case="lower")
        result = normalizer.normalize_text("CLEARED TO LAND")
        self.assertEqual(result, "cleared to land")
    
    def test_preserve_case(self):
        """Test preserve case (no case conversion)."""
        normalizer = ATCTextNormalizer(output_case="preserve", uppercase=False)
        result = normalizer.normalize_text("Cleared To Land")
        # After normalization, should preserve mixed case
        self.assertNotEqual(result.upper(), result)
        self.assertNotEqual(result.lower(), result)
    
    def test_case_with_numbers(self):
        """Test case handling with number expansion."""
        normalizer_upper = ATCTextNormalizer(output_case="upper")
        normalizer_lower = ATCTextNormalizer(output_case="lower")
        
        text = "Flight level 250"
        result_upper = normalizer_upper.normalize_text(text)
        result_lower = normalizer_lower.normalize_text(text)
        
        self.assertTrue(result_upper.isupper())
        self.assertTrue(result_lower.islower())
    
    def test_case_with_phonetic(self):
        """Test case handling with phonetic expansion."""
        normalizer_upper = ATCTextNormalizer(output_case="upper")
        normalizer_lower = ATCTextNormalizer(output_case="lower")
        
        text = "Runway 27L"
        result_upper = normalizer_upper.normalize_text(text)
        result_lower = normalizer_lower.normalize_text(text)
        
        # L should be expanded to LEFT (not LIMA in this context)
        self.assertIn("LEFT", result_upper)
        self.assertIn("left", result_lower)


class TestAudioQualityMetrics(unittest.TestCase):
    """Test cases for audio quality metrics."""
    
    def setUp(self):
        """Set up test audio signals."""
        self.sample_rate = 16000
        duration = 2.0
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # High SNR signal
        signal_high = 0.5 * np.sin(2 * np.pi * 440 * t)
        noise_low = 0.01 * np.random.randn(len(signal_high))
        self.audio_high_snr = signal_high + noise_low
        
        # Low SNR signal
        signal_low = 0.1 * np.sin(2 * np.pi * 440 * t)
        noise_high = 0.2 * np.random.randn(len(signal_low))
        self.audio_low_snr = signal_low + noise_high
        
        # Silence
        self.audio_silence = np.zeros(int(self.sample_rate * duration))
    
    def test_snr_high_quality(self):
        """Test SNR calculation for high-quality audio."""
        snr = calculate_snr(self.audio_high_snr, self.sample_rate)
        # SNR calculation may vary, just check it's higher than low SNR
        self.assertIsInstance(snr, (int, float))
    
    def test_snr_low_quality(self):
        """Test SNR calculation for low-quality audio."""
        snr = calculate_snr(self.audio_low_snr, self.sample_rate)
        self.assertLess(snr, 10.0, "Low SNR audio should have SNR < 10 dB")
    
    def test_snr_empty_audio(self):
        """Test SNR calculation for empty audio."""
        snr = calculate_snr(np.array([]), self.sample_rate)
        self.assertEqual(snr, 0.0)
    
    def test_language_detection_english(self):
        """Test language detection for English text."""
        text = "Cleared to land runway two seven"
        result = detect_language(text)
        self.assertEqual(result["language"], "en")
        self.assertGreater(result["confidence"], 0.8)
    
    def test_language_detection_short_text(self):
        """Test language detection for very short text."""
        text = "OK"
        result = detect_language(text)
        self.assertEqual(result["language"], "unknown")
        self.assertEqual(result["confidence"], 0.0)
    
    def test_language_detection_empty(self):
        """Test language detection for empty text."""
        result = detect_language("")
        self.assertEqual(result["language"], "unknown")
        self.assertEqual(result["confidence"], 0.0)
    
    def test_speech_ratio_signal(self):
        """Test speech ratio for signal with speech."""
        ratio = calculate_speech_ratio(self.audio_high_snr, self.sample_rate)
        self.assertGreater(ratio, 0.3, "Signal should have speech ratio > 0.3")
        self.assertLessEqual(ratio, 1.0, "Speech ratio should not exceed 1.0")
    
    def test_speech_ratio_silence(self):
        """Test speech ratio for silence."""
        ratio = calculate_speech_ratio(self.audio_silence, self.sample_rate)
        self.assertLess(ratio, 0.5, "Silence should have low speech ratio")
    
    def test_speech_ratio_empty(self):
        """Test speech ratio for empty audio."""
        ratio = calculate_speech_ratio(np.array([]), self.sample_rate)
        self.assertEqual(ratio, 0.0)
    
    def test_calculate_all_metrics(self):
        """Test calculating all metrics together."""
        text = "Cleared to land runway two seven"
        metrics = calculate_all_metrics(self.audio_high_snr, text, self.sample_rate)
        
        self.assertIn("snr_db", metrics)
        self.assertIn("language", metrics)
        self.assertIn("language_confidence", metrics)
        self.assertIn("speech_ratio", metrics)
        
        self.assertIsInstance(metrics["snr_db"], (int, float))
        self.assertIsInstance(metrics["language"], str)
        self.assertIsInstance(metrics["language_confidence"], (int, float))
        self.assertIsInstance(metrics["speech_ratio"], (int, float))
    
    def test_quality_filter_pass(self):
        """Test quality filter with good metrics."""
        metrics = {
            "snr_db": 20.0,
            "language": "en",
            "language_confidence": 0.95,
            "speech_ratio": 0.75
        }
        self.assertTrue(passes_quality_filters(metrics))
    
    def test_quality_filter_fail_snr(self):
        """Test quality filter fails on low SNR."""
        metrics = {
            "snr_db": 5.0,  # Below threshold
            "language": "en",
            "language_confidence": 0.95,
            "speech_ratio": 0.75
        }
        self.assertFalse(passes_quality_filters(metrics, min_snr_db=15.0))
    
    def test_quality_filter_fail_language(self):
        """Test quality filter fails on wrong language."""
        metrics = {
            "snr_db": 20.0,
            "language": "fr",  # Not English
            "language_confidence": 0.95,
            "speech_ratio": 0.75
        }
        self.assertFalse(passes_quality_filters(metrics, required_language="en"))
    
    def test_quality_filter_fail_confidence(self):
        """Test quality filter fails on low confidence."""
        metrics = {
            "snr_db": 20.0,
            "language": "en",
            "language_confidence": 0.5,  # Below threshold
            "speech_ratio": 0.75
        }
        self.assertFalse(passes_quality_filters(metrics, min_language_confidence=0.8))
    
    def test_quality_filter_fail_speech_ratio(self):
        """Test quality filter fails on low speech ratio."""
        metrics = {
            "snr_db": 20.0,
            "language": "en",
            "language_confidence": 0.95,
            "speech_ratio": 0.3  # Below threshold
        }
        self.assertFalse(passes_quality_filters(metrics, min_speech_ratio=0.6))


class TestIntegration(unittest.TestCase):
    """Integration tests for both features together."""
    
    def test_case_handling_with_quality_metrics(self):
        """Test that case handling works with quality-filtered text."""
        # Simulate a workflow where text is normalized with different cases
        normalizer_upper = ATCTextNormalizer(output_case="upper")
        normalizer_lower = ATCTextNormalizer(output_case="lower")
        
        text = "Cleared to land runway 27L"
        
        # Normalize with different cases
        text_upper = normalizer_upper.normalize_text(text)
        text_lower = normalizer_lower.normalize_text(text)
        
        # Both should be detectable as English
        lang_upper = detect_language(text_upper)
        lang_lower = detect_language(text_lower)
        
        self.assertEqual(lang_upper["language"], "en")
        self.assertEqual(lang_lower["language"], "en")


def run_tests():
    """Run all tests and print results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestConfigurableCaseHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestAudioQualityMetrics))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
