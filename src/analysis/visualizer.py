"""
Visualization Module

Creates charts and visualizations for ATC transcript analysis.
"""

import matplotlib.pyplot as plt
import matplotlib
from pathlib import Path
from typing import Dict, List
from analyzer import Analyzer


class Visualizer:
    """Create visualizations for ATC analysis."""
    
    def __init__(self, output_dir: str = "data/visualizations"):
        """
        Initialize the visualizer.
        
        Args:
            output_dir: Directory to save visualization files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set style
        plt.style.use('seaborn-v0_8-darkgrid')
        matplotlib.rcParams['figure.figsize'] = (14, 8)
        matplotlib.rcParams['font.size'] = 10
    
    def plot_top_words(self, word_freq: List[tuple], top_n: int = 20):
        """
        Create bar chart of top N most common words.
        
        Args:
            word_freq: List of (word, count) tuples
            top_n: Number of top words to display
        """
        top_words = word_freq[:top_n]
        words, counts = zip(*top_words)
        
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.barh(range(len(words)), counts, color='steelblue')
        ax.set_yticks(range(len(words)))
        ax.set_yticklabels(words)
        ax.invert_yaxis()
        ax.set_xlabel('Frequency', fontsize=12, fontweight='bold')
        ax.set_title(f'Top {top_n} Most Common Words in ATC Transcriptions', 
                    fontsize=14, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        
        for i, count in enumerate(counts):
            ax.text(count + max(counts)*0.01, i, str(count), 
                   va='center', fontsize=9)
        
        plt.tight_layout()
        output_file = self.output_dir / f'top_{top_n}_words.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Saved: {output_file}")
    
    def plot_aviation_terms(self, aviation_terms: List[tuple], top_n: int = 20):
        """
        Create bar chart of aviation-specific terms.
        
        Args:
            aviation_terms: List of (term, count) tuples
            top_n: Number of top terms to display
        """
        top_terms = aviation_terms[:top_n]
        terms, counts = zip(*top_terms)
        
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.barh(range(len(terms)), counts, color='darkorange')
        ax.set_yticks(range(len(terms)))
        ax.set_yticklabels(terms)
        ax.invert_yaxis()
        ax.set_xlabel('Frequency', fontsize=12, fontweight='bold')
        ax.set_title(f'Top {top_n} Aviation-Specific Terms', 
                    fontsize=14, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        
        for i, count in enumerate(counts):
            ax.text(count + max(counts)*0.01, i, str(count), 
                   va='center', fontsize=9)
        
        plt.tight_layout()
        output_file = self.output_dir / 'aviation_terms.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Saved: {output_file}")
    
    def plot_duration_by_video(self, video_stats: List[Dict]):
        """
        Create bar chart of duration by video.
        
        Args:
            video_stats: List of video statistics dictionaries
        """
        # Sort by duration
        sorted_stats = sorted(video_stats, key=lambda x: x['duration'], reverse=True)
        
        video_ids = [s['video_id'] for s in sorted_stats]
        durations = [s['duration']/60 for s in sorted_stats]  # Convert to minutes
        
        fig, ax = plt.subplots(figsize=(14, 6))
        bars = ax.bar(range(len(video_ids)), durations, color='mediumseagreen')
        ax.set_xticks(range(len(video_ids)))
        ax.set_xticklabels(video_ids, rotation=45, ha='right', fontsize=8)
        ax.set_ylabel('Duration (minutes)', fontsize=12, fontweight='bold')
        ax.set_title('Total Duration by Video', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        output_file = self.output_dir / 'duration_by_video.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Saved: {output_file}")
    
    def plot_segments_by_video(self, video_stats: List[Dict]):
        """
        Create bar chart of segment count by video.
        
        Args:
            video_stats: List of video statistics dictionaries
        """
        # Sort by segment count
        sorted_stats = sorted(video_stats, key=lambda x: x['segments'], reverse=True)
        
        video_ids = [s['video_id'] for s in sorted_stats]
        segments = [s['segments'] for s in sorted_stats]
        
        fig, ax = plt.subplots(figsize=(14, 6))
        bars = ax.bar(range(len(video_ids)), segments, color='mediumpurple')
        ax.set_xticks(range(len(video_ids)))
        ax.set_xticklabels(video_ids, rotation=45, ha='right', fontsize=8)
        ax.set_ylabel('Number of Segments', fontsize=12, fontweight='bold')
        ax.set_title('Number of Segments by Video', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        output_file = self.output_dir / 'segments_by_video.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Saved: {output_file}")
    
    def create_all_visualizations(self):
        """Create all standard visualizations."""
        print("Creating visualizations...")
        
        analyzer = Analyzer()
        duration_stats = analyzer.analyze_duration()
        vocab_stats = analyzer.analyze_vocabulary()
        
        self.plot_top_words(vocab_stats['top_words'], top_n=20)
        self.plot_aviation_terms(vocab_stats['aviation_terms'], top_n=20)
        self.plot_duration_by_video(duration_stats['video_stats'])
        self.plot_segments_by_video(duration_stats['video_stats'])
        
        print("\n✓ All visualizations created successfully!")


if __name__ == "__main__":
    # Example usage
    visualizer = Visualizer()
    visualizer.create_all_visualizations()
