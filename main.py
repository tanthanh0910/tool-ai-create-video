#!/usr/bin/env python3
"""
AI Video Generator - Tool tạo + cắt video.

Chế độ:
  1. Tạo video AI từ prompt (Ollama + HuggingFace + Edge TTS)
  2. Cắt video từ URL hoặc file local thành nhiều đoạn ngắn

Usage:
    python main.py                         # Interactive menu
    python main.py generate "chủ đề" -n 3  # Tạo 3 video AI
    python main.py split video.mp4 -n 5    # Cắt file thành 5 phần
    python main.py split "URL" -s 60       # Cắt video URL mỗi 60s
"""

import argparse
import asyncio
import time
from rich.console import Console
from rich.panel import Panel

from pipeline import run_pipeline
from generators.video_splitter import split_pipeline

console = Console()


def print_banner():
    console.print(
        Panel.fit(
            "[bold cyan]AI VIDEO TOOL[/]\n"
            "[dim]Tao video AI + Cat video tu URL/file[/]\n\n"
            "[green]1.[/] Tao video AI tu prompt\n"
            "[green]2.[/] Cat video tu URL hoac file local",
            border_style="cyan",
        )
    )


async def interactive_mode():
    """Che do tuong tac - menu lua chon."""
    while True:
        print_banner()
        console.print("\n[bold]Chon che do (1/2, hoac 'q' de thoat):[/]")
        choice = input("> ").strip()

        if choice.lower() in ("quit", "exit", "q"):
            console.print("[dim]Bye![/]")
            break

        if choice == "1":
            await mode_generate_interactive()
        elif choice == "2":
            await mode_split_interactive()
        else:
            console.print("[red]Vui long chon 1 hoac 2[/]")


async def mode_generate_interactive():
    """Tao video AI - interactive."""
    console.print("\n[bold cyan]== TAO VIDEO AI ==[/]")
    console.print("[bold]Nhap chu de video:[/]")
    prompt = input("> ").strip()
    if not prompt:
        return

    console.print("[bold]So luong video (default: 3):[/]")
    num_input = input("> ").strip()
    num_videos = int(num_input) if num_input.isdigit() else 3

    await run_pipeline(prompt, num_videos)


async def mode_split_interactive():
    """Cat video - interactive."""
    console.print("\n[bold cyan]== CAT VIDEO ==[/]")
    console.print("[bold]Nhap URL video hoac duong dan file:[/]")
    console.print("[dim]  VD: https://youtube.com/watch?v=xxx[/]")
    console.print("[dim]  VD: /Users/admin/video.mp4[/]")
    source = input("> ").strip()
    if not source:
        return

    console.print("\n[bold]Cach cat video:[/]")
    console.print("  [green]1.[/] Cat thanh N phan bang nhau")
    console.print("  [green]2.[/] Cat theo thoi luong (moi X giay)")
    split_choice = input("> ").strip()

    num_parts = None
    segment_seconds = None

    if split_choice == "1":
        console.print("[bold]So phan muon cat (default: 5):[/]")
        n = input("> ").strip()
        num_parts = int(n) if n.isdigit() else 5
    else:
        console.print("[bold]Moi doan bao nhieu giay (default: 60):[/]")
        s = input("> ").strip()
        segment_seconds = int(s) if s.isdigit() else 60

    start = time.time()
    console.print("\n[bold yellow]Dang xu ly...[/]")
    segments = await split_pipeline(source, num_parts, segment_seconds)
    elapsed = time.time() - start

    console.print(f"\n[bold green]{'=' * 50}[/]")
    console.print(f"[bold]Cat thanh {len(segments)} doan trong {elapsed:.1f}s[/]")
    for path in segments:
        console.print(f"  -> {path}")
    console.print(f"[bold green]{'=' * 50}[/]\n")


async def main():
    parser = argparse.ArgumentParser(
        description="AI Video Tool - Tao video AI + Cat video"
    )
    subparsers = parser.add_subparsers(dest="command")

    # Command: generate
    gen_parser = subparsers.add_parser("generate", help="Tao video AI tu prompt")
    gen_parser.add_argument("prompt", help="Chu de video")
    gen_parser.add_argument("--num", "-n", type=int, default=3, help="So video (default: 3)")

    # Command: split
    split_parser = subparsers.add_parser("split", help="Cat video tu URL/file")
    split_parser.add_argument("source", help="URL video hoac duong dan file local")
    split_parser.add_argument("--num", "-n", type=int, default=None, help="Cat thanh N phan")
    split_parser.add_argument("--seconds", "-s", type=int, default=None, help="Moi doan X giay")

    args = parser.parse_args()

    if args.command == "generate":
        print_banner()
        await run_pipeline(args.prompt, args.num)
    elif args.command == "split":
        print_banner()
        start = time.time()
        console.print("\n[bold yellow]Dang xu ly...[/]")
        segments = await split_pipeline(
            args.source,
            num_parts=args.num,
            segment_seconds=args.seconds,
        )
        elapsed = time.time() - start
        console.print(f"\n[bold green]{'=' * 50}[/]")
        console.print(f"[bold]Cat thanh {len(segments)} doan trong {elapsed:.1f}s[/]")
        for path in segments:
            console.print(f"  -> {path}")
        console.print(f"[bold green]{'=' * 50}[/]\n")
    else:
        await interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())
