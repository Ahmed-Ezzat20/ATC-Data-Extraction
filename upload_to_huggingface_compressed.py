#!/usr/bin/env python3
"""
Upload ATC Dataset with Compressed Audio

Compresses audio files into archives for faster upload to Hugging Face.

Prerequisites:
    pip install huggingface_hub datasets

Usage:
    python upload_to_huggingface_compressed.py --repo-id "username/dataset-name"
"""

import argparse
import sys
import zipfile
import shutil
from pathlib import Path
from huggingface_hub import HfApi, create_repo
from huggingface_hub.utils import HfHubHTTPError


def check_authentication():
    """Check if user is authenticated with Hugging Face."""
    try:
        api = HfApi()
        api.whoami()
        return True
    except Exception:
        return False


def create_audio_archives(audio_dir, output_dir, files_per_archive=1000):
    """
    Create zip archives from audio files.

    Args:
        audio_dir: Directory containing audio files
        output_dir: Output directory for archives
        files_per_archive: Number of files per archive

    Returns:
        List of created archive paths
    """
    audio_path = Path(audio_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    audio_files = sorted(audio_path.glob('*.wav'))
    total_files = len(audio_files)

    print(f"Creating archives from {total_files} audio files...")
    print(f"Files per archive: {files_per_archive}")

    # Calculate number of archives needed
    num_archives = (total_files + files_per_archive - 1) // files_per_archive
    print(f"Will create {num_archives} archive(s)")

    archives = []

    for i in range(num_archives):
        start_idx = i * files_per_archive
        end_idx = min(start_idx + files_per_archive, total_files)
        batch = audio_files[start_idx:end_idx]

        archive_name = f"audio_segments_part{i+1:02d}.zip"
        archive_path = output_path / archive_name

        print(f"\n[{i+1}/{num_archives}] Creating {archive_name}...")
        print(f"  Files: {len(batch)} ({start_idx+1} to {end_idx})")

        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for j, audio_file in enumerate(batch):
                zipf.write(audio_file, arcname=audio_file.name)
                if (j + 1) % 100 == 0:
                    print(f"  Progress: {j+1}/{len(batch)}")

        archive_size_mb = archive_path.stat().st_size / (1024 * 1024)
        print(f"  [OK] {archive_name} ({archive_size_mb:.1f} MB)")
        archives.append(archive_path)

    total_size_mb = sum(p.stat().st_size for p in archives) / (1024 * 1024)
    print(f"\n[OK] Created {len(archives)} archives, total size: {total_size_mb:.1f} MB")

    return archives


def create_extraction_script():
    """Create a Python script for users to extract archives."""
    script_content = '''#!/usr/bin/env python3
"""
Extract Audio Archives

Extracts compressed audio archives from the dataset.

Usage:
    python extract_audio.py
"""

import zipfile
from pathlib import Path
from huggingface_hub import hf_hub_download

def extract_audio_archives(repo_id, output_dir="audio_segments"):
    """
    Download and extract audio archives from Hugging Face.

    Args:
        repo_id: Repository ID (username/dataset-name)
        output_dir: Output directory for extracted files
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Extracting audio files from {repo_id}...")
    print(f"Output directory: {output_path.absolute()}")

    # Find all archive parts
    part = 1
    total_extracted = 0

    while True:
        archive_name = f"audio_segments_part{part:02d}.zip"

        try:
            print(f"\\n[Part {part}] Downloading {archive_name}...")
            archive_path = hf_hub_download(
                repo_id=repo_id,
                filename=archive_name,
                repo_type="dataset"
            )

            print(f"  Extracting...")
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                zipf.extractall(output_path)
                extracted = len(zipf.namelist())
                total_extracted += extracted
                print(f"  [OK] Extracted {extracted} files")

            part += 1

        except Exception as e:
            if part == 1:
                print(f"  [X] Error: {e}")
                return False
            else:
                # No more parts
                break

    print(f"\\n[OK] Total extracted: {total_extracted} audio files")
    print(f"Location: {output_path.absolute()}")
    return True

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python extract_audio.py REPO_ID")
        print("Example: python extract_audio.py username/atc-dataset")
        sys.exit(1)

    repo_id = sys.argv[1]
    extract_audio_archives(repo_id)
'''

    with open('extract_audio.py', 'w') as f:
        f.write(script_content)

    print("[OK] Created extract_audio.py")
    return 'extract_audio.py'


def upload_dataset_compressed(repo_id, data_dir='data', private=False,
                             files_per_archive=1000, keep_archives=False):
    """
    Upload dataset with compressed audio files.

    Args:
        repo_id: Repository ID
        data_dir: Data directory
        private: Create private repository
        files_per_archive: Files per archive
        keep_archives: Keep archive files after upload

    Returns:
        True if successful
    """
    api = HfApi()
    data_path = Path(data_dir)
    temp_dir = Path('temp_archives')

    print("=" * 70)
    print("COMPRESSED UPLOAD TO HUGGING FACE")
    print("=" * 70)
    print(f"\nRepository: {repo_id}")
    print(f"Data directory: {data_path.absolute()}")

    # Create repo
    try:
        api.repo_info(repo_id=repo_id, repo_type="dataset")
        print(f"\n[OK] Repository exists: {repo_id}")
    except HfHubHTTPError:
        print(f"\n[!] Creating repository: {repo_id}")
        create_repo(repo_id=repo_id, repo_type="dataset", private=private, exist_ok=True)

    # Step 1: Create audio archives
    print("\n" + "-" * 70)
    print("Step 1: Creating audio archives...")

    audio_dir = data_path / 'audio_segments'
    if not audio_dir.exists():
        print("[X] audio_segments directory not found")
        return False

    archives = create_audio_archives(audio_dir, temp_dir, files_per_archive)

    # Step 2: Upload README
    print("\n" + "-" * 70)
    print("Step 2: Creating and uploading README...")

    from upload_to_huggingface import create_dataset_card
    readme_path = create_dataset_card(data_dir, 'README.md')

    # Add note about compressed audio
    with open(readme_path, 'a') as f:
        f.write("\n\n## Audio Files\n\n")
        f.write("Audio files are provided as compressed archives for efficient download.\n\n")
        f.write("### Download and Extract\n\n")
        f.write("```python\n")
        f.write("from huggingface_hub import hf_hub_download\n")
        f.write("import zipfile\n\n")
        f.write(f'# Download and extract audio archives\n')
        f.write("# See extract_audio.py for automated extraction\n")
        f.write("```\n\n")
        f.write(f"Total archives: {len(archives)}\n")

    api.upload_file(
        path_or_fileobj=readme_path,
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="dataset"
    )
    print("[OK] README uploaded")

    # Step 3: Upload CSV files
    print("\n" + "-" * 70)
    print("Step 3: Uploading CSV files...")

    for csv_file in ['all_segments.csv', 'all_segments_detailed.csv']:
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

    # Step 4: Upload audio archives
    print("\n" + "-" * 70)
    print("Step 4: Uploading audio archives...")

    for i, archive in enumerate(archives, 1):
        archive_size_mb = archive.stat().st_size / (1024 * 1024)
        print(f"\n[{i}/{len(archives)}] Uploading {archive.name} ({archive_size_mb:.1f} MB)...")

        try:
            api.upload_file(
                path_or_fileobj=str(archive),
                path_in_repo=archive.name,
                repo_id=repo_id,
                repo_type="dataset"
            )
            print(f"  [OK] {archive.name} uploaded")
        except Exception as e:
            print(f"  [X] Error: {e}")
            return False

    # Step 5: Upload transcripts
    print("\n" + "-" * 70)
    print("Step 5: Uploading transcript files...")

    transcripts_dir = data_path / 'transcripts'
    if transcripts_dir.exists():
        api.upload_folder(
            folder_path=str(transcripts_dir),
            path_in_repo="transcripts",
            repo_id=repo_id,
            repo_type="dataset",
            allow_patterns="*.json",
            ignore_patterns="*_raw.json"
        )
        print("[OK] Transcripts uploaded")

    # Step 6: Upload analysis report
    print("\n" + "-" * 70)
    print("Step 6: Uploading analysis report...")

    report_path = data_path / 'analysis_report.txt'
    if report_path.exists():
        api.upload_file(
            path_or_fileobj=str(report_path),
            path_in_repo="analysis_report.txt",
            repo_id=repo_id,
            repo_type="dataset"
        )
        print("[OK] analysis_report.txt")

    # Step 7: Upload extraction script
    print("\n" + "-" * 70)
    print("Step 7: Creating extraction script...")

    extract_script = create_extraction_script()
    api.upload_file(
        path_or_fileobj=extract_script,
        path_in_repo="extract_audio.py",
        repo_id=repo_id,
        repo_type="dataset"
    )
    print("[OK] extract_audio.py uploaded")

    # Cleanup
    if not keep_archives:
        print("\n" + "-" * 70)
        print("Cleaning up temporary files...")
        shutil.rmtree(temp_dir)
        print("[OK] Temporary archives deleted")

    # Summary
    print("\n" + "=" * 70)
    print("UPLOAD COMPLETE")
    print("=" * 70)
    print(f"\nDataset URL: https://huggingface.co/datasets/{repo_id}")
    print(f"\nUploaded:")
    print(f"  - README.md")
    print(f"  - CSV files (2)")
    print(f"  - Audio archives ({len(archives)})")
    print(f"  - Transcript files (~250)")
    print(f"  - Analysis report")
    print(f"  - Extraction script")
    print(f"\nUsers can extract audio with:")
    print(f"  python extract_audio.py {repo_id}")

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Upload dataset with compressed audio files"
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
        help='Create private repository'
    )
    parser.add_argument(
        '--files-per-archive',
        type=int,
        default=1000,
        help='Files per archive (default: 1000)'
    )
    parser.add_argument(
        '--keep-archives',
        action='store_true',
        help='Keep archive files after upload'
    )

    args = parser.parse_args()

    # Check authentication
    print("Checking Hugging Face authentication...")
    if not check_authentication():
        print("\n[X] Not authenticated")
        print("Please login: huggingface-cli login")
        return 1

    print("[OK] Authenticated")

    # Confirm
    print("\n" + "=" * 70)
    audio_dir = Path(args.data_dir) / 'audio_segments'
    audio_files = list(audio_dir.glob('*.wav')) if audio_dir.exists() else []
    num_archives = (len(audio_files) + args.files_per_archive - 1) // args.files_per_archive

    print(f"Ready to upload to: {args.repo_id}")
    print(f"Audio files: {len(audio_files)}")
    print(f"Will create: {num_archives} archive(s)")
    print(f"Files per archive: {args.files_per_archive}")
    print("=" * 70)

    response = input("\nProceed? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cancelled.")
        return 0

    # Upload
    success = upload_dataset_compressed(
        repo_id=args.repo_id,
        data_dir=args.data_dir,
        private=args.private,
        files_per_archive=args.files_per_archive,
        keep_archives=args.keep_archives
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
