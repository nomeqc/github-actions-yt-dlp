import argparse
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Tuple

from aliyundrive_client import AliyundriveClient, AliyunDriveSessionManager
from dingtalk import send_dingtalk_message


def runcmd(cmd, shell=False):
    try:
        import shlex
        import subprocess
        args = cmd if shell else shlex.split(cmd)
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell)
        stdout, stderr = process.communicate()
        output = stdout + stderr
        output = output.rstrip(b'\n').rstrip(b'\r')
        if shell:
            try:
                import locale
                output = output.decode(locale.getpreferredencoding(False))
            except Exception:
                output = output.decode('UTF-8', errors='ignore')
        else:
            output = output.decode('UTF-8', errors='ignore')
        returncode = process.returncode
    except Exception as e:
        output = str(e)
        returncode = 2
    return output, returncode


def get_video_resolution(video_file: str) -> Tuple[int, int]:
    """获取视频分辨率

    Args:
        video_file (str): 视频文件路径

    Returns:
        Tuple[int, int]: 返回 (宽, 高)
    """
    cmd = f'ffprobe -v error -select_streams v:0 -show_entries stream=height,width -of csv=s=x:p=0 "{video_file}"'
    output, returncode = runcmd(cmd)
    if returncode != 0:
        raise Exception(output)
    output = output.splitlines()[0]
    return tuple([int(item) for item in output.split('x')])


def run(url, res, dir, drive_dir):
    output_template = os.path.join(dir, '%(title)s.%(ext)s')
    '''
        下载指定分辨率以内的最好视频，帧率30以上，
        如果没有帧率大于30的视频，则选择最差的视频(仍优先选择帧率大于30的视频
    '''
    # cmd = f'yt-dlp -f "((bv*[fps>30]/bv*)[height<={res}][ext=mp4]/(wv*[fps>30][ext=mp4]/wv*)) + ba[ext=m4a] / (b[fps>30]/b)[height<={res}][ext=mp4]/(w[fps>30]/w)" -o "{output_template}" "{url}"'
    # 指定分辨率 并发2
    cmd = f'yt-dlp -f "bv + ba / b / w" -S "res:{res}" -o "{output_template}" "{url}" --merge-output-format mp4 -N 3'
    print(f'执行命令：{cmd}')
    code = os.system(cmd)
    if code != 0:
        raise Exception('出错了！')
    filepath = list(Path(dir).glob('*'))[0]
    w, h = get_video_resolution(str(filepath))
    res_names = {
        '3840x2160': '2160p',
        '2560x1440': '1440p',
        '1920x1080': '1080p',
        '1280x720': '720p',
        '854x480': '480p',
        '640x360': '360p',
        '426x240': '240p',
    }
    res_name = res_names.get(f'{w}x{h}')
    res_name = f'{res_name}' if res_name else f'{w}x{h}'

    filepath = filepath.rename(Path(dir, f'{filepath.stem}_{res_name}{filepath.suffix}'))
    path_in_drive = Path(drive_dir, Path(filepath).name).as_posix()
    try:
        sessionManager = AliyunDriveSessionManager()
        client = AliyundriveClient(access_token=sessionManager.access_token)
        client.upload_file(str(filepath), drive_dir, check_name_mode='overwrite')
        message = f'【y2b-upload-aliyundrive】文件已上传到"{path_in_drive}"✔️'
        send_dingtalk_message(message)
    except Exception as e:
        error = f'【y2b-upload-aliyundrive】无法上传文件到"{path_in_drive}"：\n❌{str(e)}'
        send_dingtalk_message(error)
    

def parse_inputs():
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help='请输入youtube视频地址')
    parser.add_argument('res', help='请输入分辨率。支持的分辨率有：1080p 720p 480p 360p')
    parser.add_argument('drive_dir', help='请输入文件上传的目标网盘目录')
    args = parser.parse_args()
    return args


def main():
    args = parse_inputs()
    url = args.url
    drive_dir = args.drive_dir
    res_map = {'1080p': '1080', '720p': '720', '480p': '480', '360p': '360'}
    res = res_map.get(args.res, '1080')
    with TemporaryDirectory(prefix='downloads_', dir=os.path.realpath('.')) as tmpdir:
        run(url, res, tmpdir, drive_dir)


if __name__ == '__main__':
    main()
