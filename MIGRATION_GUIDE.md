# Migration Guide: Refactored Dataset Scripts

## Overview

The ATC-Data-Extraction repository has been refactored to eliminate code duplication and improve maintainability. This guide helps you migrate from the old scripts to the new unified workflow.

## What Changed?

### New Structure

A new centralized module has been created at `src/dataset/` containing:
- `utils.py`: Shared functions for loading transcripts, splitting datasets, and handling audio
- `huggingface.py`: Utilities for Hugging Face authentication, dataset card generation, and uploads
- `__init__.py`: Module exports

### Deprecated Scripts

The following scripts have been moved to the `deprecated/` directory:
1. `export_to_parquet.py`
2. `upload_parquet_to_huggingface.py`
3. `upload_to_huggingface_no_audio.py`

### Refactored Scripts

The following scripts have been refactored to use the new centralized module:
1. `prepare_and_upload_dataset.py` - Enhanced with new flags
2. `prepare_manifest_dataset.py` - Now uses shared utilities

## Migration Examples

### Example 1: Export Single Parquet File

**Old Command:**
```bash
python export_to_parquet.py \
    --data-dir data/preprocessed \
    --audio-dir data/audio_segments \
    --output dataset.parquet
```

**New Command:**
```bash
python prepare_and_upload_dataset.py \
    --data-dir data/preprocessed \
    --audio-dir data/audio_segments \
    --output-dir . \
    --no-split \
    --no-upload
```

**Output:** `dataset_output/dataset.parquet`

### Example 2: Upload Parquet to Hugging Face

**Old Command:**
```bash
# Step 1: Export
python export_to_parquet.py \
    --data-dir data/preprocessed \
    --audio-dir data/audio_segments \
    --output dataset.parquet

# Step 2: Upload
python upload_parquet_to_huggingface.py \
    --repo-id "username/atc-dataset" \
    --parquet-file dataset.parquet
```

**New Command (One Step):**
```bash
python prepare_and_upload_dataset.py \
    --repo-id "username/atc-dataset" \
    --data-dir data/preprocessed \
    --audio-dir data/audio_segments
```

**Benefits:** Combines both steps into one, automatically generates dataset card, and handles splits.

### Example 3: Upload Without Audio

**Old Command:**
```bash
python upload_to_huggingface_no_audio.py \
    --repo-id "username/atc-dataset" \
    --data-dir data/preprocessed
```

**New Command:**
```bash
python prepare_and_upload_dataset.py \
    --repo-id "username/atc-dataset" \
    --data-dir data/preprocessed \
    --audio-dir data/audio_segments \
    --no-audio
```

### Example 4: Create Manifest Format

**Old Command:**
```bash
python prepare_manifest_dataset.py \
    --data-dir data/preprocessed \
    --audio-dir data/audio_segments \
    --output-dir dataset_manifest
```

**New Command (No Change):**
```bash
python prepare_manifest_dataset.py \
    --data-dir data/preprocessed \
    --audio-dir data/audio_segments \
    --output-dir dataset_manifest
```

**Note:** The command is the same, but the script now uses shared utilities internally.

## New Features

### Unified Workflow

The refactored `prepare_and_upload_dataset.py` now supports:

1. **Single File Export** (replaces `export_to_parquet.py`):
   ```bash
   python prepare_and_upload_dataset.py --no-split --no-upload
   ```

2. **Split Dataset Export** (default):
   ```bash
   python prepare_and_upload_dataset.py --no-upload
   ```

3. **Export and Upload** (replaces `upload_parquet_to_huggingface.py`):
   ```bash
   python prepare_and_upload_dataset.py --repo-id "username/dataset"
   ```

4. **Export Without Audio** (replaces `upload_to_huggingface_no_audio.py`):
   ```bash
   python prepare_and_upload_dataset.py --repo-id "username/dataset" --no-audio
   ```

### Command-Line Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--format {parquet,manifest}` | Output format | `parquet` |
| `--no-audio` | Export without embedding audio | Include audio |
| `--no-split` | Export as single file | Split into train/val/test |
| `--no-upload` | Skip Hugging Face upload | Upload if `--repo-id` provided |
| `--train-ratio` | Training set ratio | 0.95 |
| `--val-ratio` | Validation set ratio | 0.025 |
| `--test-ratio` | Test set ratio | 0.025 |
| `--random-seed` | Random seed for splitting | 42 |
| `--private` | Create private HF repository | Public |

## Benefits of the Refactoring

1. **Less Code Duplication**: Eliminated ~770 lines of redundant code
2. **Single Source of Truth**: Shared functions in `src/dataset/` module
3. **More Flexible**: Command-line flags provide more options
4. **Easier Maintenance**: Bug fixes and improvements only need to be made once
5. **Better Consistency**: All operations use the same underlying logic

## Backward Compatibility

The deprecated scripts are still available in the `deprecated/` directory and will continue to work. However, they are no longer maintained and may be removed in a future release.

## Need Help?

If you encounter any issues during migration:
1. Check the examples in this guide
2. Review the updated `CLAUDE.md` documentation
3. Run scripts with `--help` flag to see all options
4. Open an issue on GitHub if you need assistance

## Timeline

- **Refactoring Date**: December 2025
- **Deprecation Period**: 6 months
- **Planned Removal**: June 2026

We recommend migrating to the new scripts as soon as possible to benefit from the improvements and ensure compatibility with future updates.
