# Deprecated Scripts

This directory contains scripts that have been deprecated and replaced by the refactored `prepare_and_upload_dataset.py`.

## Deprecated Files

### `export_to_parquet.py`
**Replaced by**: `prepare_and_upload_dataset.py --no-split --no-upload`

**Reason**: Functionality has been integrated into the main dataset preparation script with the `--no-split` and `--no-upload` flags.

**Migration**:
```bash
# Old command
python export_to_parquet.py --data-dir data/preprocessed --audio-dir data/audio_segments --output dataset.parquet

# New command
python prepare_and_upload_dataset.py --data-dir data/preprocessed --audio-dir data/audio_segments --output-dir . --no-split --no-upload
```

### `upload_parquet_to_huggingface.py`
**Replaced by**: `prepare_and_upload_dataset.py`

**Reason**: Upload functionality has been integrated into the main dataset preparation script.

**Migration**:
```bash
# Old command
python upload_parquet_to_huggingface.py --repo-id "username/dataset-name" --parquet-file dataset.parquet

# New command (creates and uploads in one step)
python prepare_and_upload_dataset.py --repo-id "username/dataset-name" --data-dir data/preprocessed --audio-dir data/audio_segments
```

### `upload_to_huggingface_no_audio.py`
**Replaced by**: `prepare_and_upload_dataset.py --no-audio`

**Reason**: The `--no-audio` flag in the main script provides the same functionality.

**Migration**:
```bash
# Old command
python upload_to_huggingface_no_audio.py --repo-id "username/dataset-name"

# New command
python prepare_and_upload_dataset.py --repo-id "username/dataset-name" --no-audio --data-dir data/preprocessed --audio-dir data/audio_segments
```

## Why Were These Scripts Deprecated?

These scripts contained significant code duplication (~770 lines of redundant code across all files). The refactoring:

1. **Eliminated redundancy**: Moved shared functions to `src/dataset/` module
2. **Improved maintainability**: Single source of truth for core logic
3. **Enhanced flexibility**: Command-line flags provide more options
4. **Reduced bugs**: Consistent logic across all operations

## Backup Files

The directory also contains backup files from the refactoring:
- `prepare_and_upload_dataset_old.py`: Original version before refactoring
- `prepare_manifest_dataset_old.py`: Original version before refactoring

These are kept for reference and can be safely deleted after verifying the new scripts work correctly.

## Timeline

- **Deprecated**: December 2025
- **Removal**: These files may be removed in a future release
