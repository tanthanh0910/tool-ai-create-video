#!/usr/bin/env python3
"""
Test script để kiểm tra Edge TTS hoạt động đúng.
Tạo audio cho nhiều động vật và kiểm tra nội dung.
"""

import asyncio
import edge_tts
import os
import subprocess
import hashlib

TTS_VOICE = "vi-VN-HoaiMyNeural"
TEST_DIR = "/Users/admin/Documents/video/temp/tts_test"


def get_duration(file_path: str) -> float:
    """Lấy duration của file audio."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except:
        return 0


async def test_single_tts(text: str, output_path: str) -> dict:
    """Test tạo 1 file TTS."""
    print(f"\n{'='*60}")
    print(f"Text: {text}")
    print(f"Output: {output_path}")
    
    # Xóa file cũ nếu có
    if os.path.exists(output_path):
        os.remove(output_path)
    
    # Tạo TTS mới
    communicate = edge_tts.Communicate(
        text=text,
        voice=TTS_VOICE,
        rate="-20%",
    )
    await communicate.save(output_path)
    
    # Verify
    if os.path.exists(output_path):
        size = os.path.getsize(output_path)
        duration = get_duration(output_path)
        with open(output_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        print(f"✓ Size: {size} bytes")
        print(f"✓ Duration: {duration:.2f}s")
        print(f"✓ MD5: {file_hash}")
        
        return {
            "text": text,
            "path": output_path,
            "size": size,
            "duration": duration,
            "hash": file_hash,
        }
    else:
        print("✗ Failed to create file")
        return None


async def main():
    """Test TTS cho nhiều động vật."""
    os.makedirs(TEST_DIR, exist_ok=True)
    
    animals = ["sư tử", "voi", "cá heo", "hổ", "gấu trúc"]
    
    results = []
    
    # Test từng con vật một cách TUẦN TỰ (không parallel)
    for i, animal in enumerate(animals):
        text = f"Đây là ... {animal}."
        output = os.path.join(TEST_DIR, f"{i+1:02d}_{animal.replace(' ', '_')}.mp3")
        result = await test_single_tts(text, output)
        if result:
            results.append(result)
        
        # Đợi 1 giây giữa các request
        await asyncio.sleep(1)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY:")
    print(f"{'='*60}")
    for r in results:
        print(f"{r['path']}")
        print(f"  Text: {r['text']}")
        print(f"  Hash: {r['hash']}")
        print()
    
    print(f"\nCác file được lưu tại: {TEST_DIR}")
    print("Hãy mở và nghe từng file để xác nhận nội dung đúng!")


if __name__ == "__main__":
    asyncio.run(main())
