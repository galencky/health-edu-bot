#!/usr/bin/env python3
"""
Sort and organize manually downloaded files from Google Drive
This script reorganizes files into proper directory structure based on filename patterns
"""

import os
import shutil
import re
from pathlib import Path
from collections import defaultdict

# Configuration
SOURCE_DIR = r"C:\Users\galen\Downloads\mededbot_drive"
ORGANIZED_DIR = r"C:\Users\galen\Downloads\mededbot_drive_organized"

def parse_filename(filename):
    """Parse filename to extract user_id, type, and other metadata"""
    # Remove extension
    name_without_ext = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]
    
    # Pattern 1: U{user_id}_taigi_{timestamp}.wav
    taigi_pattern = r'^(U[a-fA-F0-9]{32})_taigi_(\d{8}_\d{6})$'
    
    # Pattern 2: U{user_id}-{timestamp}.txt (with dash)
    dash_pattern = r'^(U[a-fA-F0-9]{32})-(\d{8}_\d{6})$'
    
    # Pattern 2b: U{user_id}-{description}-{timestamp}.txt (with descriptors)
    dash_descriptor_pattern = r'^(U[a-fA-F0-9]{32})-(.+)-(\d{8}_\d{6})$'
    
    # Pattern 3: U{user_id}_{timestamp}.{ext} (standard)
    standard_pattern = r'^(U[a-fA-F0-9]{32})_(\d{8}_\d{6})$'
    
    # Pattern 4: {timestamp}_U{user_id}_{rest} (prefixed with timestamp)
    prefixed_pattern = r'^(\d{8}_\d{6})_(U[a-fA-F0-9]{32})_(.+)$'
    
    # Pattern 5: {timestamp}_{rest} (timestamp only)
    timestamp_pattern = r'^(\d{8}_\d{6})_(.+)$'
    
    # Pattern 6: U{user_id}_taigi.wav (simple taigi)
    taigi_simple_pattern = r'^(U[a-fA-F0-9]{32})_taigi$'
    
    result = {
        'filename': filename,
        'user_id': None,
        'timestamp': None,
        'category': None,
        'type': None
    }
    
    # Try to match patterns
    if match := re.match(taigi_pattern, name_without_ext):
        result['user_id'] = match.group(1)
        result['timestamp'] = match.group(2)
        result['type'] = 'taigi_tts'
    elif match := re.match(taigi_simple_pattern, name_without_ext):
        result['user_id'] = match.group(1)
        result['type'] = 'taigi_tts'
    elif match := re.match(dash_descriptor_pattern, name_without_ext):
        result['user_id'] = match.group(1)
        result['type'] = match.group(2)  # e.g., 'stt-translation'
        result['timestamp'] = match.group(3)
    elif match := re.match(dash_pattern, name_without_ext):
        result['user_id'] = match.group(1)
        result['timestamp'] = match.group(2)
        result['type'] = 'text_file'
    elif match := re.match(standard_pattern, name_without_ext):
        result['user_id'] = match.group(1)
        result['timestamp'] = match.group(2)
        result['type'] = 'standard'
    elif match := re.match(prefixed_pattern, name_without_ext):
        result['timestamp'] = match.group(1)
        result['user_id'] = match.group(2)
        result['type'] = match.group(3)
    elif match := re.match(timestamp_pattern, name_without_ext):
        result['timestamp'] = match.group(1)
        result['type'] = match.group(2)
    
    # Determine category by extension and content
    if ext.lower() in ['.wav', '.mp3']:
        result['category'] = 'tts_audio'
    elif ext.lower() in ['.m4a', '.aac']:
        result['category'] = 'voicemail'
    elif ext.lower() in ['.txt', '.html', '.htm']:
        # All text-based files go to text category
        result['category'] = 'text'
    else:
        result['category'] = 'other'
    
    return result

def organize_files():
    """Organize files into proper directory structure"""
    if not os.path.exists(SOURCE_DIR):
        print(f"ERROR: Source directory not found: {SOURCE_DIR}")
        return
    
    # Create organized directory
    os.makedirs(ORGANIZED_DIR, exist_ok=True)
    
    stats = defaultdict(int)
    processed_files = []
    unknown_files = []
    
    print("Scanning files...")
    
    # Get all files
    all_files = []
    for root, dirs, files in os.walk(SOURCE_DIR):
        for file in files:
            if file.lower() == 'desktop.ini':
                continue
            all_files.append(os.path.join(root, file))
    
    print(f"Found {len(all_files)} files to organize")
    print("="*60)
    
    # Process each file
    for file_path in all_files:
        filename = os.path.basename(file_path)
        parsed = parse_filename(filename)
        
        stats['total'] += 1
        
        # Skip if no user_id found
        if not parsed['user_id']:
            print(f"⚠️  No user ID found: {filename}")
            unknown_files.append(file_path)
            stats['unknown'] += 1
            continue
        
        # Determine destination
        category = parsed['category']
        user_id = parsed['user_id']
        
        if category in ['tts_audio', 'voicemail', 'text']:
            dest_dir = os.path.join(ORGANIZED_DIR, category, user_id)
        else:
            dest_dir = os.path.join(ORGANIZED_DIR, 'other', user_id)
        
        # Create destination directory
        os.makedirs(dest_dir, exist_ok=True)
        
        # Copy file
        dest_path = os.path.join(dest_dir, filename)
        
        if os.path.exists(dest_path):
            print(f"⏭️  Already exists: {filename}")
            stats['skipped'] += 1
        else:
            shutil.copy2(file_path, dest_path)
            print(f"✓ {category}/{user_id}/{filename}")
            stats[f'organized_{category}'] += 1
            
            processed_files.append({
                'source': file_path,
                'dest': dest_path,
                'parsed': parsed
            })
    
    # Create metadata for each user directory
    print("\nCreating metadata files...")
    for category in ['tts_audio', 'voicemail', 'text', 'other']:
        category_dir = os.path.join(ORGANIZED_DIR, category)
        if not os.path.exists(category_dir):
            continue
            
        for user_dir in os.listdir(category_dir):
            user_path = os.path.join(category_dir, user_dir)
            if not os.path.isdir(user_path):
                continue
                
            # Create metadata.csv
            metadata_file = os.path.join(user_path, 'metadata.csv')
            with open(metadata_file, 'w', encoding='utf-8') as f:
                f.write('filename,user_id,timestamp,type,category\n')
                
                for file in os.listdir(user_path):
                    if file == 'metadata.csv':
                        continue
                    parsed = parse_filename(file)
                    f.write(f'"{file}","{parsed["user_id"]}","{parsed["timestamp"] or ""}","{parsed["type"] or ""}","{parsed["category"]}"\n')
    
    # Print summary
    print("\n" + "="*60)
    print("ORGANIZATION SUMMARY")
    print("="*60)
    print(f"Total files processed: {stats['total']}")
    print(f"Files with unknown user ID: {stats['unknown']}")
    print(f"Files skipped (already exist): {stats['skipped']}")
    print("\nOrganized by category:")
    for key, value in stats.items():
        if key.startswith('organized_'):
            category = key.replace('organized_', '')
            print(f"  {category}: {value}")
    
    print(f"\nFiles organized to: {ORGANIZED_DIR}")
    
    # Save unknown files list
    if unknown_files:
        unknown_file = os.path.join(ORGANIZED_DIR, 'unknown_files.txt')
        with open(unknown_file, 'w', encoding='utf-8') as f:
            f.write("Files without identifiable user ID:\n\n")
            for file in unknown_files:
                f.write(f"{file}\n")
        print(f"\nUnknown files list saved to: {unknown_file}")
    
    # Show directory structure
    print("\nDirectory structure created:")
    for category in ['tts_audio', 'voicemail', 'text', 'other']:
        category_path = os.path.join(ORGANIZED_DIR, category)
        if os.path.exists(category_path):
            user_count = len([d for d in os.listdir(category_path) if os.path.isdir(os.path.join(category_path, d))])
            print(f"  {category}/  ({user_count} users)")

def main():
    """Main entry point"""
    print("File Organization Tool")
    print("="*60)
    print(f"Source: {SOURCE_DIR}")
    print(f"Destination: {ORGANIZED_DIR}")
    print("="*60)
    
    # Confirm before proceeding
    response = input("\nThis will organize files into a new directory structure. Continue? (y/n): ")
    if response.lower() != 'y':
        print("Aborted.")
        return
    
    organize_files()
    
    print("\n✓ Organization complete!")
    print("\nNext steps:")
    print("1. Review the organized structure")
    print("2. Check unknown_files.txt for any files that couldn't be categorized")
    print("3. Run step2_upload_to_r2.py with the organized directory")

if __name__ == "__main__":
    main()