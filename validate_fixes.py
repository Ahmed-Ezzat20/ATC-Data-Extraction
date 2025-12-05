import sys
import pandas as pd
sys.path.insert(0, '/home/ubuntu/ATC-Data-Extraction')

from src.preprocessing.normalizer import ATCTextNormalizer

# Load the CSV
df = pd.read_csv('/home/ubuntu/upload/all_segments_detailed(1).csv')

# Initialize normalizer
normalizer = ATCTextNormalizer()

# List of previously identified problematic samples (by index)
problematic_indices = [1, 4, 8, 9, 12, 14, 16, 20, 21, 38, 45, 55, 71, 78, 89, 90]

print("="*80)
print("Validating Fixes on Full CSV Dataset")
print("="*80)

all_passed = True

for index in problematic_indices:
    if index < len(df):
        row = df.iloc[index]
        original = row['original_transcription']
        if pd.isna(original):
            continue
        
        normalized = normalizer.normalize_text(original)
        
        print(f"\n--- Sample {index+1} ---")
        print(f"  Original:   {original}")
        print(f"  Normalized: {normalized}")
        
        # Verification checks
        if "->" in original and "TO" not in normalized:
            print("  ❌ FAILED: Arrow notation not converted")
            all_passed = False
        if "PC-12" in original and "PC ONE TWO" not in normalized:
            print("  ❌ FAILED: PC-12 not handled correctly")
            all_passed = False
        if "3,000" in original and "THREE THOUSAND" not in normalized:
            print("  ❌ FAILED: 3,000 not handled correctly")
            all_passed = False
        if "N0KW" in original and "NOVEMBER ZERO KILO WHISKEY" not in normalized:
            print("  ❌ FAILED: N0KW not handled correctly")
            all_passed = False
        if "GPD848" in original and "GOLF PAPA DELTA EIGHT FOUR EIGHT" not in normalized:
            print("  ❌ FAILED: GPD848 not handled correctly")
            all_passed = False

print("\n" + "="*80)
if all_passed:
    print("✅ All previously identified issues have been successfully fixed!")
else:
    print("❌ Some issues remain.")
print("="*80)
