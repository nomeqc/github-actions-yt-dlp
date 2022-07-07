down_file(){
    url=$1
    filename=$2
    echo "下载：$url"
    curl -# -Lfo "$filename" "$url"
    echo ""
    chmod a+rx "$filename"
}

mkdir -p "$TOOLS_PATH"

script_dir="$(cd $(dirname "${BASH_SOURCE[0]}") || exit; pwd)"

# 将tools目录添加进PATH
echo "$(cd "$TOOLS_PATH" || exit; pwd)" >> $GITHUB_PATH

# 安装python依赖
if [[ -f ${MAIN_REPO}/requirements.txt ]]; then pip install -r ${MAIN_REPO}/requirements.txt; fi

# 下载ffmpeg
if [[ "$TOOLS_CACHE_HIT" != "true" ]]; then
    down_file "https://github.com/Nomeqc/my-release/releases/download/ffmpeg/ffmpeg" "$TOOLS_PATH/ffmpeg"
    down_file "https://github.com/Nomeqc/my-release/releases/download/ffmpeg/ffprobe" "$TOOLS_PATH/ffprobe"
fi

# 下载yt-dlp
down_file "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp" "/usr/local/bin/yt-dlp"
