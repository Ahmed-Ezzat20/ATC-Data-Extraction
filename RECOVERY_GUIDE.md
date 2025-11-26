# Audio Segment Recovery Guide

## Problem Summary

Your validation shows:
- **Expected segments**: 11,473 (from transcripts)
- **Actual audio files**: 9,990
- **Missing**: 1,483 audio segments

This means some audio segmentation failed or was interrupted during the original pipeline run.

## Quick Fix

### Option 1: Automatic Recovery (Recommended)

Use the automated recovery script:

```bash
# First, diagnose which videos are affected
python diagnose_missing_audio.py

# Then recover the missing segments
python recover_missing_audio.py
```

The recovery script will:
1. Identify all videos with missing segments
2. Re-segment from existing raw audio (if available)
3. Re-download and segment videos without raw audio
4. Skip segments that already exist

### Option 2: Manual Re-segmentation

If you want more control:

```bash
# Re-run just the segmentation phase
# This will skip existing segments and only create missing ones
python main.py --playlist-url 'YOUR_PLAYLIST_URL' \
               --skip-extraction \
               --skip-download \
               --skip-analysis
```

**Note**: This only works if raw audio files still exist in `data/raw_audio/`

### Option 3: Full Re-download

If raw audio is missing:

```bash
# Re-download and re-segment (skips extraction)
python main.py --playlist-url 'YOUR_PLAYLIST_URL' \
               --skip-extraction \
               --skip-analysis
```

## Step-by-Step Recovery

### Step 1: Diagnose the Issue

```bash
python diagnose_missing_audio.py --export-list
```

This will:
- Show which videos have missing segments
- Identify which videos have raw audio available
- Export detailed list to `missing_segments.txt`

**Example output:**
```
Missing Audio Segments Diagnostic
==================================================================
Total missing segments: 1,483
Videos with missing segments: 45
Videos that can be recovered (have raw audio): 30
Videos that need re-download (no raw audio): 15
```

### Step 2: Recover Missing Segments

#### If raw audio exists (faster):

```bash
python recover_missing_audio.py
```

This will:
- Re-segment from existing raw audio files
- Skip segments that already exist
- Only process videos with missing segments

#### If raw audio is missing:

The script will automatically re-download the videos that need it. You'll see:

```
[Phase 1] Re-segmenting from existing raw audio (30 videos)...
[Phase 2] Re-downloading and segmenting (15 videos)...
```

### Step 3: Validate Results

```bash
python validate_data.py
```

You should now see:
```
[OK] SYNC STATUS: All components synchronized
```

## Understanding the Issue

### Common Causes

1. **Pipeline interruption**: The original run was stopped before completion
2. **Disk space**: Ran out of space during segmentation
3. **FFmpeg errors**: Some segments failed to process
4. **Timeout**: Long videos timed out during segmentation
5. **Network issues**: Downloads were interrupted

### Why Transcripts and Audio Don't Match

The pipeline runs in phases:
1. **Phase 1**: Extract transcripts (completed - 11,473 segments)
2. **Phase 2**: Download audio and segment (partially completed - 9,990 segments)
3. **Phase 3**: Analysis (completed, based on transcripts)

Your Phase 2 was interrupted or failed for some videos, leaving 1,483 segments without audio files.

## Recovery Script Options

### Dry Run

See what would be done without actually doing it:

```bash
python recover_missing_audio.py --dry-run
```

### Force Re-download

Force re-download even if raw audio exists (use if raw audio is corrupted):

```bash
python recover_missing_audio.py --force-download
```

### Custom Data Directory

If your data is in a different location:

```bash
python recover_missing_audio.py --data-dir /path/to/data
```

## Troubleshooting

### Issue: "Raw audio not found"

**Solution**: Run with automatic download:
```bash
python recover_missing_audio.py
```
The script will automatically download missing videos.

### Issue: "FFmpeg error"

**Possible causes**:
- FFmpeg not installed
- Corrupted audio file
- Invalid timestamps

**Solution**:
1. Check FFmpeg installation: `ffmpeg -version`
2. Delete corrupted raw audio: `rm data/raw_audio/VIDEO_ID.webm`
3. Re-run recovery script

### Issue: "yt-dlp error"

**Possible causes**:
- Video no longer available
- Network issues
- yt-dlp needs update

**Solution**:
1. Update yt-dlp: `pip install -U yt-dlp`
2. Check video is still available on YouTube
3. Check network connection

### Issue: Recovery incomplete

If recovery script fails:

1. Check error messages in output
2. Run diagnostic with export:
   ```bash
   python diagnose_missing_audio.py --export-list
   ```
3. Review `missing_segments.txt` for specific failures
4. Process failed videos manually:
   ```python
   from segmentation.audio_segmenter import AudioSegmenter
   segmenter = AudioSegmenter()
   segmenter.process_video('VIDEO_ID', download=True)
   ```

## Prevention

To avoid this issue in future runs:

1. **Monitor disk space**: Ensure sufficient space before running
2. **Use checkpoints**: The pipeline supports resumption
3. **Check logs**: Review output for errors
4. **Validate incrementally**: Run validation after each phase
5. **Backup raw audio**: Keep raw audio until validation passes

## Performance Tips

### Faster Recovery

If you have raw audio files:
- Recovery is fast (just re-segmentation)
- Typically 1-2 seconds per video

If re-downloading needed:
- Slower (network dependent)
- Typically 10-30 seconds per video
- Consider running overnight for large recoveries

### Parallel Processing

For large recoveries, consider processing in batches:

```python
# Create custom script for parallel processing
from multiprocessing import Pool
from segmentation.audio_segmenter import AudioSegmenter

def process_video(video_id):
    segmenter = AudioSegmenter()
    return segmenter.process_video(video_id, download=False)

# Process multiple videos in parallel
with Pool(4) as pool:
    results = pool.map(process_video, video_ids)
```

## Verification

After recovery, verify synchronization:

```bash
python validate_data.py
```

Expected output:
```
[1/6] Validating Transcripts...
  [OK] 250 transcript files
  [OK] 11,473 total segments

[2/6] Validating Audio Segments...
  [OK] 11,473 audio segment files

[OK] SYNC STATUS: All components synchronized
```

## Getting Help

If you continue to have issues:

1. Export diagnostic information:
   ```bash
   python diagnose_missing_audio.py --export-list > diagnostic_output.txt
   ```

2. Check the logs for specific error messages

3. Verify dependencies:
   ```bash
   ffmpeg -version
   yt-dlp --version
   ```

4. Test with a single video:
   ```python
   python -c "
   from segmentation.audio_segmenter import AudioSegmenter
   s = AudioSegmenter()
   result = s.process_video('VIDEO_ID', download=True)
   print(f'Created {result[\"segments_created\"]} segments')
   "
   ```
