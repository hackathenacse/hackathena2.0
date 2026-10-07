import shutil
import subprocess
from pathlib import Path

brain_dir = Path(r"C:\Users\MELVIN\.gemini\antigravity-ide\brain\5fd4bb46-bd37-4d4a-9986-4fb3035847ff")
media_dir = Path("demo/media").resolve()
media_dir.mkdir(parents=True, exist_ok=True)

# Copy generated face portraits
face_mapping = {
    "authentic_face.jpg": brain_dir / "spokesperson_authentic_1791278482967.jpg",
    "deepfake_face.jpg": brain_dir / "deepfake_synthetic_avatar_1791278525909.jpg",
    "ceo_face.jpg": brain_dir / "ceo_businessman_1791278508876.jpg",
}

for dest_name, src_path in face_mapping.items():
    dest_path = media_dir / dest_name
    if src_path.exists():
        shutil.copy2(src_path, dest_path)
        print(f"Copied {src_path.name} -> {dest_path.name}")

clips = [
    {
        "name": "authentic_sample",
        "speech": "Welcome to today general product demonstration. All system components are functioning as expected.",
        "image": media_dir / "authentic_face.jpg",
    },
    {
        "name": "deepfake_sample",
        "speech": "Hello, this is a video analysis verification sample for forensic media testing.",
        "image": media_dir / "deepfake_face.jpg",
    },
    {
        "name": "scam_ceo_wire",
        "speech": "This is the CEO speaking. We have an urgent acquisition deal. Transfer funds immediately to the new account number and keep this strictly confidential.",
        "image": media_dir / "ceo_face.jpg",
    },
]

for clip in clips:
    wav_path = media_dir / f"{clip['name']}.wav"
    mp4_path = media_dir / f"{clip['name']}.mp4"
    img_path = clip["image"]

    # 1. Synthesize audio
    ps_script = f"""
    Add-Type -AssemblyName System.Speech
    $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $s.SetOutputToWaveFile('{wav_path.as_posix()}')
    $s.Speak('{clip["speech"]}')
    $s.Dispose()
    """
    subprocess.run(["powershell", "-Command", ps_script], check=True)

    # 2. Encode video clip with realistic face frames
    # Scale image to 640x640 with subtle pan/framing
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-loop", "1", "-i", str(img_path.resolve()),
        "-i", str(wav_path.resolve()),
        "-vf", "scale=640:640:force_original_aspect_ratio=decrease,pad=640:640:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "128k",
        "-t", "9",
        str(mp4_path.resolve())
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    print(f"Successfully created face-enabled demo video: {mp4_path.name}")

print("Demo clips generation complete with human face frames.")
