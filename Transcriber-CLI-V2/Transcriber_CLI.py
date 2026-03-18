from art import tprint
from transcribers.FirstShot import First_Shot
from transcribers.SecondShot import Second_Shot
from helpers.cost_analysis import cost_tracker
from helpers.txt_to_csv import convert_json_to_csv
from helpers.segmentation import process_images_segmentation, get_segmentation_settings
from Validation.validate_scientific_names import validate_csv_scientific_names
from Validation.find_duplicate_records import validate_csv_duplicate_records
from Validation.find_duplicate_entries import validate_csv_entries
import os
import re
import stat
from pathlib import Path
import requests
from urllib.parse import urlparse
import shutil
import json
import pandas as pd
from datetime import datetime
import json


# Global validation settings
validation_settings = {
    'scientific_names': True,  # Default: enabled
    'duplicate_records': False,  # Default: disabled
    'duplicate_entries': True,  # Default: enabled (collector, date, collid search)
    # Future validation types can be added here
    # 'genus_species': True,
    # 'collection_data': True,
}


def configure_validation_settings():
    global validation_settings
    
    print("\n" + "="*60)
    print("VALIDATION SETTINGS")
    print("="*60)
    print("Configure which fields will be validated at the end of transcription.")
    print("All validations are enabled by default.")
    print("Use numbers to toggle settings, 'r' to reset all to default, 'q' to finish.")
    print("-"*60)
    
    while True:
        # Display current settings
        print("\nCurrent Validation Settings:")
        print("1. Scientific Names Validation:", "✓ ENABLED" if validation_settings['scientific_names'] else "✗ DISABLED")
        print("2. Duplicate Records Validation:", "✓ ENABLED" if validation_settings['duplicate_records'] else "✗ DISABLED")
        print("3. Duplicate Entries Validation:", "✓ ENABLED" if validation_settings['duplicate_entries'] else "✗ DISABLED")
        # Future validations can be added here:
        # print("4. Genus/Species Validation:", "✓ ENABLED" if validation_settings['genus_species'] else "✗ DISABLED")
        # print("4. Collection Data Validation:", "✓ ENABLED" if validation_settings['collection_data'] else "✗ DISABLED")
        
        print("\nOptions:")
        print("1 - Toggle Scientific Names Validation")
        print("2 - Toggle Duplicate Records Validation")
        print("3 - Toggle Duplicate Entries Validation")
        # print("4 - Toggle Genus/Species Validation")
        # print("5 - Toggle Collection Data Validation")
        print("r - Reset all to default (all enabled)")
        print("q - Finish and return to main menu")
        print("back - Return to main menu")
        
        choice = input("\nEnter your choice: ").strip().lower()
        
        if choice == '1':
            validation_settings['scientific_names'] = not validation_settings['scientific_names']
            status = "enabled" if validation_settings['scientific_names'] else "disabled"
            print(f"Scientific Names Validation {status}")
            
        elif choice == '2':
            validation_settings['duplicate_records'] = not validation_settings['duplicate_records']
            status = "enabled" if validation_settings['duplicate_records'] else "disabled"
            print(f"Duplicate Records Validation {status}")
            
        elif choice == '3':
            validation_settings['duplicate_entries'] = not validation_settings['duplicate_entries']
            status = "enabled" if validation_settings['duplicate_entries'] else "disabled"
            print(f"Duplicate Entries Validation {status}")
            
        # Future validation toggles:
        # elif choice == '4':
        #     validation_settings['genus_species'] = not validation_settings['genus_species']
        #     status = "enabled" if validation_settings['genus_species'] else "disabled"
        #     print(f"Genus/Species Validation {status}")
        
        elif choice == 'r' or choice == 'reset':
            validation_settings = {
                'scientific_names': True,
                'duplicate_records': False,
                'duplicate_entries': True,
                # Future defaults:
                # 'genus_species': True,
                # 'collection_data': True,
            }
            print("All validation settings reset to default (enabled)")
            
        elif choice == 'q' or choice == 'quit' or choice == 'back':
            break
            
        else:
            print("Invalid choice. Please enter 1, 'r', 'q', or 'back'")
    
    print("\nValidation settings saved!")
    return validation_settings


#Determine how many shots to do
def select_shots():
    while True:
        choice = input("\nChoose processing mode:\n1. One shot\n2. Two shots\nEnter choice (1-2) or 'back' to go back: ")
        if choice in ['1', '2']:
            return int(choice)
        elif choice.lower() == 'back':
            return 'back'
        print("Please enter 1, 2, or 'back'")


#Ask if user wants to use segmentation
def select_segmentation():
    while True:
        choice = input("\nDo you want to use image segmentation before transcription?\n1. Yes - Run segmentation first\n2. No - Skip segmentation\nEnter choice (1-2) or 'back' to go back: ")
        if choice in ['1', '2']:
            return choice == '1'  # Returns True for segmentation, False for skip
        elif choice.lower() == 'back':
            return 'back'
        print("Please enter 1, 2, or 'back'")


#Local or URL download Images
def select_image_source():
    while True:
        choice = input("\nChoose image source:\n1. Local images\n2. URL download\n3. CSV file with URLs (transcribe missing fields only)\nEnter choice (1-3) or 'back' to go back: ")
        if choice == '1':
            return 'local'
        elif choice == '2':
            return 'url'
        elif choice == '3':
            return 'csv'
        elif choice.lower() == 'back':
            return 'back'
        print("Please enter 1, 2, 3, or 'back'")


# ============================================================
# CSV-based transcription functions
# ============================================================

def get_csv_file_path():
    """Get path to CSV file containing image URLs and existing data."""
    while True:
        csv_path = input("\nEnter path to CSV file with image URLs (or 'back' to go back): ").strip()
        if csv_path.lower() == 'back':
            return 'back', None
        
        if not os.path.exists(csv_path):
            print(f"Error: File not found at {csv_path}")
            continue
        
        if not csv_path.endswith('.csv'):
            print("Error: File must be a .csv file")
            continue
        
        # Load and analyze the CSV
        try:
            df = pd.read_csv(csv_path)
            print(f"\n✅ Loaded CSV with {len(df)} rows and {len(df.columns)} columns")
            return csv_path, df
        except Exception as e:
            print(f"Error reading CSV: {e}")
            continue


def select_url_column(df):
    """Let user select which column contains the image URLs."""
    print("\n" + "="*60)
    print("SELECT IMAGE URL COLUMN")
    print("="*60)
    print("\nAvailable columns:")
    
    # Show columns with sample values
    for i, col in enumerate(df.columns, 1):
        sample = str(df[col].iloc[0])[:50] if len(df) > 0 else "N/A"
        print(f"{i:3d}. {col[:40]:<40} | Sample: {sample}...")
    
    while True:
        choice = input(f"\nSelect column containing image URLs (1-{len(df.columns)}) or 'back': ").strip()
        if choice.lower() == 'back':
            return 'back'
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(df.columns):
                selected_col = df.columns[idx]
                # Verify it looks like URLs
                sample_val = str(df[selected_col].iloc[0]) if len(df) > 0 else ""
                if 'http' in sample_val.lower():
                    print(f"\n✅ Selected: '{selected_col}' - looks like URLs!")
                    return selected_col
                else:
                    confirm = input(f"Warning: '{selected_col}' doesn't look like URLs. Continue anyway? (y/n): ")
                    if confirm.lower() in ['y', 'yes']:
                        return selected_col
            else:
                print(f"Please enter a number between 1 and {len(df.columns)}")
        except ValueError:
            print("Please enter a valid number or 'back'")


def analyze_empty_fields(df, url_column):
    """Analyze which fields have empty values that need transcription."""
    print("\n" + "="*60)
    print("ANALYZING EMPTY FIELDS")
    print("="*60)
    
    # Columns to skip (not useful for transcription)
    skip_columns = [url_column, 'Unnamed: 0']
    
    empty_analysis = {}
    for col in df.columns:
        if col in skip_columns:
            continue
        # Count empty/null values
        empty_count = df[col].isna().sum() + (df[col] == "").sum()
        total = len(df)
        if empty_count > 0:
            pct = (empty_count / total) * 100
            empty_analysis[col] = {'empty': empty_count, 'total': total, 'pct': pct}
    
    print("\nFields with missing data:")
    print("-"*60)
    for col, stats in sorted(empty_analysis.items(), key=lambda x: x[1]['pct'], reverse=True):
        print(f"   {col[:35]:<35} | {stats['empty']:>4}/{stats['total']} empty ({stats['pct']:.1f}%)")
    
    return empty_analysis


def select_fields_to_transcribe(df, url_column, empty_analysis):
    """Let user select which fields to transcribe."""
    print("\n" + "="*60)
    print("SELECT FIELDS TO TRANSCRIBE")
    print("="*60)
    
    # Get columns with empty values
    empty_cols = list(empty_analysis.keys())
    
    if not empty_cols:
        print("No empty fields found in the CSV!")
        return []
    
    print("\nFields with missing data (select which to transcribe):")
    for i, col in enumerate(empty_cols, 1):
        stats = empty_analysis[col]
        print(f"{i:3d}. {col[:40]:<40} | {stats['empty']} empty ({stats['pct']:.1f}%)")
    
    print("\n" + "-"*60)
    print("Options:")
    print("  • Enter 'all' to select ALL fields")
    print("  • Enter numbers separated by commas (e.g., 1,3,5,7)")
    print("  • Enter a range (e.g., 1-5)")
    print("  • Combine ranges and numbers (e.g., 1-3,5,7-9)")
    print("  • Enter 'back' to go back")
    print("-"*60)
    
    while True:
        choice = input(f"\nSelect fields to transcribe: ").strip().lower()
        
        if choice == 'back':
            return 'back'
        
        if choice == 'all':
            print(f"\n✅ Will transcribe ALL {len(empty_cols)} fields with missing data")
            return empty_cols
        
        # Parse the selection (handles ranges and comma-separated values)
        selected = []
        try:
            parts = choice.split(',')
            for part in parts:
                part = part.strip()
                if '-' in part:
                    # Handle range (e.g., "1-5")
                    range_parts = part.split('-')
                    if len(range_parts) == 2:
                        start = int(range_parts[0].strip())
                        end = int(range_parts[1].strip())
                        for idx in range(start, end + 1):
                            if 1 <= idx <= len(empty_cols):
                                field = empty_cols[idx - 1]
                                if field not in selected:
                                    selected.append(field)
                else:
                    # Handle single number
                    idx = int(part)
                    if 1 <= idx <= len(empty_cols):
                        field = empty_cols[idx - 1]
                        if field not in selected:
                            selected.append(field)
            
            if selected:
                print(f"\n✅ Selected {len(selected)} field(s):")
                for field in selected:
                    print(f"   • {field}")
                return selected
            else:
                print(f"No valid fields selected. Please enter numbers between 1 and {len(empty_cols)}")
                
        except ValueError:
            print("Invalid input. Please enter 'all', numbers (e.g., 1,3,5), ranges (e.g., 1-5), or 'back'")


def download_images_from_csv(df, url_column, download_dir):
    """Download images from URLs in the CSV file."""
    if os.path.exists(download_dir):
        safe_rmtree(download_dir)
    os.makedirs(download_dir, exist_ok=True)
    
    urls = df[url_column].dropna().tolist()
    print(f"\nDownloading {len(urls)} images from CSV...")
    
    url_map = {}
    row_map = {}  # Map filename to row index for later matching
    
    for i, url in enumerate(urls, 1):
        if not url or not isinstance(url, str) or not url.startswith('http'):
            continue
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Get original filename
            original_filename = os.path.basename(urlparse(url).path) or f"image_{i}.jpg"
            filename = f"{i:04d}_{original_filename}"
            filepath = os.path.join(download_dir, filename)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            url_map[filename] = url
            row_map[filename] = i - 1  # Store the DataFrame row index
            
            if i % 10 == 0 or i == len(urls):
                print(f"Downloaded {i}/{len(urls)}: {filename}")
                
        except Exception as e:
            print(f"Failed to download {url}: {e}")
    
    # Save mappings
    map_path = os.path.join(download_dir, 'url_map.json')
    with open(map_path, 'w', encoding='utf-8') as f:
        json.dump({'url_map': url_map, 'row_map': row_map}, f, indent=2)
    
    print(f"\n✅ Downloaded {len(url_map)} images")
    return url_map, row_map


def merge_transcriptions_to_csv(original_df, transcription_csv_path, url_column, row_map, fields_to_update, output_path):
    """
    Merge transcription results back into the original CSV, filling only empty fields.
    
    Args:
        original_df: Original DataFrame with existing data
        transcription_csv_path: Path to the transcription results CSV
        url_column: Column name containing image URLs
        row_map: Mapping of filenames to original row indices
        fields_to_update: List of field names to update (only if empty)
        output_path: Where to save the merged CSV
    """
    print("\n" + "="*60)
    print("MERGING TRANSCRIPTIONS INTO ORIGINAL CSV")
    print("="*60)
    
    # Load transcription results
    transcription_df = pd.read_csv(transcription_csv_path)
    print(f"Loaded {len(transcription_df)} transcription results")
    
    # Create a copy of the original DataFrame
    merged_df = original_df.copy()
    
    updates_made = 0
    fields_updated = {field: 0 for field in fields_to_update}
    
    # Try to match transcriptions to original rows
    # The transcription CSV should have a filename or image reference
    for idx, trans_row in transcription_df.iterrows():
        # Try to find the matching original row
        # Check if there's an 'image_file' or similar column in transcription
        image_file = None
        for col in ['image_file', 'filename', 'image', 'file']:
            if col in trans_row.index:
                image_file = trans_row[col]
                break
        
        if image_file and image_file in row_map:
            orig_idx = row_map[image_file]
            
            # Update only empty fields in the original
            for field in fields_to_update:
                if field in trans_row.index and field in merged_df.columns:
                    # Check if original field is empty
                    orig_value = merged_df.at[orig_idx, field]
                    is_empty = pd.isna(orig_value) or str(orig_value).strip() == ''
                    
                    if is_empty:
                        new_value = trans_row[field]
                        if pd.notna(new_value) and str(new_value).strip() != '':
                            merged_df.at[orig_idx, field] = new_value
                            fields_updated[field] += 1
                            updates_made += 1
    
    # Save merged CSV
    merged_df.to_csv(output_path, index=False)
    
    print(f"\n✅ Merged transcriptions saved to: {output_path}")
    print(f"\nTotal updates made: {updates_made}")
    print("\nUpdates per field:")
    for field, count in fields_updated.items():
        print(f"   {field}: {count} values filled")
    
    return merged_df


#Name the run instead of having a bunch of dates and shitty formatting
def get_run_name():
    while True:
        run_name = input("\nEnter a name for this run (or press Enter for default): ").strip()
        if run_name.lower() == 'back':
            return 'back'
        if not run_name:
            run_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # Sanitize filename for cross-platform compatibility
        # Remove characters that are problematic on both Windows and Unix
        run_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', run_name)
        # Remove trailing dots and spaces (Windows issue)
        run_name = run_name.rstrip('. ')
        # Ensure it's not empty after sanitization
        if not run_name:
            run_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return run_name


#The most stupid workaround to make this work on all platforms 
#I hate you Bill Gates, you are on that list I know it. 
def safe_rmtree(path):
    if not os.path.exists(path):
        return
    
    try:
        shutil.rmtree(path)
    except PermissionError:
        # Windows sometimes has permission issues, try to fix them
        if os.name == 'nt':  # Windows
            import stat
            def remove_readonly(func, path, exc_info):
                os.chmod(path, stat.S_IWRITE)
                func(path)
            shutil.rmtree(path, onerror=remove_readonly)
        else:
            raise

#Pretty self explanitory
def download_images_from_urls(url_file_path, download_dir):
    if not os.path.exists(url_file_path):
        print(f"Error: URL file not found at {url_file_path}")
        return False
    
    # Clear existing images using safe removal
    if os.path.exists(download_dir):
        safe_rmtree(download_dir)
    
    os.makedirs(download_dir, exist_ok=True)
    
    with open(url_file_path, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    print(f"\nDownloading {len(urls)} images...")
    url_map = {}
    for i, url in enumerate(urls, 1):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Get original filename and add index prefix
            original_filename = os.path.basename(urlparse(url).path) or f"image_{i}.jpg"
            filename = f"{i:04d}_{original_filename}"
            filepath = os.path.join(download_dir, filename)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Track mapping of saved filename to original URL
            url_map[filename] = url
            
            print(f"Downloaded {i}/{len(urls)}: {filename}")
        except Exception as e:
            print(f"Failed to download {url}: {e}")
    
    # Save URL map for later enrichment of JSON/CSV
    try:
        map_path = os.path.join(download_dir, 'url_map.json')
        with open(map_path, 'w', encoding='utf-8') as mf:
            json.dump(url_map, mf, indent=2, ensure_ascii=False)
        print(f"Saved URL map to {map_path}")
    except Exception as e:
        print(f"Warning: Could not save URL map: {e}")
    
    return True



def select_prompt():
    prompts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Prompts")
    
    if os.path.exists(prompts_dir):
        prompt_files = [f for f in os.listdir(prompts_dir) if f.endswith('.txt')]
        if prompt_files:
            print("\nAvailable prompts:")
            for i, prompt in enumerate(prompt_files, 1):
                print(f"{i}. {prompt}")
            print(f"{len(prompt_files) + 1}. Custom filepath")
            
            #Implementing Back options for if you make an oopsie 
            while True:
                choice_input = input(f"\nSelect prompt (1-{len(prompt_files) + 1}) or 'back' to go back: ")
                if choice_input.lower() == 'back':
                    return 'back'
                try:
                    choice = int(choice_input)
                    if 1 <= choice <= len(prompt_files):
                        return os.path.join(prompts_dir, prompt_files[choice-1])
                    elif choice == len(prompt_files) + 1:
                        custom_path = input("Enter custom prompt filepath (or 'back' to go back): ")
                        if custom_path.lower() == 'back':
                            continue
                        return custom_path
                    print(f"Please enter a number between 1 and {len(prompt_files) + 1}")
                except ValueError:
                    print("Please enter a valid number or 'back'")
    
    while True:
        prompt_path = input("Enter prompt filepath (or 'back' to go back): ")
        if prompt_path.lower() == 'back':
            return 'back'
        return prompt_path

#WHERE THE HELL ARE THE TRANSCRITPIONS GOING????????
def get_output_base_path():
    home_dir = Path(os.path.expanduser("~"))
    
    # Try Desktop first on all systems
    desktop_path = home_dir / "Desktop"
    if desktop_path.exists():
        #Right HERE :)
        return desktop_path / "Finished Transcriptions"
    
    # Fallback to home directory if Desktop doesn't exist
    return home_dir / "Finished Transcriptions"

#Shows the number of images in the folder just as a double check for things. 
def show_images_in_folder(folder_path):
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    images = [f for f in os.listdir(folder_path) if os.path.splitext(f.lower())[1] in image_extensions]
    
    if not images:
        print("No image files found in the folder.")
        return
    
    print(f"\nFound {len(images)} image(s):")
    for i, img in enumerate(sorted(images), 1):
        print(f"{i:3d}. {img}")

#Local or URL Images entering 
def get_images_folder(use_urls):
    while True:
        #User chooses URLS
        if use_urls:
            url_file = input("\nEnter path to .txt file containing image URLs (or 'back' to go back): ")
            if url_file.lower() == 'back':
                return 'back', None
            # Use cross-platform path for downloads within temp area
            downloads_dir = get_output_base_path() / "temp_downloads"
            download_dir = str(downloads_dir)
            
            if download_images_from_urls(url_file, download_dir):
                return download_dir, "downloaded_images"
            else:
                print("Failed to download images. Please try again.")
                continue
        else:
            #User chooses Local images on Machine
            folder_path = input("\nEnter path to local images folder (or 'back' to go back): ")
            if folder_path.lower() == 'back':
                return 'back', None
            if not os.path.exists(folder_path):
                print(f"Error: Folder not found at {folder_path}")
                continue
            
            # Ask if user wants to see the images in the folder
            while True:
                show_choice = input("\nDo you want to see the images in this folder? (y/n): ").lower()
                if show_choice in ['y', 'yes']:
                    show_images_in_folder(folder_path)
                    break
                elif show_choice in ['n', 'no']:
                    break
                else:
                    print("Please enter 'y' or 'n'")
            
            return folder_path, os.path.basename(folder_path)


def rename_csv_files(source_dir, run_name, shot_type):
    for csv_file in source_dir.glob('*.csv'):
        new_name = f"{run_name}_{shot_type}.csv"
        new_path = source_dir / new_name
        csv_file.rename(new_path)
        print(f"Renamed {csv_file.name} to {new_name}")
        return new_path  # Return the new path for moving

def move_json_files_to_shot_folder(source_dir, raw_dir, shot_name):
    shot_dir = raw_dir / shot_name
    shot_dir.mkdir(parents=True, exist_ok=True)
    
    for json_file in source_dir.glob('*.json'):
        destination = shot_dir / json_file.name
        shutil.move(str(json_file), str(destination))
        #print(f"Moved {json_file.name} to {shot_name} folder")

#Wrapper for all the stuff before
def ask_continue_after_segmentation():
    while True:
        choice = input("\nSegmentation completed. Do you want to continue with transcription?\n1. Yes - Continue with transcription\n2. No - Stop here\nEnter choice (1-2): ").strip().lower()
        
        # Handle various input formats
        if choice in ['1', 'y', 'yes', 'continue']:
            return True
        elif choice in ['2', 'n', 'no', 'stop']:
            return False
        elif choice == 'quit' or choice == 'exit':
            print("Exiting...")
            return False
        else:
            print("Please enter 1, 2, 'yes', 'no', or 'quit'")
            print(f"You entered: '{choice}'")  # Debug info to help user see what they entered


def configure_transcription():
    config = {}
    step = 'run_name'
    
    while True:
        if step == 'run_name':
            run_name = get_run_name()
            if run_name == 'back':
                return None  # Return to main menu
            config['run_name'] = run_name
            print(f"Run name: {run_name}")
            step = 'segmentation'
            
        elif step == 'segmentation':
            use_segmentation = select_segmentation()
            if use_segmentation == 'back':
                step = 'run_name'
                continue
            config['use_segmentation'] = use_segmentation
            if use_segmentation:
                print("Segmentation will be performed before transcription.")
            else:
                print("Segmentation will be skipped.")
            step = 'shots'
            
        elif step == 'shots':
            num_shots = select_shots()
            if num_shots == 'back':
                step = 'segmentation'
                continue
            config['num_shots'] = num_shots
            step = 'prompt'
            
        elif step == 'prompt':
            prompt_path = select_prompt()
            if prompt_path == 'back':
                step = 'shots'
                continue
            print(f"Using: {prompt_path}")
            if not os.path.exists(prompt_path):
                print(f"Error: Prompt file not found at {prompt_path}")
                continue
            config['prompt_path'] = prompt_path
            step = 'image_source'
            
        elif step == 'image_source':
            image_source = select_image_source()
            if image_source == 'back':
                step = 'prompt'
                continue
            config['image_source'] = image_source
            
            # Route to appropriate next step based on source type
            if image_source == 'csv':
                step = 'csv_file'
            else:
                # For 'local' and 'url', use the old flow
                config['use_urls'] = (image_source == 'url')
                step = 'images_folder'
        
        # New CSV-based workflow steps
        elif step == 'csv_file':
            csv_path, df = get_csv_file_path()
            if csv_path == 'back':
                step = 'image_source'
                continue
            config['csv_path'] = csv_path
            config['csv_df'] = df
            step = 'csv_url_column'
        
        elif step == 'csv_url_column':
            url_column = select_url_column(config['csv_df'])
            if url_column == 'back':
                step = 'csv_file'
                continue
            config['url_column'] = url_column
            step = 'csv_fields'
        
        elif step == 'csv_fields':
            empty_analysis = analyze_empty_fields(config['csv_df'], config['url_column'])
            fields_to_transcribe = select_fields_to_transcribe(
                config['csv_df'], 
                config['url_column'], 
                empty_analysis
            )
            if fields_to_transcribe == 'back':
                step = 'csv_url_column'
                continue
            config['fields_to_transcribe'] = fields_to_transcribe
            config['empty_analysis'] = empty_analysis
            
            # Download images from CSV URLs
            print("\n" + "="*60)
            print("DOWNLOADING IMAGES FROM CSV")
            print("="*60)
            downloads_dir = get_output_base_path() / "temp_csv_downloads"
            download_dir = str(downloads_dir)
            url_map, row_map = download_images_from_csv(
                config['csv_df'], 
                config['url_column'], 
                download_dir
            )
            config['base_folder'] = download_dir
            config['folder_name'] = "csv_images"
            config['url_map'] = url_map
            config['row_map'] = row_map
            break
            
        elif step == 'images_folder':
            base_folder, folder_name = get_images_folder(config['use_urls'])
            if base_folder == 'back':
                step = 'image_source'
                continue
            config['base_folder'] = base_folder
            config['folder_name'] = folder_name
            break
    
    return config


def main():
    tprint("Transcriber-CLI-V2")
    print("Created by: Riley Herbst")
    print(85*"=")
    print("Welcome to the Field Museum transcriber-cli, this is an all-purpose image transcriber.")
    print("(You can type 'back' at any step to return to the previous choice)")
    
    '''
    Checks if ~/Desktop exists → returns ~/Desktop/Finished Transcriptions
    Otherwise falls back to ~/Finished Transcriptions
    '''    
    output_base = get_output_base_path()
    output_base.mkdir(parents=True, exist_ok=True)
    
    
    print(f"Finished transcriptions will be saved to: {output_base}")
    
    # Main menu loop
    while True:
        print("\n" + "="*60)
        print("MAIN MENU")
        print("="*60)
        print("1. Start Transcription Process")
        print("2. Configure Validation Settings")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            # Configure transcription 
            config = configure_transcription()
            if config is None:  # User went back to main menu
                continue
            break  # Exit main menu to continue with transcription
            
        elif choice == '2':
            configure_validation_settings()
            continue  # Return to main menu
            
        elif choice == '3':
            print("Goodbye!")
            return
            
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
    
    # Continue with transcription process
    run_name = config['run_name']
    use_segmentation = config['use_segmentation']
    num_shots = config['num_shots']
    prompt_path = config['prompt_path']
    base_folder = config['base_folder']
    folder_name = config['folder_name']
    
    # Create run-specific output directory
    run_output_dir = get_output_base_path() / run_name
    run_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Handle segmentation if requested
    processing_folder = base_folder  # Default to original folder
    
    if use_segmentation:
        # Create segmentation output folder
        segmentation_output_dir = run_output_dir / "Segmented_Images"
        segmentation_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get segmentation settings
        model_path, classes_to_render = get_segmentation_settings()
        
        try:
            # Run segmentation
            success_count, total_count = process_images_segmentation(
                base_folder, 
                str(segmentation_output_dir), 
                model_path, 
                classes_to_render
            )
            
            print(f"\nSegmentation Results:")
            print(f"Successfully processed: {success_count}/{total_count} images")
            print(f"Segmented images saved to: {segmentation_output_dir}")
            
            # Ask if user wants to continue
            if not ask_continue_after_segmentation():
                print("Stopping at segmentation as requested.")
                print(f"Segmented images can be found at: {segmentation_output_dir}")
                return
            
            # Use segmented images for transcription
            processing_folder = str(segmentation_output_dir)
            print(f"\nContinuing with transcription using segmented images from: {processing_folder}")
            
        except Exception as e:
            print(f"Error during segmentation: {e}")
            print("Continuing with original images...")
            processing_folder = base_folder
    
    # Create Raw Transcriptions folder (.json files)
    raw_transcriptions_dir = run_output_dir / "Raw Transcriptions"
    
    # Set the prompt path in the cost tracker
    cost_tracker.set_prompt_path(prompt_path)
    
    try:
        if num_shots == 1:
            print("\nSelect model for image processing:")
            model = First_Shot.select_model()
            
            # Use run-specific directory for output
            output_dir = run_output_dir
            First_Shot.process_images(processing_folder, prompt_path, output_dir, run_name, model_id=model)
            
            # Convert JSON files to CSV
            print("\n=== Converting JSON files to CSV ===")
            convert_json_to_csv(str(output_dir))
            
            # Validate fields based on user settings
            if validation_settings['scientific_names']:
                print("\n=== Validating Scientific Names ===")
                for csv_file in output_dir.glob('*.csv'):
                    validate_csv_scientific_names(csv_file)
            else:
                print("\n=== Skipping Scientific Names Validation (disabled by user) ===")
            
            if validation_settings['duplicate_records']:
                print("\n=== Validating Duplicate Records ===")
                for csv_file in output_dir.glob('*.csv'):
                    validate_csv_duplicate_records(csv_file)
            else:
                print("\n=== Skipping Duplicate Records Validation (disabled by user) ===")
            
            if validation_settings['duplicate_entries']:
                print("\n=== Validating Duplicate Entries (Collector, Date, CollID) ===")
                for csv_file in output_dir.glob('*.csv'):
                    validate_csv_entries(csv_file)
            else:
                print("\n=== Skipping Duplicate Entries Validation (disabled by user) ===")
            
            # Future validation types can be added here:
            # if validation_settings['genus_species']:
            #     print("\n=== Validating Genus/Species ===")
            #     for csv_file in output_dir.glob('*.csv'):
            #         validate_genus_species(csv_file)
            
            # Rename CSV files
            print("\n=== Renaming CSV files ===")
            rename_csv_files(output_dir, run_name, "single_shot")
            
            # Move JSON files to Raw Transcriptions folder
            print("\n=== Moving JSON files to Raw Transcriptions folder ===")
            move_json_files_to_shot_folder(output_dir, raw_transcriptions_dir, "Single Shot")
        
        else:  # Two shots
            print("\nTwo shots mode: Running first pass, then second pass using first pass results")
            
            # Select models for both passes upfront
            print("\n=== Model Selection ===")
            print("\nSelect model for first pass processing:")
            model1 = First_Shot.select_model()
            print("\nSelect model for second pass processing:")
            model2 = Second_Shot.select_model()
            
            # Create temporary processing directories
            temp_first_dir = run_output_dir / "temp_first"
            temp_second_dir = run_output_dir / "temp_second"
            temp_first_dir.mkdir(exist_ok=True)
            temp_second_dir.mkdir(exist_ok=True)
            
            # Run first shot
            print("\n=== Running First Pass ===")
            First_Shot.process_images(processing_folder, 
                          prompt_path, temp_first_dir, 
                          run_name, 
                          model_id=model1)
            print("\n=== Converting First Pass JSON files to CSV ===")
            convert_json_to_csv(str(temp_first_dir))
            
            # Find the batch JSON file from first shot
            batch_file = list(temp_first_dir.glob(f"{run_name}_first_shot_transcriptions_batch.json"))
            if not batch_file:
                print("Error: Could not find first shot batch JSON file. Skipping second shot.")
                return
            
            batch_json_path = batch_file[0]
            print(f"\nFound first shot batch JSON: {batch_json_path}")
            
            # Run second shot with the JSON file from first shot
            print("\n=== Running Second Pass using First Pass Results ===")
            
            # Process second shot using first shot results
            Second_Shot.process_with_first_shot(
            processing_folder, 
            prompt_path, 
            batch_json_path, 
            temp_second_dir, 
            run_name, 
            model_id=model2
            )
            
            # Convert second shot JSON files to CSV
            print("\n=== Converting Second Pass JSON files to CSV ===")
            convert_json_to_csv(str(temp_second_dir))
            
            # Rename and move CSV files to main run directory
            print("\n=== Renaming and moving CSV files ===")
            first_csv = rename_csv_files(temp_first_dir, run_name, "first_shot")
            second_csv = rename_csv_files(temp_second_dir, run_name, "second_shot")
            
            if first_csv:
                shutil.move(str(first_csv), str(run_output_dir / first_csv.name))
            if second_csv:
                shutil.move(str(second_csv), str(run_output_dir / second_csv.name))
            
            # Validate fields based on user settings
            if validation_settings['scientific_names']:
                print("\n=== Validating Scientific Names ===")
                for csv_file in run_output_dir.glob('*.csv'):
                    validate_csv_scientific_names(csv_file)
            else:
                print("\n=== Skipping Scientific Names Validation (disabled by user) ===")
            
            if validation_settings['duplicate_records']:
                print("\n=== Validating Duplicate Records ===")
                for csv_file in run_output_dir.glob('*.csv'):
                    validate_csv_duplicate_records(csv_file)
            else:
                print("\n=== Skipping Duplicate Records Validation (disabled by user) ===")
            
            if validation_settings['duplicate_entries']:
                print("\n=== Validating Duplicate Entries (Collector, Date, CollID) ===")
                for csv_file in run_output_dir.glob('*.csv'):
                    validate_csv_entries(csv_file)
            else:
                print("\n=== Skipping Duplicate Entries Validation (disabled by user) ===")
            
            # Future validation types can be added here:
            # if validation_settings['genus_species']:
            #     print("\n=== Validating Genus/Species ===")
            #     for csv_file in run_output_dir.glob('*.csv'):
            #         validate_genus_species(csv_file)
            
            # Move JSON files to shot-specific folders in Raw Transcriptions
            print("\n=== Moving JSON files to Raw Transcriptions folders ===")
            move_json_files_to_shot_folder(temp_first_dir, raw_transcriptions_dir, "First Shot")
            move_json_files_to_shot_folder(temp_second_dir, raw_transcriptions_dir, "Second Shot")
            
            # Clean up temporary directories
            shutil.rmtree(temp_first_dir)
            shutil.rmtree(temp_second_dir)
        
        print("\nTranscription and CSV conversion completed, Thank you!")
        
        # Generate and save cost analysis report directly to run directory
        print("\n=== Generating Cost Analysis Report ===")
        cost_tracker.save_report_to_desktop(run_name, target_dir=str(run_output_dir))
        
    except Exception as e:
        print(f"\nError during transcription process: {str(e)}")
        # Still generate cost report even if there was an error
        print("\n=== Generating Cost Analysis Report ===")
        cost_tracker.save_report_to_desktop(run_name, target_dir=str(run_output_dir))

if __name__ == "__main__":
    main()

