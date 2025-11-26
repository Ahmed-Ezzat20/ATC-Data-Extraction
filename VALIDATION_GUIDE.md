# Data Validation Guide

## Overview

The `validate_data.py` script validates that all data components are properly synchronized across the ATC Data Extraction pipeline phases.

## Usage

### Basic Validation

```bash
python validate_data.py
```

### Custom Data Directory

```bash
python validate_data.py --data-dir /path/to/data
```

## What It Validates

### Phase 1: Transcripts
- Checks that transcript JSON files exist in `data/transcripts/`
- Validates JSON structure (video_id, segments, etc.)
- Counts total videos and segments
- Verifies each segment has required fields (segment_num, start_time, duration, transcript)

### Phase 2: Audio Segments
- Verifies audio WAV files exist in `data/audio_segments/`
- Ensures each transcript segment has a corresponding audio file
- Checks file naming: `{video_id}_seg{segment_num:03d}.wav`
- Detects orphaned audio files (no matching transcript)
- Counts raw audio files in `data/raw_audio/`

### Phase 3: Analysis Outputs
- Validates CSV files:
  - `all_segments.csv` (audio_filename, transcription)
  - `all_segments_detailed.csv` (includes video_id, timing info)
- Verifies row counts match transcript segments
- Checks `analysis_report.txt` exists with expected sections
- Validates visualization files in `data/visualizations/`

## Expected Output

### With Valid Data

```
======================================================================
DATA SYNCHRONIZATION VALIDATOR
======================================================================
Data directory: C:\Work\GenArabia\ATC-Data-Extraction\data

[1/6] Validating Transcripts...
----------------------------------------------------------------------
  [OK] 217 transcript files
  [OK] 9,990 total segments

[2/6] Validating Audio Segments...
----------------------------------------------------------------------
  [OK] 9,990 audio segment files

[3/6] Validating CSV Outputs...
----------------------------------------------------------------------
  [OK] all_segments.csv: 9,990 rows
  [OK] all_segments_detailed.csv: 9,990 rows

[4/6] Validating Analysis Report...
----------------------------------------------------------------------
  [OK] analysis_report.txt exists and is valid

[5/6] Validating Raw Audio Files...
----------------------------------------------------------------------
  [OK] 217 raw audio files

[6/6] Validating Visualizations...
----------------------------------------------------------------------
  [OK] 5 visualization files

======================================================================
VALIDATION SUMMARY
======================================================================

Data Components:
  Videos: 217
  Transcript segments: 9,990
  Audio segments: 9,990

[OK] SYNC STATUS: All components synchronized

[i] INFO:
  - Found 217 transcript files
  - Total segments in transcripts: 9,990
  - Found 9,990 audio segment files
  - all_segments.csv: 9,990 rows
  - all_segments_detailed.csv: 9,990 rows
  - Analysis report is valid
  - Found 217 raw audio files
  - Found 5 visualization files

======================================================================
```

### With Missing/Incomplete Data

```
======================================================================
DATA SYNCHRONIZATION VALIDATOR
======================================================================
Data directory: C:\Work\GenArabia\ATC-Data-Extraction\data

[1/6] Validating Transcripts...
----------------------------------------------------------------------

[2/6] Validating Audio Segments...
----------------------------------------------------------------------

[3/6] Validating CSV Outputs...
----------------------------------------------------------------------
  ! all_segments.csv not found
  ! all_segments_detailed.csv not found

[4/6] Validating Analysis Report...
----------------------------------------------------------------------
  ! analysis_report.txt not found

[5/6] Validating Raw Audio Files...
----------------------------------------------------------------------
  ! No raw audio files

[6/6] Validating Visualizations...
----------------------------------------------------------------------
  ! Visualizations directory not found

======================================================================
VALIDATION SUMMARY
======================================================================

Data Components:
  Videos: 0
  Transcript segments: 0
  Audio segments: 0

[ERROR] SYNC STATUS: Components NOT synchronized

[X] ERRORS (1):
  - No transcript files found

! WARNINGS (6):
  - No audio segment files found
  - CSV file not found: all_segments.csv
  - CSV file not found: all_segments_detailed.csv
  - Analysis report not found
  - No raw audio files found
  - Visualizations directory does not exist

======================================================================
```

## Exit Codes

- **0**: Validation successful, all components synchronized
- **1**: Validation failed, errors or inconsistencies found

## Common Issues and Solutions

### Issue: No transcript files found
**Solution**: Run Phase 1 of the pipeline:
```bash
python main.py --playlist-url "YOUR_URL"
```

### Issue: Missing audio files for transcript segments
**Solution**: Re-run Phase 2 of the pipeline:
```bash
python main.py --playlist-url "YOUR_URL" --skip-extraction
```

### Issue: CSV files not found
**Solution**: Re-run Phase 3 of the pipeline:
```bash
python main.py --playlist-url "YOUR_URL" --skip-extraction --skip-segmentation
```

### Issue: Row count mismatch in CSV files
**Solution**: Delete CSV files and re-run Phase 3:
```bash
rm data/all_segments*.csv
python main.py --playlist-url "YOUR_URL" --skip-extraction --skip-segmentation
```

### Issue: Orphaned audio files
**Cause**: Audio files exist without corresponding transcripts
**Solution**: This usually happens when transcripts are deleted but audio isn't. Either:
1. Delete the audio files manually
2. Re-run the full pipeline to regenerate both

## Validating Data from Another Machine

If you've copied data from another machine:

1. Copy the entire `data/` directory:
   ```bash
   # From source machine
   tar -czf atc-data.tar.gz data/

   # To target machine
   tar -xzf atc-data.tar.gz
   ```

2. Run validation:
   ```bash
   python validate_data.py
   ```

3. Expected results based on your other machine's output:
   - Videos: 217 or 250 (discrepancy in your output)
   - Transcript segments: ~9,990 to 11,473
   - Audio segments: Should match transcript segments
   - Total duration: ~1,004.9 minutes
   - Total words: ~116,431
   - Unique words: ~5,082

## Data Integrity Checks

The validator performs these integrity checks:

1. **Structural Integrity**: JSON files are valid and well-formed
2. **Referential Integrity**: Each segment in transcripts has corresponding audio
3. **Count Integrity**: CSV rows match transcript segments
4. **Content Integrity**: Required fields present in all records
5. **Completeness**: All expected output files exist

## Automated Validation

Include validation in your pipeline script:

```bash
#!/bin/bash
set -e

# Run pipeline
python main.py --playlist-url "$PLAYLIST_URL"

# Validate results
python validate_data.py

if [ $? -eq 0 ]; then
    echo "Pipeline completed successfully and data is synchronized"
else
    echo "Pipeline completed but data validation failed"
    exit 1
fi
```

## Getting Help

If validation fails and you can't resolve the issues:

1. Check the error messages carefully
2. Review the pipeline logs
3. Ensure all pipeline phases completed without errors
4. Try re-running the failed phase with verbose logging
5. Check disk space and file permissions
