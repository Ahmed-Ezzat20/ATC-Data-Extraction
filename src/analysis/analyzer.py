"""
Analysis Module

Performs duration and vocabulary analysis on extracted transcripts.
"""

import json
import re
import csv
from pathlib import Path
from collections import Counter
from typing import Dict, List, Tuple


class Analyzer:
    """Analyze ATC transcripts for duration and vocabulary statistics."""
    
    def __init__(self, transcripts_dir: str = "data/transcripts"):
        """
        Initialize the analyzer.
        
        Args:
            transcripts_dir: Directory containing transcript JSON files
        """
        self.transcripts_dir = Path(transcripts_dir)
    
    def load_all_transcripts(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Load all transcript files.

        Returns:
            Tuple of (all_segments, video_stats)
        """
        json_files = sorted(self.transcripts_dir.glob("*.json"))
        # Exclude raw files
        json_files = [f for f in json_files if not f.stem.endswith('_raw')]

        all_segments = []
        video_stats = []

        for json_file in json_files:
            with open(json_file, 'r') as f:
                data = json.load(f)

            video_duration = sum(seg['duration'] for seg in data['segments'])
            video_stats.append({
                'video_id': data['video_id'],
                'segments': len(data['segments']),
                'duration': video_duration
            })

            # Add video_id to each segment for proper tracking
            for segment in data['segments']:
                segment_with_id = segment.copy()
                segment_with_id['video_id'] = data['video_id']
                all_segments.append(segment_with_id)

        return all_segments, video_stats
    
    def analyze_duration(self) -> Dict:
        """
        Analyze duration statistics.
        
        Returns:
            Dictionary with duration statistics
        """
        segments, video_stats = self.load_all_transcripts()
        
        total_duration = sum(seg['duration'] for seg in segments)
        
        return {
            'total_videos': len(video_stats),
            'total_segments': len(segments),
            'total_duration_seconds': total_duration,
            'total_duration_minutes': total_duration / 60,
            'total_duration_hours': total_duration / 3600,
            'average_segment_duration': total_duration / len(segments) if segments else 0,
            'video_stats': video_stats
        }
    
    def analyze_vocabulary(self) -> Dict:
        """
        Analyze vocabulary statistics.
        
        Returns:
            Dictionary with vocabulary statistics
        """
        segments, _ = self.load_all_transcripts()
        
        # Combine all transcripts
        all_text = ' '.join([seg['transcript'] for seg in segments])
        
        # Tokenize
        words = re.findall(r'\b[A-Za-z0-9]+\b', all_text)
        words_lower = [w.lower() for w in words]
        
        total_words = len(words_lower)
        unique_words = len(set(words_lower))
        word_freq = Counter(words_lower)
        
        # Aviation terms
        aviation_terms = {
            'runway', 'taxi', 'taxiway', 'gate', 'clearance', 'cleared', 'approach',
            'departure', 'arrival', 'altitude', 'heading', 'speed', 'knots', 'feet',
            'climb', 'descend', 'hold', 'holding', 'contact', 'tower', 'ground',
            'radar', 'traffic', 'aircraft', 'flight', 'pushback', 'startup',
            'emergency', 'mayday', 'pan', 'squawk', 'transponder', 'roger', 'wilco',
            'affirmative', 'negative', 'standby', 'proceed', 'continue', 'wind',
            'visibility', 'weather', 'fuel', 'divert', 'alternate', 'go', 'around'
        }
        
        aviation_counts = {
            word: word_freq.get(word, 0) 
            for word in aviation_terms 
            if word_freq.get(word, 0) > 0
        }
        aviation_counts_sorted = sorted(
            aviation_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Flight callsigns (words with numbers)
        callsigns = [w for w in words if re.search(r'\d', w)]
        callsign_freq = Counter(callsigns)
        
        return {
            'total_words': total_words,
            'unique_words': unique_words,
            'vocabulary_richness': unique_words / total_words if total_words > 0 else 0,
            'word_frequency': word_freq,
            'top_words': word_freq.most_common(50),
            'aviation_terms': aviation_counts_sorted,
            'top_callsigns': callsign_freq.most_common(20)
        }
    
    def generate_csv(self, output_file: str = "data/all_segments.csv",
                    detailed: bool = False):
        """
        Generate CSV file with all segments.
        
        Args:
            output_file: Output CSV file path
            detailed: Whether to include detailed metadata
        """
        segments, _ = self.load_all_transcripts()
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if detailed:
            fieldnames = [
                'audio_filename', 'transcription', 'video_id', 'segment_num',
                'start_time', 'duration', 'timestamp_range'
            ]
        else:
            fieldnames = ['audio_filename', 'transcription']
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for seg in segments:
                # Generate proper audio filename with video_id
                video_id = seg.get('video_id', 'unknown')
                audio_filename = f"{video_id}_seg{seg['segment_num']:03d}.wav"

                row = {
                    'audio_filename': audio_filename,
                    'transcription': seg['transcript']
                }

                if detailed:
                    row.update({
                        'video_id': video_id,
                        'segment_num': seg['segment_num'],
                        'start_time': seg['start_time'],
                        'duration': seg['duration'],
                        'timestamp_range': seg['timestamp_range']
                    })

                writer.writerow(row)
    
    def generate_report(self, output_file: str = "data/analysis_report.txt"):
        """
        Generate comprehensive analysis report.
        
        Args:
            output_file: Output report file path
        """
        duration_stats = self.analyze_duration()
        vocab_stats = self.analyze_vocabulary()
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("ATC TRANSCRIPTIONS ANALYSIS REPORT\n")
            f.write("="*70 + "\n\n")
            
            # Duration statistics
            f.write("DURATION STATISTICS\n")
            f.write("-"*70 + "\n")
            f.write(f"Total Videos: {duration_stats['total_videos']}\n")
            f.write(f"Total Segments: {duration_stats['total_segments']:,}\n")
            f.write(f"Total Duration: {duration_stats['total_duration_seconds']} seconds\n")
            f.write(f"                {duration_stats['total_duration_minutes']:.2f} minutes\n")
            f.write(f"                {duration_stats['total_duration_hours']:.2f} hours\n")
            f.write(f"Average Segment: {duration_stats['average_segment_duration']:.2f} seconds\n\n")
            
            # Vocabulary statistics
            f.write("VOCABULARY STATISTICS\n")
            f.write("-"*70 + "\n")
            f.write(f"Total Words: {vocab_stats['total_words']:,}\n")
            f.write(f"Unique Words: {vocab_stats['unique_words']:,}\n")
            f.write(f"Vocabulary Richness: {vocab_stats['vocabulary_richness']*100:.2f}%\n\n")
            
            # Top words
            f.write("TOP 30 MOST COMMON WORDS\n")
            f.write("-"*70 + "\n")
            for i, (word, count) in enumerate(vocab_stats['top_words'][:30], 1):
                freq_pct = (count / vocab_stats['total_words']) * 100
                f.write(f"{i:3d}. {word:<20} {count:>6} ({freq_pct:>6.2f}%)\n")
            
            f.write("\n" + "="*70 + "\n")


if __name__ == "__main__":
    # Example usage
    analyzer = Analyzer()
    
    duration_stats = analyzer.analyze_duration()
    print(f"Total duration: {duration_stats['total_duration_minutes']:.1f} minutes")
    
    vocab_stats = analyzer.analyze_vocabulary()
    print(f"Total words: {vocab_stats['total_words']:,}")
    print(f"Unique words: {vocab_stats['unique_words']:,}")
