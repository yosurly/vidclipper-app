import streamlit as st
from moviepy.editor import VideoFileClip, concatenate_videoclips
import tempfile
import pandas as pd
import os
import requests

st.title("🎬 VidClipper - 映像＋音声も自然につなぐ動画編集ツール（CSV不要版）")

# 入力方式選択
input_method = st.radio("動画ファイルの入力方法を選んでください：", ["ファイルをアップロード", "URLを入力"], index=0)
video_path = None

# 動画取得
if input_method == "ファイルをアップロード":
    video_file = st.file_uploader("動画ファイル（MP4など）をアップロード", type=["mp4", "mov", "avi", "mkv"])
    if video_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
            tmp_video.write(video_file.read())
            video_path = tmp_video.name
elif input_method == "URLを入力":
    video_url = st.text_input("動画ファイルのURLを入力してください（Dropboxリンクは ?dl=1 に）")
    if video_url and st.button("URLから動画を取得"):
        try:
            if "dropbox.com" in video_url and "dl=0" in video_url:
                video_url = video_url.replace("dl=0", "dl=1")
            response = requests.get(video_url, stream=True, timeout=10)
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_video.write(chunk)
                video_path = tmp_video.name
            st.success("✅ 動画を正常にダウンロードしました")
        except Exception as e:
            st.error(f"❌ 動画のダウンロードに失敗しました: {e}")

# ハイフン区切りによる切り出し時間の入力欄
st.markdown("### ✂️ 切り出し区間（1行に1区間、`開始-終了` 形式、例: `00:01:00-00:02:30`）")
time_text = st.text_area("切り出し時間を以下に入力してください：", height=150)

# 実行処理
if video_path and time_text and st.button("切り出して結合"):
    lines = [line.strip() for line in time_text.strip().split("\n") if line.strip()]
    segments = []
    parse_error = False

    for i, line in enumerate(lines):
        if "-" not in line:
            st.error(f"❌ {i+1}行目にハイフン `-` がありません: 「{line}」")
            parse_error = True
            continue
        parts = line.split("-")
        if len(parts) != 2:
            st.error(f"❌ {i+1}行目が不正です（開始-終了 の形式）: 「{line}」")
            parse_error = True
            continue
        try:
            start = sum(x * int(t) for x, t in zip([3600, 60, 1], parts[0].split(":")[-3:]))
            end = sum(x * int(t) for x, t in zip([3600, 60, 1], parts[1].split(":")[-3:]))
            segments.append((start, end))
        except:
            st.error(f"❌ {i+1}行目の時間形式が無効です: 「{line}」")
            parse_error = True

    if not parse_error:
        try:
            video = VideoFileClip(video_path)
            video_duration = video.duration
            valid_clips = []

            for start, end in segments:
                if start >= video_duration:
                    continue
                if end > video_duration:
                    end = video_duration
                clip = video.subclip(start, end)
                clip = clip.fadein(0.5).fadeout(0.5)
                if clip.audio:
                    clip.audio = clip.audio.audio_fadein(0.5).audio_fadeout(0.5)
                valid_clips.append(clip)

            if not valid_clips:
                st.error("有効な切り出し区間がありません。")
            else:
                final = concatenate_videoclips(valid_clips, method="compose")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as out:
                    output_path = out.name
                    final.write_videofile(output_path, codec="libx264", audio_codec="aac")

                with open(output_path, "rb") as f:
                    st.download_button("📥 ダウンロード - 結合動画（音声フェード付き）", f, file_name="vidclipper_output.mp4")

        except Exception as e:
            st.error(f"処理中にエラーが発生しました: {e}")
