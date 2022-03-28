mkdir -p $TOOLS_PATH
curl -L https://github.com/Nomeqc/my-release/releases/download/ffmpeg/ffmpeg -o $TOOLS_PATH/ffmpeg
curl -L https://github.com/Nomeqc/my-release/releases/download/ffmpeg/ffprobe -o $TOOLS_PATH/ffprobe
chmod a+rx $TOOLS_PATH/ffmpeg
chmod a+rx $TOOLS_PATH/ffprobe
