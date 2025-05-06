import streamlit as st
from moviepy.editor import VideoFileClip, concatenate_videoclips
import tempfile
import os
import requests

# セッション状態初期化
if "processing" not in st.session_state:
    st.session_state["processing"] = False
processing = st.session_state["processing"]

# タイトル（大きめ）
st.markdown("<h1 style='font-size: 32px;'>VidClipper – 指定された区間の映像や音声を抜き出しシームレスにつなぎます</h1>", unsafe_allow_html=True)

# 動画ファイルの入力
st.markdown("<h3 style='margin-top: 2em;'>動画・音声ファイル：</h3>", unsafe_allow_html=True)
input_method = st.radio("", ["ファイル", "URL（Dropboxリンクは ?dl=1 に）"], index=0)

video_path = None
uploaded_filename = ""
video_url = ""

if input_method == "ファイル":
    video_file = st.file_uploader("", type=["mp4", "mov", "avi", "mkv", "webm"])
    if video_file:
        uploaded_filename = video_file.name
        st.text(f"ファイル名：{uploaded_filename}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
            tmp_video.write(video_file.read())
            video_path = tmp_video.name
else:
    video_url = st.text_input("動画ファイルのURLを入力してください：")
    if video_url:
        st.text(f"入力されたURL：{video_url}")
    if video_url and st.button("URLから動画を取得", disabled=processing):
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

# 切り出し区間
st.markdown("<h3 style='margin-top: 2em;'>切り出し区間：</h3>", unsafe_allow_html=True)
st.markdown("１行１区間で ”開始時間-終了時間”（例．00:01:00-00:30:00）", unsafe_allow_html=True)
time_text = st.text_area("", height=150)

# 実行ボタン
run_button = st.button("実行", disabled=processing)

# 処理本体
if video_path and time_text and run_button:
    st.session_state["processing"] = True
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
                clip = video.subclip(start, end).fadein(0.5).fadeout(0.5)
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
                    st.download_button("ダウンロード", f, file_name="vidclipper_output.mp4")

        except Exception as e:
            st.error(f"処理中にエラーが発生しました: {e}")

    st.session_state["processing"] = False
