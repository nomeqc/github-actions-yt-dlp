mkdir -p "$TOOLS_PATH"
# 将tools目录添加进PATH
echo "$(cd "$TOOLS_PATH" || exit; pwd)" >> $GITHUB_PATH
# 安装python依赖
if [[ -f requirements.txt ]]; then pip install -r requirements.txt; fi

ffmpeg_url="https://github.com/Nomeqc/my-release/releases/download/ffmpeg/ffmpeg"
ffprobe_url="https://github.com/Nomeqc/my-release/releases/download/ffmpeg/ffprobe"
ytdlp_url="https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
# 下载ffmpeg
if [[ "$TOOLS_CACHE_HIT" != "true" ]]; then
    echo "下载：$ffmpeg_url"
    curl -# -Lfo "$TOOLS_PATH/ffmpeg" "$ffmpeg_url"
    echo "下载：$ffprobe_url"
    curl -# -Lfo "$TOOLS_PATH/ffprobe" "$ffprobe_url"
    chmod a+rx "$TOOLS_PATH/ffmpeg"
    chmod a+rx "$TOOLS_PATH/ffprobe"
fi
# 下载yt-dlp
echo "下载：$ytdlp_url"
curl -# -Lfo /usr/local/bin/yt-dlp "$ytdlp_url"
chmod a+rx /usr/local/bin/yt-dlp
