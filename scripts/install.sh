mkdir -p $TOOLS_PATH
# 将tools目录添加进PATH
echo "$(cd $TOOLS_PATH; pwd)" >> $GITHUB_PATH
# 安装python依赖
if [[ -f requirements.txt ]]; then pip install -r requirements.txt; fi
# 下载ffmpeg
if [[ "$TOOLS_CACHE_HIT" != "true" ]]; then
    curl -Lfo $TOOLS_PATH/ffmpeg https://github.com/Nomeqc/my-release/releases/download/ffmpeg/ffmpeg
    curl -Lfo $TOOLS_PATH/ffprobe https://github.com/Nomeqc/my-release/releases/download/ffmpeg/ffprobe
    chmod a+rx $TOOLS_PATH/ffmpeg
    chmod a+rx $TOOLS_PATH/ffprobe
fi
# 下载yt-dlp
curl -Lfo /usr/local/bin/yt-dlp https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp
chmod a+rx /usr/local/bin/yt-dlp
