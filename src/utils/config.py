"""
Configuration Management Module

Handles loading and parsing of configuration from YAML files and environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class GeminiConfig:
    """Gemini API configuration."""
    api_key: str
    model: str = "gemini-2.5-pro"
    request_delay: float = 2.0
    max_retries: int = 3
    retry_delay: float = 1.0
    uppercase_transcripts: bool = True


@dataclass
class AudioConfig:
    """Audio processing configuration."""
    format: str = "wav"
    sample_rate: int = 44100
    channels: int = 2
    bit_depth: int = 16


@dataclass
class PathsConfig:
    """Output paths configuration."""
    transcripts: str = "data/transcripts"
    raw_audio: str = "data/raw_audio"
    segments: str = "data/audio_segments"
    visualizations: str = "data/visualizations"
    logs: str = "logs"
    checkpoints: str = "data/checkpoints"


@dataclass
class Config:
    """Main configuration class."""
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)

    @classmethod
    def from_yaml(cls, config_file: str = "config.yaml") -> "Config":
        """
        Load configuration from YAML file.

        Args:
            config_file: Path to YAML configuration file

        Returns:
            Config instance
        """
        config_path = Path(config_file)

        # Start with default configuration
        config_dict: Dict[str, Any] = {}

        # Load from YAML if exists
        if config_path.exists():
            with open(config_path, 'r') as f:
                config_dict = yaml.safe_load(f) or {}

        # Parse Gemini configuration
        gemini_dict = config_dict.get('gemini', {})
        # Resolve environment variable for API key
        api_key = gemini_dict.get('api_key', '${GEMINI_API_KEY}')
        if api_key.startswith('${') and api_key.endswith('}'):
            env_var = api_key[2:-1]
            api_key = os.environ.get(env_var, '')

        gemini_config = GeminiConfig(
            api_key=api_key,
            model=gemini_dict.get('model', 'gemini-2.5-pro'),
            request_delay=gemini_dict.get('request_delay', 2.0),
            max_retries=gemini_dict.get('max_retries', 3),
            retry_delay=gemini_dict.get('retry_delay', 1.0),
            uppercase_transcripts=gemini_dict.get('uppercase_transcripts', True)
        )

        # Parse Audio configuration
        audio_dict = config_dict.get('audio', {})
        audio_config = AudioConfig(
            format=audio_dict.get('format', 'wav'),
            sample_rate=audio_dict.get('sample_rate', 44100),
            channels=audio_dict.get('channels', 2),
            bit_depth=audio_dict.get('bit_depth', 16)
        )

        # Parse Paths configuration
        paths_dict = config_dict.get('paths', {})
        paths_config = PathsConfig(
            transcripts=paths_dict.get('transcripts', 'data/transcripts'),
            raw_audio=paths_dict.get('raw_audio', 'data/raw_audio'),
            segments=paths_dict.get('segments', 'data/audio_segments'),
            visualizations=paths_dict.get('visualizations', 'data/visualizations'),
            logs=paths_dict.get('logs', 'logs'),
            checkpoints=paths_dict.get('checkpoints', 'data/checkpoints')
        )

        return cls(
            gemini=gemini_config,
            audio=audio_config,
            paths=paths_config
        )

    @classmethod
    def from_defaults(cls) -> "Config":
        """
        Create configuration with default values.

        Returns:
            Config instance with defaults
        """
        api_key = os.environ.get('GEMINI_API_KEY', '')

        return cls(
            gemini=GeminiConfig(api_key=api_key),
            audio=AudioConfig(),
            paths=PathsConfig()
        )

    def to_yaml(self, output_file: str = "config.yaml"):
        """
        Save configuration to YAML file.

        Args:
            output_file: Path to output YAML file
        """
        config_dict = {
            'gemini': {
                'api_key': '${GEMINI_API_KEY}',
                'model': self.gemini.model,
                'request_delay': self.gemini.request_delay,
                'max_retries': self.gemini.max_retries,
                'retry_delay': self.gemini.retry_delay,
                'uppercase_transcripts': self.gemini.uppercase_transcripts
            },
            'audio': {
                'format': self.audio.format,
                'sample_rate': self.audio.sample_rate,
                'channels': self.audio.channels,
                'bit_depth': self.audio.bit_depth
            },
            'paths': {
                'transcripts': self.paths.transcripts,
                'raw_audio': self.paths.raw_audio,
                'segments': self.paths.segments,
                'visualizations': self.paths.visualizations,
                'logs': self.paths.logs,
                'checkpoints': self.paths.checkpoints
            }
        }

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
