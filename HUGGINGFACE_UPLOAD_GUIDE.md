# Hugging Face Upload Guide

Complete guide for uploading your ATC dataset to Hugging Face Hub.

## Prerequisites

### 1. Install Hugging Face Hub

```bash
pip install huggingface_hub datasets
```

### 2. Create a Hugging Face Account

If you don't have one:
1. Go to https://huggingface.co/join
2. Sign up for a free account

### 3. Get Your Access Token

1. Go to https://huggingface.co/settings/tokens
2. Click "New token"
3. Give it a name (e.g., "dataset-upload")
4. Select "write" permissions
5. Copy the token

### 4. Login via CLI

```bash
huggingface-cli login
```

Paste your token when prompted.

**Alternative**: Set environment variable:
```bash
export HF_TOKEN=your_token_here
```

## Quick Start

### Basic Upload

```bash
python upload_to_huggingface.py --repo-id "your-username/atc-dataset"
```

This will:
1. Create the repository if it doesn't exist
2. Generate a dataset card (README.md)
3. Upload CSV files
4. Upload all audio segments
5. Upload analysis report

### Upload as Private Dataset

```bash
python upload_to_huggingface.py --repo-id "your-username/atc-dataset" --private
```

### Custom Data Directory

```bash
python upload_to_huggingface.py --repo-id "your-username/atc-dataset" --data-dir /path/to/data
```

## What Gets Uploaded

### Files Uploaded:
1. **README.md** - Auto-generated dataset card with statistics
2. **all_segments.csv** - Basic audio-transcription pairs
3. **all_segments_detailed.csv** - Detailed metadata with timing info
4. **audio_segments/** - All WAV audio files (9,990+ files)
5. **analysis_report.txt** - Full analysis report (optional)

### Total Upload Size:
Depends on your audio files, typically:
- ~10GB for 10,000 segments
- Upload time: 30 minutes - 2 hours (depends on internet speed)

## Step-by-Step Process

### Step 1: Ensure Data is Clean

Before uploading, make sure your data is synchronized:

```bash
python validate_data.py
```

You should see: `[OK] SYNC STATUS: All components synchronized`

If not, run cleanup first:
```bash
python cleanup_missing_segments.py --backup
```

### Step 2: Choose Repository Name

Pick a descriptive name:
- `username/atc-communications`
- `username/aviation-speech-dataset`
- `username/air-traffic-control-audio`

### Step 3: Upload

```bash
python upload_to_huggingface.py --repo-id "your-username/dataset-name"
```

The script will:
1. Check authentication ✓
2. Create repository (if needed) ✓
3. Generate dataset card ✓
4. Upload files with progress ✓
5. Provide dataset URL ✓

### Step 4: Verify Upload

Visit your dataset:
```
https://huggingface.co/datasets/your-username/dataset-name
```

Check:
- [ ] README displays correctly
- [ ] CSV files are accessible
- [ ] Audio files are in `audio_segments/` folder
- [ ] File count matches your local data

## Using Your Dataset

### Load with Datasets Library

```python
from datasets import load_dataset

# Load the entire dataset
dataset = load_dataset("your-username/dataset-name")

# Load specific split
dataset = load_dataset("your-username/dataset-name", split="train")
```

### Create Custom Loading Script (Advanced)

For automatic audio loading, create `dataset_name.py`:

```python
import datasets
from pathlib import Path

class ATCDataset(datasets.GeneratorBasedBuilder):
    def _info(self):
        return datasets.DatasetInfo(
            features=datasets.Features({
                "audio": datasets.Audio(sampling_rate=44100),
                "transcription": datasets.Value("string"),
                "video_id": datasets.Value("string"),
                "segment_num": datasets.Value("int32"),
                "duration": datasets.Value("float32"),
            })
        )

    def _split_generators(self, dl_manager):
        # Download CSV and audio files
        csv_path = dl_manager.download("all_segments_detailed.csv")
        audio_dir = dl_manager.download("audio_segments")

        return [
            datasets.SplitGenerator(
                name=datasets.Split.TRAIN,
                gen_kwargs={"csv_path": csv_path, "audio_dir": audio_dir}
            )
        ]

    def _generate_examples(self, csv_path, audio_dir):
        import pandas as pd
        df = pd.read_csv(csv_path)

        for idx, row in df.iterrows():
            audio_path = Path(audio_dir) / row["audio_filename"]

            yield idx, {
                "audio": str(audio_path),
                "transcription": row["transcription"],
                "video_id": row["video_id"],
                "segment_num": row["segment_num"],
                "duration": row["duration"],
            }
```

## Troubleshooting

### Issue: "Not authenticated"

**Solution**:
```bash
huggingface-cli login
```

### Issue: "Repository already exists"

**Solutions**:
1. Use existing repo (script will upload to it)
2. Choose different name
3. Delete old repo from Hugging Face website first

### Issue: Upload interrupted

**Solution**:
Re-run the script. It will:
- Skip already uploaded files
- Resume from where it stopped
- Complete the upload

### Issue: Slow upload

**Causes**:
- Large number of files (9,990+ audio segments)
- Slow internet connection
- Hugging Face server load

**Solutions**:
- Run overnight
- Use faster internet connection
- Upload in batches (advanced)

### Issue: "File too large"

Hugging Face has file size limits:
- Individual file: 50GB (should be fine for audio)
- Total repo: No limit for datasets

If you have issues:
- Check individual audio file sizes
- Compress audio if needed (reduce sample rate/bit depth)

## Advanced Options

### Upload Specific Files Only

Modify the script to upload only what you need:

```python
# Upload only CSV files (no audio)
python upload_to_huggingface.py --repo-id "username/dataset" --no-audio
```

### Batch Upload (For Large Datasets)

For very large datasets, upload in batches:

```python
# Split audio files into folders
# batch_1, batch_2, etc.
# Upload each batch separately
```

### Update Existing Dataset

To update files in an existing dataset:

```bash
python upload_to_huggingface.py --repo-id "username/dataset"
```

The script will overwrite existing files with new versions.

## Making Your Dataset Public

### Initial Upload as Private

```bash
python upload_to_huggingface.py --repo-id "username/dataset" --private
```

### Later Make Public

1. Go to dataset settings: https://huggingface.co/datasets/username/dataset/settings
2. Scroll to "Change repository visibility"
3. Click "Make public"

## Best Practices

### 1. Clean Data First

Always validate before uploading:
```bash
python validate_data.py
```

### 2. Test with Small Sample

Upload a small test dataset first:
- Create a test dataset with 10-20 files
- Verify everything works
- Then upload full dataset

### 3. Good Dataset Card

The script auto-generates a README, but you can customize it:
- Add more context about data collection
- Include example use cases
- Add limitations and biases
- Provide citation information

### 4. Choose Appropriate License

Default is CC-BY-4.0. Consider:
- CC0 (public domain)
- CC-BY-SA (share-alike)
- MIT
- Custom license

Update in README.md header:
```yaml
---
license: cc-by-4.0
---
```

## Dataset Card Customization

After upload, edit your README.md to add:

### Usage Examples
```python
# Add specific examples for your domain
from datasets import load_dataset
dataset = load_dataset("username/dataset-name")

# Show how to use for ASR training
# Show how to filter by duration
# Show how to extract aviation terms
```

### Known Issues
Document any data quality issues, limitations, or biases.

### Changelog
Keep track of dataset versions:
```
## Changelog

### v1.1 (2024-01-15)
- Added 500 new segments
- Fixed transcription errors in 50 files
- Updated metadata format

### v1.0 (2024-01-01)
- Initial release
- 9,990 audio segments
```

## Cost

Hugging Face Hub is **free** for public datasets with no size limits!

Private datasets:
- Free tier: 100GB
- Pro subscription: Unlimited ($9/month)

## Support

If you encounter issues:

1. Check Hugging Face docs: https://huggingface.co/docs/hub
2. Hugging Face forum: https://discuss.huggingface.co/
3. GitHub issues for this script

## Next Steps After Upload

1. **Share your dataset**: Post on Twitter, Reddit, forums
2. **Create a model card**: Train a model and share it
3. **Write a blog post**: Document your process
4. **Collect feedback**: Improve based on user feedback
5. **Version control**: Update dataset as you collect more data

---

**Ready to upload?**

```bash
# Login
huggingface-cli login

# Upload
python upload_to_huggingface.py --repo-id "your-username/atc-dataset"
```

Your dataset will be live at:
`https://huggingface.co/datasets/your-username/atc-dataset`
