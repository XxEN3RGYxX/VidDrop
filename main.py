import os
import sys
import threading
import tempfile
import shutil
import subprocess
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from yt_dlp import YoutubeDL

# GUI appearance
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

download_folder = os.getcwd()
download_thread = None
download_cancelled = False
history = []

# ffmpeg path setup
if getattr(sys, 'frozen', False):
    current_dir = sys._MEIPASS
    bundled_ffmpeg = os.path.join(current_dir, "ffmpeg.exe")
    bundled_ffprobe = os.path.join(current_dir, "ffprobe.exe")
    temp_ffmpeg_path = os.path.join(tempfile.gettempdir(), "ffmpeg.exe")
    temp_ffprobe_path = os.path.join(tempfile.gettempdir(), "ffprobe.exe")
    if not os.path.exists(temp_ffmpeg_path):
        shutil.copyfile(bundled_ffmpeg, temp_ffmpeg_path)
    if not os.path.exists(temp_ffprobe_path):
        shutil.copyfile(bundled_ffprobe, temp_ffprobe_path)
    ffmpeg_path = temp_ffmpeg_path
    ffprobe_path = temp_ffprobe_path
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    ffmpeg_path = os.path.join(current_dir, "ffmpeg.exe")
    ffprobe_path = os.path.join(current_dir, "ffprobe.exe")

if os.path.exists(ffmpeg_path):
    os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg_path)
if os.path.exists(ffprobe_path):
    os.environ["PATH"] += os.pathsep + os.path.dirname(ffprobe_path)

def check_ffmpeg_ffprobe():
    try:
        subprocess.run([ffmpeg_path, "-version"], capture_output=True, text=True)
        subprocess.run([ffprobe_path, "-version"], capture_output=True, text=True)
    except Exception as e:
        print("Error running ffmpeg/ffprobe:", e)

check_ffmpeg_ffprobe()

def choose_folder():
    global download_folder
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        download_folder = folder_selected
        folder_label.configure(text=download_folder)

def update_history():
    history_textbox.delete("1.0", ctk.END)
    for url in history:
        history_textbox.insert(ctk.END, url + "\n")

def cancel_download():
    global download_cancelled
    download_cancelled = True
    cancel_button.configure(state="disabled")
    status_label.configure(text="Cancelling...")

def download():
    global download_thread, download_cancelled

    url = url_entry.get().strip()
    file_name = filename_entry.get().strip()
    format_type = format_var.get()

    if not url:
        messagebox.showerror("Error", "Please enter a valid URL.")
        return

    if download_thread and download_thread.is_alive():
        messagebox.showwarning("Download in progress", "Please wait or cancel the current download.")
        return

    if url not in history:
        history.append(url)
        update_history()

    download_button.configure(state="disabled")
    cancel_button.configure(state="normal")
    progress_bar.set(0)
    status_label.configure(text="Downloading...")
    download_cancelled = False

    download_thread = threading.Thread(target=lambda: download_yt(url, format_type, file_name))
    download_thread.start()

def download_yt(url, format_type, file_name):
    global download_cancelled

    def hook(d):
        if download_cancelled:
            raise Exception("Download cancelled by user")
        if d['status'] == 'downloading':
            percent_str = d.get('_percent_str', '').strip()
            try:
                percent = float(percent_str.replace('%', ''))
                root.after(0, lambda: progress_bar.set(percent / 100))
            except:
                pass
        elif d['status'] == 'finished':
            def finish():
                progress_bar.set(1)
                status_label.configure(text="Download completed!")
                download_button.configure(state="normal")
                cancel_button.configure(state="disabled")
            root.after(0, finish)

    format_str = 'bestvideo+bestaudio/best' if format_type == "Video" else 'bestaudio/best'

    outtmpl_pattern = os.path.join(download_folder, file_name + '.%(ext)s') if file_name else os.path.join(download_folder, '%(playlist_index)s - %(title)s.%(ext)s')

    options = {
        'progress_hooks': [hook],
        'outtmpl': outtmpl_pattern,
        'format': format_str,
        'ffmpeg_location': os.path.dirname(ffmpeg_path),
        'quiet': True,
        'no_warnings': True,
    }

    if format_type == "Audio":
        options.update({
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        options.update({
            'merge_output_format': 'mp4',
        })

    try:
        with YoutubeDL(options) as ydl:
            ydl.download([url])
    except Exception as e:
        if "cancelled" in str(e).lower():
            root.after(0, lambda: status_label.configure(text="Download cancelled."))
        else:
            root.after(0, lambda: messagebox.showerror("Error", str(e)))
            root.after(0, lambda: status_label.configure(text="Download error."))
    finally:
        def reset_buttons():
            download_button.configure(state="normal")
            cancel_button.configure(state="disabled")
        root.after(0, reset_buttons)

def on_format_change():
    quality_menu.configure(state="disabled")

# GUI Setup
root = ctk.CTk()
root.title("VidDrop")
root.geometry("700x500")

# Disable right-click globally on all widgets and window
root.bind_all("<Button-3>", lambda e: "break")
root.bind_all("<Button-2>", lambda e: "break")

frame = ctk.CTkFrame(root)
frame.pack(padx=20, pady=20, fill="both", expand=True)

url_label = ctk.CTkLabel(frame, text="Enter URL:")
url_label.pack(anchor="w", pady=(0, 5))

url_entry = ctk.CTkEntry(frame, width=600)
url_entry.pack(anchor="w", pady=(0, 10))

filename_label = ctk.CTkLabel(frame, text="File name (optional):")
filename_label.pack(anchor="w", pady=(0, 5))

filename_entry = ctk.CTkEntry(frame, width=600)
filename_entry.pack(anchor="w", pady=(0, 10))

format_var = ctk.StringVar(value="Video")

format_frame = ctk.CTkFrame(frame)
format_frame.pack(anchor="w", pady=(0, 10))

ctk.CTkLabel(format_frame, text="Format:").pack(side="left")

video_rb = ctk.CTkRadioButton(format_frame, text="Video", variable=format_var, value="Video", command=on_format_change)
video_rb.pack(side="left", padx=10)

audio_rb = ctk.CTkRadioButton(format_frame, text="Audio", variable=format_var, value="Audio", command=on_format_change)
audio_rb.pack(side="left")

quality_frame = ctk.CTkFrame(frame)
quality_frame.pack(anchor="w", pady=(0, 10))

ctk.CTkLabel(quality_frame, text="Quality:").pack(side="left")

quality_var = ctk.StringVar(value="Best available quality")
quality_menu = ctk.CTkOptionMenu(quality_frame, variable=quality_var, values=["Best available quality"])
quality_menu.pack(side="left", padx=10)
quality_menu.configure(state="disabled")

folder_button = ctk.CTkButton(frame, text="Choose folder", command=choose_folder)
folder_button.pack(anchor="w", pady=(0, 10))

folder_label = ctk.CTkLabel(frame, text=download_folder)
folder_label.pack(anchor="w", pady=(0, 10))

download_button = ctk.CTkButton(frame, text="Download", command=download)
download_button.pack(anchor="w", pady=(0, 10))

cancel_button = ctk.CTkButton(frame, text="Cancel", command=cancel_download, state="disabled")
cancel_button.pack(anchor="w", pady=(0, 10))

progress_bar = ctk.CTkProgressBar(frame, width=600)
progress_bar.pack(anchor="w", pady=(0, 10))

status_label = ctk.CTkLabel(frame, text="Waiting...")
status_label.pack(anchor="w", pady=(0, 10))

history_label = ctk.CTkLabel(frame, text="URL History:")
history_label.pack(anchor="w", pady=(10, 5))

history_textbox = ctk.CTkTextbox(frame, height=5)
history_textbox.pack(fill="both", expand=True)

update_history()
on_format_change()

root.mainloop()






























