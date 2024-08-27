import os
import zipfile
import rarfile
import patoolib
import tkinter as tk
from tkinter import filedialog, messagebox


def extract_zip(file_path, extract_path):
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)


def extract_rar(file_path, extract_path):
    patoolib.extract_archive(file_path, outdir=extract_path)


def batch_extract(source_dir, target_dir):
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith(('.zip', '.rar')):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(root, source_dir)
                extract_path = os.path.join(target_dir, relative_path)

                if not os.path.exists(extract_path):
                    os.makedirs(extract_path)

                try:
                    if file.lower().endswith('.zip'):
                        extract_zip(file_path, extract_path)
                    elif file.lower().endswith('.rar'):
                        extract_rar(file_path, extract_path)
                    print(f"Extracted: {file}")
                except Exception as e:
                    print(f"Error extracting {file}: {str(e)}")


def select_source_directory():
    return filedialog.askdirectory(title="Select Source Directory")


def select_target_directory():
    return filedialog.askdirectory(title="Select Target Directory")


def start_extraction():
    source_dir = select_source_directory()
    if not source_dir:
        return

    target_dir = select_target_directory()
    if not target_dir:
        return

    batch_extract(source_dir, target_dir)
    messagebox.showinfo("Extraction Complete", "All files have been extracted.")


# Create the main window
root = tk.Tk()
root.title("Batch Extractor")
root.geometry("300x100")

# Create and pack the button
extract_button = tk.Button(root, text="Start Batch Extraction", command=start_extraction)
extract_button.pack(expand=True)

# Start the GUI event loop
root.mainloop()