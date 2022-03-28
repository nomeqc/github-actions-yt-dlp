mkdir -p bin
curl -L https://github.com/Nomeqc/my-release/releases/download/ffmpeg/ffmpeg -o bin/ffmpeg
curl -L https://github.com/Nomeqc/my-release/releases/download/ffmpeg/ffprobe -o bin/ffprobe
chmod a+rx bin/ffmpeg
chmod a+rx bin/ffprobe
# 将bin目录添加进PATH
echo "$(cd ./bin; pwd)" >> $GITHUB_PATH
