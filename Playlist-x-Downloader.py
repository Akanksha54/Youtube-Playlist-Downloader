import os
import sys
import time
import threading
from math import ceil
from tqdm import tqdm
from colorama import Fore, Style, init
import yt_dlp

# Initialize colorama
init(autoreset=True)

BANNER_FILE = 'banner.txt'


class DownloadProgress:
    def __init__(self):
        self.pbar = None

    def hook(self, d):
        if d['status'] == 'downloading':
            if self.pbar is None:
                self.pbar = tqdm(total=d.get('total_bytes', 0), unit='B', unit_scale=True, desc="Downloading", leave=False)
            self.pbar.update(d.get('downloaded_bytes', 0) - self.pbar.n)
        elif d['status'] == 'finished' and self.pbar:
            self.pbar.close()
            self.pbar = None


def fetch_playlist(url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'force_generic_extractor': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=False)
            if 'entries' in result:
                return result
            else:
                print(f"{Fore.RED}{Style.BRIGHT}Failed to fetch playlist: No entries found{Style.RESET_ALL}")
                sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}{Style.BRIGHT}Failed to fetch playlist: {e}{Style.RESET_ALL}")
        sys.exit(1)


def split_links(video_urls, chunk_size):
    for i in range(0, len(video_urls), chunk_size):
        yield video_urls[i:i + chunk_size]


def download_video(video_info, thread_name):
    progress = DownloadProgress()
    video_url = f"https://www.youtube.com/watch?v={video_info['id']}"
    ydl_opts = {
        'quiet': True,
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': '%(title)s.%(ext)s',
        'progress_hooks': [progress.hook]
    }
    try:
        print(f"    {Fore.CYAN}{thread_name} is downloading: {video_info['title']}{Style.RESET_ALL}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            start_time = time.time()
            ydl.download([video_url])
            end_time = time.time()
            filename = ydl.prepare_filename(video_info)
            file_size = os.path.getsize(filename)
            download_speed = file_size / (end_time - start_time) / 1024  # KB/s
            print(f"    {Fore.GREEN}{thread_name} --> {filename.split('/')[-1]} Downloaded at {download_speed:.2f} KB/s{Style.RESET_ALL}")
    except yt_dlp.utils.DownloadError as e:
        print(f"{Fore.RED}{Style.BRIGHT}Failed to download {video_info['title']} ({video_info['id']}): {str(e).split(': ')[-1]}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}{Style.BRIGHT}Unexpected error for {video_info['title']} ({video_info['id']}): {e}{Style.RESET_ALL}")


def downloader(video_infos, thread_name):
    for info in video_infos:
        download_video(info, thread_name)


def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner():
    try:
        with open(BANNER_FILE, 'r') as file:
            print(f"{Fore.RED}{Style.BRIGHT}{file.read()}{Style.RESET_ALL}")
    except FileNotFoundError:
        print(f"{Fore.RED}{Style.BRIGHT}Banner file not found.{Style.RESET_ALL}")


def main():
    clear_terminal()
    print_banner()
    print(f"{Style.BRIGHT}Enter Playlist URL: {Style.RESET_ALL}", end="")
    playlist_url = input().strip()

    playlist = fetch_playlist(playlist_url)
    playlist_name = playlist.get('title', 'Unknown Playlist')
    videos = playlist['entries']

    if not videos:
        print(f"{Fore.RED}{Style.BRIGHT}No videos found in the playlist.{Style.RESET_ALL}")
        sys.exit(1)

    print(f"\nPlaylist: {Fore.YELLOW}{playlist_name}{Style.RESET_ALL}")
    print(f"Playlist contains {len(videos)} videos.\n")
    print("Downloading Started...\n")

    num_threads = 4
    chunk_size = ceil(len(videos) / num_threads)
    video_chunks = list(split_links(videos, chunk_size))

    # Adjust the number of threads to the number of chunks if fewer chunks than threads
    num_threads = min(num_threads, len(video_chunks))

    threads = []
    for i in range(num_threads):
        thread_name = f"Thread-{i + 1}"
        t = threading.Thread(target=downloader, args=(video_chunks[i], thread_name), name=thread_name)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
