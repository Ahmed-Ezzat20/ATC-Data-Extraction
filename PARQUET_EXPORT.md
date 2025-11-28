# Parquet Export Guide

This guide explains how to export your ATC dataset to Parquet format with embedded audio files.

## What is Parquet?

Parquet is a columnar storage format optimized for:
- **Efficient storage**: Compression reduces file size by 60-70%
- **Fast querying**: Columnar format allows reading specific columns only
- **Wide compatibility**: Works with pandas, PyArrow, Apache Spark, TensorFlow, PyTorch
- **Self-contained**: Single file with all data (metadata + audio)

## Quick Start

### 1. Install Dependencies

```bash
pip install pyarrow>=14.0.0
```

### 2. Export Dataset

```bash
# Export preprocessed data with audio
python export_to_parquet.py \
    --data-dir data/preprocessed \
    --audio-dir data/audio_segments \
    --output atc_dataset.parquet

# Export metadata only (no audio files)
python export_to_parquet.py \
    --data-dir data/preprocessed \
    --output atc_metadata.parquet \
    --no-audio
```

### 3. Load and Use

```bash
# Explore the dataset
python examples/load_parquet_example.py atc_dataset.parquet
```

## Export Options

### Command-Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--data-dir` | `data/preprocessed` | Directory with preprocessed transcripts |
| `--audio-dir` | `data/audio_segments` | Directory with WAV audio files |
| `--output` | `atc_dataset.parquet` | Output Parquet file path |
| `--no-audio` | False | Export metadata only (exclude audio) |

### Examples

```bash
# Full export with audio
python export_to_parquet.py \
    --data-dir data/preprocessed \
    --audio-dir data/audio_segments \
    --output full_dataset.parquet

# Metadata only (for text-only tasks)
python export_to_parquet.py \
    --data-dir data/preprocessed \
    --output metadata_only.parquet \
    --no-audio

# Export from original (non-preprocessed) data
python export_to_parquet.py \
    --data-dir data/transcripts \
    --audio-dir data/audio_segments \
    --output original_dataset.parquet
```

## Parquet Schema

Each record in the Parquet file contains:

| Column | Type | Description |
|--------|------|-------------|
| `audio_filename` | string | WAV file name (e.g., "VIDEO_ID_seg001.wav") |
| `video_id` | string | YouTube video ID |
| `segment_num` | int64 | Segment number within the video |
| `transcription` | string | Final/preprocessed transcription |
| `original_transcription` | string | Original transcription (before preprocessing) |
| `audio` | binary | WAV file bytes (if audio included) |
| `start_time` | float64 | Start time in seconds |
| `duration` | float64 | Segment duration in seconds |
| `timestamp_range` | string | Human-readable timestamp (e.g., "[00:05 - 00:11]") |

## Loading and Using Parquet Files

### Python (pandas)

```python
import pandas as pd

# Load entire dataset
df = pd.read_parquet('atc_dataset.parquet')

print(f"Total records: {len(df):,}")
print(df.head())

# Access specific columns
transcriptions = df['transcription'].tolist()
video_ids = df['video_id'].unique()

# Filter by video
video_data = df[df['video_id'] == 'VIDEO_ID']

# Search transcriptions
matches = df[df['transcription'].str.contains('TOWER', na=False)]
```

### Python (PyArrow)

```python
import pyarrow.parquet as pq

# Load table
table = pq.read_table('atc_dataset.parquet')

# Convert to pandas
df = table.to_pandas()

# Read specific columns only (more efficient)
table = pq.read_table('atc_dataset.parquet',
                      columns=['transcription', 'audio_filename'])
```

### Extracting Audio

```python
import pandas as pd

# Load dataset
df = pd.read_parquet('atc_dataset.parquet')

# Extract single audio file
row = df.iloc[0]
with open(f"extracted_{row['audio_filename']}", 'wb') as f:
    f.write(row['audio'])

# Extract all audio for a video
video_data = df[df['video_id'] == 'VIDEO_ID']
for _, row in video_data.iterrows():
    with open(row['audio_filename'], 'wb') as f:
        f.write(row['audio'])
```

### Using with ML Frameworks

#### PyTorch Dataset

```python
import torch
from torch.utils.data import Dataset
import pandas as pd
import io
import soundfile as sf

class ATCDataset(Dataset):
    def __init__(self, parquet_file):
        self.df = pd.read_parquet(parquet_file)

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]

        # Load audio from bytes
        audio_bytes = io.BytesIO(row['audio'])
        audio, sr = sf.read(audio_bytes)

        return {
            'audio': torch.tensor(audio, dtype=torch.float32),
            'transcription': row['transcription'],
            'video_id': row['video_id']
        }

# Usage
dataset = ATCDataset('atc_dataset.parquet')
dataloader = torch.utils.data.DataLoader(dataset, batch_size=32, shuffle=True)
```

#### TensorFlow Dataset

```python
import tensorflow as tf
import pandas as pd
import io

def load_atc_dataset(parquet_file):
    df = pd.read_parquet(parquet_file)

    def generator():
        for _, row in df.iterrows():
            # Decode audio
            audio_bytes = row['audio']
            # Process audio here...

            yield {
                'audio': audio_data,
                'transcription': row['transcription'],
            }

    return tf.data.Dataset.from_generator(
        generator,
        output_signature={
            'audio': tf.TensorSpec(shape=(None,), dtype=tf.float32),
            'transcription': tf.TensorSpec(shape=(), dtype=tf.string),
        }
    )

# Usage
dataset = load_atc_dataset('atc_dataset.parquet')
dataset = dataset.batch(32).prefetch(tf.data.AUTOTUNE)
```

## Performance Tips

### Memory Efficiency

For large datasets, use chunked reading:

```python
import pandas as pd

# Read in chunks
chunk_size = 1000
for chunk in pd.read_parquet('atc_dataset.parquet',
                              iterator=True,
                              chunk_size=chunk_size):
    # Process chunk
    process_batch(chunk)
```

### Column Selection

Read only needed columns:

```python
# Read only text columns (faster than loading audio)
df = pd.read_parquet('atc_dataset.parquet',
                     columns=['transcription', 'video_id', 'audio_filename'])
```

### Filtering During Load

Use PyArrow filters for efficient filtering:

```python
import pyarrow.parquet as pq
import pyarrow as pa

# Filter during read (more efficient than loading then filtering)
table = pq.read_table(
    'atc_dataset.parquet',
    filters=[('video_id', '=', 'SPECIFIC_VIDEO_ID')]
)
df = table.to_pandas()
```

## File Size Considerations

### Typical File Sizes

For reference, with 10,000 segments (~5 seconds each):
- **Audio segments (WAV)**: ~2 GB
- **Parquet with audio**: ~700 MB (65% compression)
- **Parquet metadata only**: ~2 MB

### Compression

The export uses Snappy compression by default, which provides:
- Fast compression/decompression
- Good compression ratio (typically 60-70%)
- Wide compatibility

## Hugging Face Integration

### Upload to Hugging Face

Use the included upload script (recommended):

```bash
# Login first
huggingface-cli login

# Upload dataset
python upload_parquet_to_huggingface.py \
    --repo-id "username/atc-dataset" \
    --parquet-file atc_dataset.parquet

# For private repository
python upload_parquet_to_huggingface.py \
    --repo-id "username/atc-dataset" \
    --parquet-file atc_dataset.parquet \
    --private
```

The script will:
- Create the repository if it doesn't exist
- Auto-generate a comprehensive dataset card (README.md)
- Upload the Parquet file as `data/train.parquet`
- Display usage examples

### Manual Upload (Python)

```python
from huggingface_hub import HfApi

api = HfApi()

# Upload single Parquet file
api.upload_file(
    path_or_fileobj="atc_dataset.parquet",
    path_in_repo="data/train.parquet",
    repo_id="username/atc-dataset",
    repo_type="dataset"
)
```

### Load from Hugging Face

```python
# Method 1: Using datasets library
from datasets import load_dataset

dataset = load_dataset("username/atc-dataset")
print(dataset['train'][0])

# Method 2: Using pandas with manual download
import pandas as pd
from huggingface_hub import hf_hub_download

file_path = hf_hub_download(
    repo_id="username/atc-dataset",
    filename="data/train.parquet",
    repo_type="dataset"
)

df = pd.read_parquet(file_path)
```

## Troubleshooting

### Missing Audio Files

If some audio files are missing:
```
[!] Warning: 150 audio files not found
```

Solutions:
- Check that `--audio-dir` points to the correct directory
- Ensure audio segmentation was completed successfully
- Use `--no-audio` if you only need metadata

### Memory Issues

If export runs out of memory with large datasets:

```bash
# Export in batches (not implemented yet, but can be added)
# Or export metadata only, then add audio separately
python export_to_parquet.py --data-dir data/preprocessed --no-audio
```

### Corrupted Audio

If audio doesn't play correctly:
- Verify original WAV files are valid
- Check that audio wasn't modified during preprocessing
- Ensure correct audio directory path

## Best Practices

1. **Always backup** original data before export
2. **Verify export** by loading and checking a few samples
3. **Use metadata-only** for text-only tasks (much smaller file)
4. **Keep original WAVs** as source of truth
5. **Test loading** before distributing dataset
6. **Document preprocessing** steps in dataset card

## Advanced Usage

### Custom Schema

Modify `export_to_parquet.py` to add custom columns:

```python
# Add custom metadata
segment_data = {
    # ... existing fields ...
    'custom_field': compute_custom_value(segment),
}
```

### Partitioning

For very large datasets, consider partitioning by video:

```python
import pyarrow.parquet as pq

# Save partitioned dataset
pq.write_to_dataset(
    table,
    root_path='dataset_partitioned',
    partition_cols=['video_id']
)
```

### Convert to Other Formats

```python
import pandas as pd

# Load Parquet
df = pd.read_parquet('atc_dataset.parquet')

# Convert to CSV (without audio)
df[['audio_filename', 'transcription', 'video_id']].to_csv('dataset.csv', index=False)

# Convert to JSON
df.to_json('dataset.json', orient='records', lines=True)
```

## Example Workflow

Complete workflow from data to ML-ready Parquet:

```bash
# 1. Extract and preprocess
python main.py --playlist-url "PLAYLIST_URL"
python preprocess_data.py --data-dir data --output-dir data/preprocessed

# 2. Export to Parquet
python export_to_parquet.py \
    --data-dir data/preprocessed \
    --audio-dir data/audio_segments \
    --output atc_final.parquet

# 3. Verify export
python examples/load_parquet_example.py atc_final.parquet

# 4. Use in training
python train_model.py --dataset atc_final.parquet
```

## Support

For issues or questions:
- Check error messages in console output
- Verify all directories exist and contain expected files
- Ensure dependencies are installed: `pip install -r requirements.txt`
- Review statistics in export summary
