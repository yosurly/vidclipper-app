import streamlit as st
from moviepy.editor import VideoFileClip, concatenate_videoclips
import tempfile
import pandas as pd
import os

st.title("🎬 VidClipper - 動画を切り出してつなげるツール")
st.write("動画ファイル（MP4など）と、切り出し時間を記載したCSVをアップロードしてください。")

# ファイルアップロード
video_file = st.file_uploader("動画ファイルをアップロード", type=["mp4", "mov", "avi", "mkv"])
csv_file = st.file_uploader("CSVファイルをアップロード（start,end）", type="csv")

# 実行ボタン
if st.button("切り出して結合"):
    if video_file is None or csv_file is None:
        st.error("両方のファイルをアップロードしてください。")
    else:
        # 一時ファイルとして保存
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
            tmp_video.write(video_file.read())
            video_path = tmp_video.name

        df = pd.read_csv(csv_file)
        segments = []
        for i, row in df.iterrows():
            try:
                start = sum(x * int(t) for x, t in zip([3600, 60, 1], row["start"].split(":")[-3:]))
                end = sum(x * int(t) for x, t in zip([3600, 60, 1], row["end"].split(":")[-3:]))
                segments.append((start, end))
            except:
                st.warning(f"行 {i+1} の時間形式が無効です: {row}")
        
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
                valid_clips.append(clip)

            if not valid_clips:
                st.error("有効な切り出し区間がありません。CSVを確認してください。")
            else:
                final = concatenate_videoclips(valid_clips, method="compose")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as out:
                    output_path = out.name
                    final.write_videofile(output_path, codec="libx264", audio_codec="aac")

                with open(output_path, "rb") as f:
                    st.download_button("📥 ダウンロード - 結合動画", f, file_name="vidclipper_output.mp4")

        except Exception as e:
            st.error(f"処理中にエラーが発生しました: {e}")
