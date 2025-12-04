"""
Audio Quality Metrics Module

This module provides functions to calculate audio quality metrics for ATC speech:
- Signal-to-Noise Ratio (SNR)
- Language detection
- Voice Activity Detection (VAD) / Speech ratio

Author: Manus AI
Date: December 4, 2025
"""

import numpy as np
import librosa
from typing import Dict, Optional
from langdetect import detect, detect_langs, LangDetectException


def calculate_snr(audio: np.ndarray, sample_rate: int = 16000) -> float:
    """
    Calculate Signal-to-Noise Ratio (SNR) for an audio segment.
    
    This uses a simple energy-based approach:
    1. Estimate noise from the quietest portions of the audio
    2. Calculate signal power from the entire audio
    3. Compute SNR = 10 * log10(signal_power / noise_power)
    
    Args:
        audio: Audio data as numpy array
        sample_rate: Sample rate of the audio
        
    Returns:
        SNR in decibels (dB)
    """
    if len(audio) == 0:
        return 0.0
    
    # Calculate the energy of the signal
    signal_power = np.mean(audio ** 2)
    
    # Estimate noise from the quietest 10% of frames
    frame_length = int(0.025 * sample_rate)  # 25ms frames
    hop_length = int(0.010 * sample_rate)    # 10ms hop
    
    # Split audio into frames
    frames = librosa.util.frame(audio, frame_length=frame_length, hop_length=hop_length)
    
    # Calculate energy per frame
    frame_energies = np.sum(frames ** 2, axis=0)
    
    # Estimate noise from the quietest 10% of frames
    noise_threshold = np.percentile(frame_energies, 10)
    noise_frames = frames[:, frame_energies <= noise_threshold]
    
    if noise_frames.size > 0:
        noise_power = np.mean(noise_frames ** 2)
    else:
        # Fallback: use minimum frame energy
        noise_power = np.min(frame_energies) / frame_length
    
    # Avoid division by zero
    if noise_power == 0:
        return 60.0  # Very high SNR if no noise detected
    
    # Calculate SNR in dB
    snr_db = 10 * np.log10(signal_power / noise_power)
    
    return float(snr_db)


def detect_language(text: str) -> Dict[str, any]:
    """
    Detect the language of a text transcript.
    
    Args:
        text: Text transcript
        
    Returns:
        Dictionary with 'language' (ISO 639-1 code) and 'confidence' (0.0-1.0)
    """
    if not text or len(text.strip()) < 3:
        return {"language": "unknown", "confidence": 0.0}
    
    try:
        # Get language probabilities
        langs = detect_langs(text)
        
        if langs:
            # Return the most probable language
            top_lang = langs[0]
            return {
                "language": top_lang.lang,
                "confidence": float(top_lang.prob)
            }
        else:
            return {"language": "unknown", "confidence": 0.0}
            
    except LangDetectException:
        # Language detection failed
        return {"language": "unknown", "confidence": 0.0}


def calculate_speech_ratio(audio: np.ndarray, sample_rate: int = 16000, 
                          aggressiveness: int = 2) -> float:
    """
    Calculate the ratio of speech to total audio using Voice Activity Detection.
    
    This uses a simple energy-based VAD approach since py-webrtcvad requires
    specific audio formats.
    
    Args:
        audio: Audio data as numpy array
        sample_rate: Sample rate of the audio
        aggressiveness: VAD aggressiveness (0-3, higher = more aggressive)
        
    Returns:
        Speech ratio (0.0-1.0), where 1.0 means 100% speech
    """
    if len(audio) == 0:
        return 0.0
    
    # Frame parameters
    frame_duration_ms = 30  # 30ms frames
    frame_length = int(sample_rate * frame_duration_ms / 1000)
    
    # Ensure audio length is a multiple of frame_length
    num_frames = len(audio) // frame_length
    if num_frames == 0:
        return 0.0
    
    audio_trimmed = audio[:num_frames * frame_length]
    
    # Split into frames
    frames = audio_trimmed.reshape(num_frames, frame_length)
    
    # Calculate energy per frame
    frame_energies = np.sum(frames ** 2, axis=1)
    
    # Determine speech threshold based on aggressiveness
    # Higher aggressiveness = higher threshold = fewer frames classified as speech
    percentiles = {
        0: 20,  # Very permissive
        1: 30,  # Permissive
        2: 40,  # Moderate (default)
        3: 50,  # Aggressive
    }
    threshold_percentile = percentiles.get(aggressiveness, 40)
    
    # Calculate threshold
    energy_threshold = np.percentile(frame_energies, threshold_percentile)
    
    # Count frames above threshold as speech
    speech_frames = np.sum(frame_energies > energy_threshold)
    
    # Calculate ratio
    speech_ratio = speech_frames / num_frames
    
    return float(speech_ratio)


def calculate_all_metrics(audio: np.ndarray, text: str, 
                         sample_rate: int = 16000) -> Dict[str, any]:
    """
    Calculate all audio quality metrics for a segment.
    
    Args:
        audio: Audio data as numpy array
        text: Text transcript
        sample_rate: Sample rate of the audio
        
    Returns:
        Dictionary with all quality metrics
    """
    # Calculate SNR
    snr_db = calculate_snr(audio, sample_rate)
    
    # Detect language
    lang_info = detect_language(text)
    
    # Calculate speech ratio
    speech_ratio = calculate_speech_ratio(audio, sample_rate)
    
    return {
        "snr_db": round(snr_db, 2),
        "language": lang_info["language"],
        "language_confidence": round(lang_info["confidence"], 3),
        "speech_ratio": round(speech_ratio, 3)
    }


def passes_quality_filters(metrics: Dict[str, any], 
                          min_snr_db: float = 15.0,
                          required_language: str = "en",
                          min_language_confidence: float = 0.8,
                          min_speech_ratio: float = 0.6) -> bool:
    """
    Check if audio metrics pass quality thresholds.
    
    Args:
        metrics: Quality metrics dictionary
        min_snr_db: Minimum SNR in dB
        required_language: Required language code
        min_language_confidence: Minimum language confidence
        min_speech_ratio: Minimum speech ratio
        
    Returns:
        True if all filters pass, False otherwise
    """
    # Check SNR
    if metrics["snr_db"] < min_snr_db:
        return False
    
    # Check language
    if metrics["language"] != required_language:
        return False
    
    # Check language confidence
    if metrics["language_confidence"] < min_language_confidence:
        return False
    
    # Check speech ratio
    if metrics["speech_ratio"] < min_speech_ratio:
        return False
    
    return True
