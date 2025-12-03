"""
Hugging Face Hub Utilities

Functions for authentication, dataset card generation, and uploading to Hugging Face.
"""

from pathlib import Path
from typing import Dict, Optional
from huggingface_hub import HfApi, create_repo
from huggingface_hub.utils import HfHubHTTPError


def check_authentication() -> bool:
    """
    Check if user is authenticated with Hugging Face.
    
    Returns:
        True if authenticated, False otherwise
    """
    try:
        api = HfApi()
        api.whoami()
        return True
    except Exception:
        return False


def generate_dataset_card(
    stats: Dict,
    output_file: str = "README.md",
    dataset_name: str = "ATC Communications Dataset",
    has_audio: bool = True,
    format_type: str = "parquet",
    splits: Optional[list] = None
) -> str:
    """
    Generate a comprehensive dataset card (README.md) for Hugging Face.
    
    Args:
        stats: Dictionary containing dataset statistics
        output_file: Output file path
        dataset_name: Name of the dataset
        has_audio: Whether the dataset includes audio files
        format_type: Format of the dataset ('parquet' or 'manifest')
        splits: List of split names (e.g., ['train', 'validation', 'test'])
        
    Returns:
        Path to the created README file
    """
    if splits is None:
        splits = ['train', 'validation', 'test'] if stats.get('val_segments', 0) > 0 else ['train']
    
    # Calculate totals
    total_segments = stats.get('total_segments', 0)
    total_videos = stats.get('total_videos', 0)
    
    # Calculate duration
    total_duration_seconds = total_segments * 5  # Rough estimate if not provided
    total_hours = total_duration_seconds / 3600
    
    # Estimate word count (rough estimate: 10 words per segment)
    total_words = total_segments * 10
    
    # Determine size category
    if total_segments < 1000:
        size_category = "n<1K"
    elif total_segments < 10000:
        size_category = "1K<n<10K"
    elif total_segments < 100000:
        size_category = "10K<n<100K"
    else:
        size_category = "100K<n<1M"
    
    # Build dataset_info section
    if format_type == "parquet":
        features_yaml = """  features:
  - name: audio_filename
    dtype: string
  - name: video_id
    dtype: string
  - name: segment_num
    dtype: int64
  - name: transcription
    dtype: string
  - name: original_transcription
    dtype: string"""
        
        if has_audio:
            features_yaml += """
  - name: audio
    dtype: binary"""
        
        features_yaml += """
  - name: start_time
    dtype: float64
  - name: duration
    dtype: float64
  - name: timestamp_range
    dtype: string"""
    else:
        features_yaml = """  features:
  - name: audio_filepath
    dtype: string
  - name: text
    dtype: string
  - name: duration
    dtype: float64"""
    
    # Build splits section
    splits_yaml = "  splits:\n"
    for split in splits:
        split_segments = stats.get(f'{split}_segments', 0)
        splits_yaml += f"  - name: {split}\n"
        splits_yaml += f"    num_examples: {split_segments}\n"
    
    # Create the full card content
    card_content = f"""---
license: cc-by-4.0
task_categories:
- automatic-speech-recognition
- audio-classification
- text-to-speech
language:
- en
tags:
- aviation
- atc
- air-traffic-control
- audio
- speech
size_categories:
- {size_category}
dataset_info:
{features_yaml}
{splits_yaml}---

# {dataset_name}

## Dataset Description

This dataset contains Air Traffic Control (ATC) communications extracted from YouTube videos, with transcriptions and {'audio files' if has_audio else 'metadata'}.

### Dataset Summary

- **Total Audio Segments**: {total_segments:,}
- **Total Videos**: {total_videos}
- **Total Duration**: ~{total_hours:.1f} hours
- **Total Words**: ~{total_words:,}
- **Language**: English (Aviation/ATC terminology)
- **Format**: {format_type.upper()}
- **Audio Included**: {'Yes' if has_audio else 'No'}

### Supported Tasks

- **Automatic Speech Recognition (ASR)**: Train models on aviation-specific speech
- **Audio Classification**: Classify types of ATC communications
- **Speaker Diarization**: Identify pilot vs. controller speech
- **Text-to-Speech**: Generate synthetic ATC communications
- **Language Modeling**: Train models on aviation terminology
- **Named Entity Recognition**: Extract callsigns, airports, altitudes

## Dataset Structure

### Data Splits

The dataset is split into the following subsets:

"""
    
    # Add split details
    for split in splits:
        split_videos = stats.get(f'{split}_videos', 0)
        split_segments = stats.get(f'{split}_segments', 0)
        card_content += f"- **{split.capitalize()}**: {split_videos} videos, {split_segments:,} segments\n"
    
    card_content += f"""
### Data Format

The dataset is provided in **{format_type.upper()}** format.

### Schema

Each record contains:

- **`audio_filename`**: WAV file name (e.g., "VIDEO_ID_seg001.wav")
- **`video_id`**: YouTube video ID (source)
- **`segment_num`**: Segment number within the video
- **`transcription`**: Preprocessed/normalized transcription (uppercase, standardized)
- **`original_transcription`**: Original transcription (before preprocessing)
"""
    
    if has_audio:
        card_content += "- **`audio`**: Binary audio data (WAV format)\n"
    
    card_content += """- **`start_time`**: Start time in seconds
- **`duration`**: Duration in seconds
- **`timestamp_range`**: Human-readable timestamp (e.g., "[00:05 - 00:11]")

## Usage

### Loading the Dataset

```python
from datasets import load_dataset

# Load the entire dataset
dataset = load_dataset("YOUR_USERNAME/YOUR_DATASET_NAME")

# Load specific split
train_dataset = load_dataset("YOUR_USERNAME/YOUR_DATASET_NAME", split="train")
```

### Example Record

```python
# Access first record
record = dataset['train'][0]

print(f"Transcription: {record['transcription']}")
print(f"Duration: {record['duration']} seconds")
"""
    
    if has_audio:
        card_content += """
# Access audio (if included)
audio_bytes = record['audio']
```
"""
    else:
        card_content += "```\n"
    
    card_content += """
## Data Collection

The data was collected from publicly available YouTube videos containing ATC communications. The extraction pipeline includes:

1. **Video Selection**: YouTube videos with ATC communications
2. **Subtitle Extraction**: Using Google Gemini 2.5 Pro API to extract on-screen text
3. **Audio Segmentation**: Segmenting audio based on extracted timestamps using FFmpeg
4. **Text Preprocessing**: Normalization, phonetic expansion, and standardization
5. **Quality Filtering**: Removing low-quality, non-English, or unintelligible segments

## Preprocessing

The transcriptions have been preprocessed with the following steps:

- **Uppercase Conversion**: All text converted to uppercase (ATC standard)
- **Phonetic Expansion**: Single letters expanded to NATO phonetic alphabet (e.g., "N" → "NOVEMBER")
- **Number Expansion**: Digits converted to words (e.g., "123" → "ONE TWO THREE")
- **Spelling Corrections**: Common ATC misspellings corrected
- **Punctuation Removal**: All punctuation removed for consistency
- **Tag Removal**: Non-critical speaker/context tags removed

The `original_transcription` field preserves the pre-processed text for reference.

## Limitations

- Audio quality varies depending on the source video
- Some segments may contain background noise or crosstalk
- Transcriptions are based on on-screen text, which may differ from actual audio
- Dataset is limited to English ATC communications
- Regional accents and terminology variations may be present

## Citation

If you use this dataset in your research, please cite:

```bibtex
@dataset{atc_communications,
  title={ATC Communications Dataset},
  author={ATC-Data-Extraction Contributors},
  year={2025},
  publisher={Hugging Face},
  howpublished={\\url{https://huggingface.co/datasets/YOUR_USERNAME/YOUR_DATASET_NAME}}
}
```

## License

This dataset is released under the **CC-BY-4.0** license.

## Contact

For questions, issues, or contributions, please visit the [GitHub repository](https://github.com/Ahmed-Ezzat20/ATC-Data-Extraction).
"""
    
    # Write to file
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(card_content)
    
    return str(output_path)


def upload_to_hub(
    repo_id: str,
    files_to_upload: list,
    repo_type: str = "dataset",
    private: bool = False,
    commit_message: str = "Upload dataset files"
) -> bool:
    """
    Upload files to Hugging Face Hub.
    
    Args:
        repo_id: Repository ID (e.g., "username/dataset-name")
        files_to_upload: List of file paths to upload
        repo_type: Type of repository ("dataset" or "model")
        private: Whether to create a private repository
        commit_message: Commit message for the upload
        
    Returns:
        True if successful, False otherwise
    """
    try:
        api = HfApi()
        
        # Check authentication
        if not check_authentication():
            print("[X] Error: Not authenticated with Hugging Face")
            print("    Please run: huggingface-cli login")
            return False
        
        print(f"\n{'='*70}")
        print(f"UPLOADING TO HUGGING FACE HUB")
        print(f"{'='*70}")
        print(f"Repository: {repo_id}")
        print(f"Type: {repo_type}")
        print(f"Private: {private}")
        print(f"Files to upload: {len(files_to_upload)}")
        
        # Create repository if it doesn't exist
        try:
            create_repo(
                repo_id=repo_id,
                repo_type=repo_type,
                private=private,
                exist_ok=True
            )
            print(f"[OK] Repository created/verified: {repo_id}")
        except HfHubHTTPError as e:
            if "already exists" not in str(e).lower():
                print(f"[X] Error creating repository: {e}")
                return False
        
        # Upload files
        print(f"\nUploading files...")
        for file_path in files_to_upload:
            file_path = Path(file_path)
            if not file_path.exists():
                print(f"  [!] Warning: File not found, skipping: {file_path}")
                continue
            
            try:
                api.upload_file(
                    path_or_fileobj=str(file_path),
                    path_in_repo=file_path.name,
                    repo_id=repo_id,
                    repo_type=repo_type,
                    commit_message=commit_message,
                )
                print(f"  [OK] Uploaded: {file_path.name}")
            except Exception as e:
                print(f"  [X] Error uploading {file_path.name}: {e}")
                return False
        
        print(f"\n{'='*70}")
        print(f"UPLOAD COMPLETE")
        print(f"{'='*70}")
        print(f"View your dataset at: https://huggingface.co/datasets/{repo_id}")
        
        return True
        
    except Exception as e:
        print(f"[X] Error during upload: {e}")
        return False
