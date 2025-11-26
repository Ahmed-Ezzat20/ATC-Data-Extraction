#!/usr/bin/env python3
"""
Batched Upload to Hugging Face Hub

Uploads large datasets in batches to avoid timeouts.

Prerequisites:
    pip install huggingface_hub datasets

Usage:
    python upload_to_huggingface_batched.py --repo-id "username/dataset-name"
"""

import argparse
import sys
import time
from pathlib import Path
from huggingface_hub import HfApi, create_repo
from huggingface_hub.utils import HfHubHTTPError
import httpx


def check_authentication():
    """Check if user is authenticated with Hugging Face."""
    try:
        api = HfApi()
        api.whoami()
        return True
    except Exception:
        return False


def upload_files_in_batches(api, file_paths, repo_id, path_in_repo, batch_size=100, max_retries=3):
    """
    Upload files in batches with retry logic.

    Args:
        api: HfApi instance
        file_paths: List of file paths to upload
        repo_id: Repository ID
        path_in_repo: Path in repository
        batch_size: Number of files per batch
        max_retries: Maximum retry attempts per batch

    Returns:
        Number of successfully uploaded files
    """
    total_files = len(file_paths)
    uploaded = 0
    failed = []

    # Split into batches
    batches = [file_paths[i:i + batch_size] for i in range(0, total_files, batch_size)]

    print(f"Uploading {total_files} files in {len(batches)} batches of {batch_size}...")

    for batch_idx, batch in enumerate(batches, 1):
        print(f"\n[Batch {batch_idx}/{len(batches)}] Uploading {len(batch)} files...")

        for attempt in range(max_retries):
            try:
                # Upload each file in the batch
                for file_path in batch:
                    filename = file_path.name
                    remote_path = f"{path_in_repo}/{filename}" if path_in_repo else filename

                    api.upload_file(
                        path_or_fileobj=str(file_path),
                        path_in_repo=remote_path,
                        repo_id=repo_id,
                        repo_type="dataset"
                    )
                    uploaded += 1

                    # Show progress
                    if uploaded % 10 == 0:
                        print(f"  Progress: {uploaded}/{total_files} ({uploaded/total_files*100:.1f}%)")

                # Batch successful
                print(f"  [OK] Batch {batch_idx} completed ({len(batch)} files)")
                break

            except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                print(f"  [!] Timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 10
                    print(f"  Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    print(f"  [X] Batch {batch_idx} failed after {max_retries} attempts")
                    failed.extend(batch)

            except Exception as e:
                print(f"  [X] Error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    failed.extend(batch)

        # Small delay between batches to avoid rate limiting
        if batch_idx < len(batches):
            time.sleep(2)

    if failed:
        print(f"\n[!] {len(failed)} files failed to upload")
        failed_list_path = Path("failed_uploads.txt")
        with open(failed_list_path, 'w') as f:
            for file_path in failed:
                f.write(f"{file_path}\n")
        print(f"Failed files list saved to: {failed_list_path}")

    return uploaded


def upload_dataset_batched(repo_id, data_dir='data', private=False, batch_size=100):
    """
    Upload dataset to Hugging Face Hub in batches.

    Args:
        repo_id: Repository ID (username/dataset-name)
        data_dir: Data directory path
        private: Whether to create a private repository
        batch_size: Number of files per batch

    Returns:
        True if successful
    """
    api = HfApi()
    data_path = Path(data_dir)

    print("=" * 70)
    print("BATCHED UPLOAD TO HUGGING FACE")
    print("=" * 70)
    print(f"\nRepository: {repo_id}")
    print(f"Data directory: {data_path.absolute()}")
    print(f"Batch size: {batch_size}")

    # Create repo if needed
    try:
        api.repo_info(repo_id=repo_id, repo_type="dataset")
        print(f"\n[OK] Repository exists: {repo_id}")
    except HfHubHTTPError:
        print(f"\n[!] Creating repository: {repo_id}")
        create_repo(repo_id=repo_id, repo_type="dataset", private=private, exist_ok=True)
        print(f"[OK] Repository created")

    # Step 1: Upload README
    print("\n" + "-" * 70)
    print("Step 1: Uploading README...")

    # Import the create_dataset_card function from the original script
    from upload_to_huggingface import create_dataset_card

    readme_path = create_dataset_card(data_dir, 'README.md')
    api.upload_file(
        path_or_fileobj=readme_path,
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="dataset"
    )
    print("[OK] README uploaded")

    # Step 2: Upload CSV files
    print("\n" + "-" * 70)
    print("Step 2: Uploading CSV files...")

    csv_files = ['all_segments.csv', 'all_segments_detailed.csv']
    for csv_file in csv_files:
        csv_path = data_path / csv_file
        if csv_path.exists():
            print(f"  Uploading {csv_file}...")
            api.upload_file(
                path_or_fileobj=str(csv_path),
                path_in_repo=csv_file,
                repo_id=repo_id,
                repo_type="dataset"
            )
            print(f"  [OK] {csv_file}")

    # Step 3: Upload audio files in batches
    print("\n" + "-" * 70)
    print("Step 3: Uploading audio files (batched)...")

    audio_dir = data_path / 'audio_segments'
    if audio_dir.exists():
        audio_files = sorted(audio_dir.glob('*.wav'))
        print(f"Found {len(audio_files)} audio files")

        uploaded = upload_files_in_batches(
            api=api,
            file_paths=audio_files,
            repo_id=repo_id,
            path_in_repo="audio_segments",
            batch_size=batch_size
        )

        print(f"\n[OK] Audio upload complete: {uploaded}/{len(audio_files)} files")
    else:
        print("[X] audio_segments directory not found")
        return False

    # Step 4: Upload transcript files in batches
    print("\n" + "-" * 70)
    print("Step 4: Uploading transcript files (batched)...")

    transcripts_dir = data_path / 'transcripts'
    if transcripts_dir.exists():
        transcript_files = sorted([f for f in transcripts_dir.glob('*.json')
                                  if not f.stem.endswith('_raw')])
        print(f"Found {len(transcript_files)} transcript files")

        uploaded = upload_files_in_batches(
            api=api,
            file_paths=transcript_files,
            repo_id=repo_id,
            path_in_repo="transcripts",
            batch_size=batch_size
        )

        print(f"\n[OK] Transcripts upload complete: {uploaded}/{len(transcript_files)} files")

    # Step 5: Upload analysis report
    print("\n" + "-" * 70)
    print("Step 5: Uploading analysis report...")

    report_path = data_path / 'analysis_report.txt'
    if report_path.exists():
        api.upload_file(
            path_or_fileobj=str(report_path),
            path_in_repo="analysis_report.txt",
            repo_id=repo_id,
            repo_type="dataset"
        )
        print("[OK] analysis_report.txt")

    # Summary
    print("\n" + "=" * 70)
    print("UPLOAD COMPLETE")
    print("=" * 70)
    print(f"\nDataset URL: https://huggingface.co/datasets/{repo_id}")
    print("\nNext steps:")
    print("1. Visit your dataset on Hugging Face")
    print("2. Verify all files uploaded correctly")
    print(f"3. Load with: load_dataset('{repo_id}')")

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Upload dataset to Hugging Face Hub in batches"
    )
    parser.add_argument(
        '--repo-id',
        required=True,
        help='Repository ID (username/dataset-name)'
    )
    parser.add_argument(
        '--data-dir',
        default='data',
        help='Data directory (default: data)'
    )
    parser.add_argument(
        '--private',
        action='store_true',
        help='Create a private repository'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Number of files per batch (default: 50)'
    )

    args = parser.parse_args()

    # Check authentication
    print("Checking Hugging Face authentication...")
    if not check_authentication():
        print("\n[X] Not authenticated with Hugging Face")
        print("\nPlease login first:")
        print("  huggingface-cli login")
        return 1

    print("[OK] Authenticated")

    # Confirm
    print("\n" + "=" * 70)
    print(f"Ready to upload to: {args.repo_id}")
    print(f"Data directory: {args.data_dir}")
    print(f"Batch size: {args.batch_size} files")
    print(f"Private: {args.private}")
    print("\nThis will upload:")
    print("  - README.md")
    print("  - CSV files (2)")
    print("  - Audio files (~9,990 in batches)")
    print("  - Transcript files (~250 in batches)")
    print("  - Analysis report")
    print("=" * 70)

    response = input("\nProceed with upload? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Upload cancelled.")
        return 0

    # Upload
    success = upload_dataset_batched(
        repo_id=args.repo_id,
        data_dir=args.data_dir,
        private=args.private,
        batch_size=args.batch_size
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
