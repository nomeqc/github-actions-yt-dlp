import argparse
import asyncio
import base64
import datetime
import hashlib
import hmac
import json
import math
import mimetypes
import os
import sys
from random import choice
from urllib.parse import quote_plus

import aiohttp
import requests
import xmltodict



class MuseUploader():

    def __init__(self, filepath: str, transfer_token: str = "", concurrency: int = 3):
        self.filepath = filepath
        self.trunk_size = int(3 * 1024 * 1024)
        self.transfer_token = transfer_token
        self.concurrency = concurrency
        self.sem = None
        self.session = self.create_session()
        self.device_id = ''.join([choice("0123456789abcdef") for i in range(11)])
        self.create_info = {}
        self.token_info = {}
        self.oss_user_agent = 'aliyun-sdk-js/6.16.0 Chrome 98.0.4758.82 on Windows 10 64-bit'
        self.init_multipart_result = {}
        self.multipart_upload_record = {}
        self.debug = False

    def create_session(self):
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=3, pool_maxsize=3, max_retries=3)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def run(self):
        self.validate_token()
        self.create()
        self.get_upload_token()
        self.upload()
        self.add()
        self.finish()
        self.get_share_info()
        return self.create_info.get('code')

    def check_response(self, resp):
        resp.raise_for_status()
        data = resp.json()
        if int(data.get('code')) != 0:
            message = data.get('message')
            raise Exception(f'出错了！"{message}"')

    def validate_token(self):
        headers = {
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'sec-ch-ua': '"(Not(A:Brand";v="8", "Chromium";v="98", "Google Chrome";v="98"',
            'x-transfer-device': '51114e2794e',
            'x-transfer-token': self.transfer_token,
            'sec-ch-ua-mobile': '?0',
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36',
            'sec-ch-ua-platform': '"Windows"',
            'Accept': '*/*',
            'Origin': 'https://musetransfer.com',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://musetransfer.com/',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        response = requests.get('https://service.tezign.com/transfer/user/get', headers=headers)
        if not response.ok or int(response.json().get('code')) != 0:
            self.transfer_token = ''
        else:
            self.transfer_token = response.json().get('result', {}).get('token')

    def create(self):
        url = "https://service.tezign.com/transfer/share/create"
        title = os.path.basename(self.filepath)
        if len(title) > 50:
            title = title[:47] + '...'
        payload = {
            "title": title,
            "titleType": 0,
            "expire": "365",
            "customBackground": 0
        }
        headers = {
            'Connection': 'keep-alive',
            'sec-ch-ua': '"(Not(A:Brand";v="8", "Chromium";v="98", "Google Chrome";v="98"',
            'Accept': 'application/json',
            'x-transfer-device': self.device_id,
            'sec-ch-ua-mobile': '?0',
            'Content-Type': 'application/json;charset=UTF-8',
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36',
            'sec-ch-ua-platform': '"Windows"',
            'Origin': 'https://musetransfer.com',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://musetransfer.com/',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        if self.transfer_token:
            headers['x-transfer-token'] = self.transfer_token
        response = self.session.request("POST", url, headers=headers, data=json.dumps(payload))
        self.check_response(response)
        data = response.json()
        self.create_info = data.get('result')
        if self.debug:
            print(response.text)

    def make_digest(self, message, key):
        key = bytes(key, 'UTF-8')
        message = bytes(message, 'UTF-8')

        digester = hmac.new(key, message, hashlib.sha1)
        signature1 = digester.digest()

        signature2 = base64.b64encode(signature1)

        return str(signature2, 'UTF-8')

    def get_upload_token(self):
        url = "https://service.tezign.com/transfer/asset/getUploadToken"
        payload = {}
        headers = {
            'Connection': 'keep-alive',
            'sec-ch-ua': '"(Not(A:Brand";v="8", "Chromium";v="98", "Google Chrome";v="98"',
            'x-transfer-device': self.device_id,
            'sec-ch-ua-mobile': '?0',
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36',
            'sec-ch-ua-platform': '"Windows"',
            'Accept': '*/*',
            'Origin': 'https://musetransfer.com',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://musetransfer.com/',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        if self.transfer_token:
            headers['x-transfer-token'] = self.transfer_token
        response = self.session.request("GET", url, headers=headers, data=payload)
        self.check_response(response)
        data = response.json()
        self.token_info = data.get('result', {})
        if self.debug:
            print(response.text)

    def build_auth_headers(self, method: str, request_uri: str, content_md5: str = None, content_type: str = None):
        access_key_id = self.token_info.get('accessKeyId')
        security_token = self.token_info.get('securityToken')
        GMT_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'
        gmt_datetime_str = datetime.datetime.utcnow().strftime(GMT_FORMAT)
        arr = [
            f'{method.upper()}',
        ]
        if content_md5:
            arr.append(content_md5)
        else:
            arr.append('')
        if content_type:
            arr.append(content_type.lower())
        else:
            arr.append('')
        arr.append(gmt_datetime_str)
        arr.append(f'x-oss-date:{gmt_datetime_str}')
        arr.append(f'x-oss-security-token:{security_token}')
        arr.append(f'x-oss-user-agent:{self.oss_user_agent}')
        arr.append(f'/transfer-private{request_uri}'.rstrip('='))
        message = '\n'.join(arr)
        if self.debug:
            print('------------------------------------')
            print(message)
            print('------------------------------------')
        signature = self.make_digest(message, self.token_info.get('accessKeySecret'))
        headers = {
            'x-oss-user-agent': self.oss_user_agent,
            'x-oss-date': gmt_datetime_str,
            'x-oss-security-token': security_token,
            'authorization': f'OSS {access_key_id}:{signature}'
        }
        return headers

    async def upload_multi_main(self):
        balance = os.path.getsize(self.filepath)
        offset = 0
        self.initiate_multipart_upload()
        conn = aiohttp.TCPConnector(limit=10)
        timeout = aiohttp.ClientTimeout(total=None, connect=None, sock_connect=30, sock_read=30)
        self.sem = asyncio.Semaphore(self.concurrency)
        async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
            n = 0
            tasks = []
            while balance > 0:
                n += 1
                length = min(self.trunk_size, balance)
                data_range = range(offset, offset + length)
                tasks.append(asyncio.create_task(self.upload_part(session, data_range, n)))
                offset += length
                balance -= length
            await asyncio.wait(tasks)
        print('')
        if self.debug:
            print(self.multipart_upload_record)
        self.submit_parts()

    def upload(self):
        filesize = os.path.getsize(self.filepath)
        n = math.ceil(filesize / self.trunk_size)
        if n > 1:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.upload_multi_main())
            # Wait 250 ms for the underlying SSL connections to close
            loop.run_until_complete(asyncio.sleep(0.25))
            loop.close()
        else:
            self.upload_single()

    def upload_single(self):
        headers = {
            'Connection': 'keep-alive',
            'sec-ch-ua-mobile': '?0',
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua': '"(Not(A:Brand";v="8", "Chromium";v="98", "Google Chrome";v="98"',
            'Accept': '*/*',
            'Origin': 'https://musetransfer.com',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://musetransfer.com/',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        with open(self.filepath, 'rb') as fp:
            data = fp.read()
        basename = os.path.basename(self.filepath)
        upload_path = self.create_info.get('uploadPath')
        request_uri = f'/{upload_path}{basename}'
        auth_headers = self.build_auth_headers(method='PUT', request_uri=request_uri)
        headers.update(auth_headers)
        url_path = f'/{upload_path}{quote_plus(basename)}'
        response = self.session.put(f'https://share-file.tezign.com{url_path}', headers=headers, data=data)
        # self.check_response(response)
        etag = response.headers.get('ETag')
        if not etag:
            raise Exception(f'上传文件异常')

    def initiate_multipart_upload(self):
        upload_path = self.create_info.get('uploadPath')
        basename = os.path.basename(self.filepath)
        request_uri = f'/{upload_path}{basename}?uploads='
        url = f"https://share-file.tezign.com/{upload_path}{quote_plus(basename)}?uploads="
        headers = {
            'Connection': 'keep-alive',
            'Content-Length': '0',
            'sec-ch-ua-mobile': '?0',
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua': '"(Not(A:Brand";v="8", "Chromium";v="98", "Google Chrome";v="98"',
            'Accept': '*/*',
            'Origin': 'https://musetransfer.com',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://musetransfer.com/',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        auth_headers = self.build_auth_headers(method='POST', request_uri=request_uri)
        headers.update(auth_headers)
        response = self.session.request("POST", url, headers=headers)
        result = xmltodict.parse(response.text)
        upload_result = result['InitiateMultipartUploadResult']
        self.init_multipart_result['Bucket'] = upload_result['Bucket']
        self.init_multipart_result['Key'] = upload_result['Key']
        self.init_multipart_result['UploadId'] = upload_result['UploadId']
        if self.debug:
            print(response.text)

    async def upload_part(self, session, data_range, part_number):
        async with self.sem:
            headers = {
                'Connection': 'keep-alive',
                'sec-ch-ua-mobile': '?0',
                'User-Agent':
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36',
                'sec-ch-ua-platform': '"Windows"',
                'sec-ch-ua': '"(Not(A:Brand";v="8", "Chromium";v="98", "Google Chrome";v="98"',
                'Accept': '*/*',
                'Origin': 'https://musetransfer.com',
                'Sec-Fetch-Site': 'cross-site',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Dest': 'empty',
                'Referer': 'https://musetransfer.com/',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            upload_id = self.init_multipart_result.get('UploadId')
            key = self.init_multipart_result.get('Key')
            parts = key.split('/')
            parts[-1] = quote_plus(parts[-1])
            url_path = '/' + '/'.join(parts) + f'?partNumber={part_number}&uploadId={upload_id}'
            url = f'https://share-file.tezign.com{url_path}'
            request_uri = f'/{key}?partNumber={part_number}&uploadId={upload_id}'
            content_type, _ = mimetypes.guess_type(request_uri)
            content_type = content_type if content_type else 'application/octet-stream'
            auth_headers = self.build_auth_headers(method='PUT', content_type=content_type, request_uri=request_uri)
            headers['Content-Type'] = content_type
            headers.update(auth_headers)
            with open(self.filepath, 'rb') as fp:
                fp.seek(data_range.start)
                data = fp.read(data_range.stop - data_range.start)
            async with session.put(url, headers=headers, data=data) as resp:
                resp.raise_for_status()
                etag = resp.headers.get('ETag', '')
                if not etag:
                    raise Exception(f'上传文件异常：partNumber:{part_number}')
                self.multipart_upload_record[str(part_number)] = etag
                total = math.ceil(os.path.getsize(self.filepath) / self.trunk_size)
                sys.stdout.write('\r已上传分片：{}/{}  '.format(len(self.multipart_upload_record), total))
                sys.stdout.flush()

    def submit_parts(self):
        headers = {
            'Connection': 'keep-alive',
            'sec-ch-ua-mobile': '?0',
            'Content-Type': 'application/xml',
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36',
            'sec-ch-ua': '"(Not(A:Brand";v="8", "Chromium";v="98", "Google Chrome";v="98"',
            'sec-ch-ua-platform': '"Windows"',
            'Accept': '*/*',
            'Origin': 'https://musetransfer.com',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://musetransfer.com/',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        key = self.init_multipart_result.get('Key')
        upload_id = self.init_multipart_result.get('UploadId')
        request_uri = f'/{key}?uploadId={upload_id}'

        parts = key.split('/')
        parts[-1] = quote_plus(parts[-1])
        url_path = '/' + '/'.join(parts) + f'?uploadId={upload_id}'

        url = f'https://share-file.tezign.com{url_path}'
        content_type = 'application/xml'
        payload_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<CompleteMultipartUpload>']
        for i in range(1, len(self.multipart_upload_record) + 1):
            etag = self.multipart_upload_record.get(str(i))
            payload_lines.extend(['<Part>', f'<PartNumber>{i}</PartNumber>', f'<ETag>{etag}</ETag>', '</Part>'])
        payload_lines.append('</CompleteMultipartUpload>')
        data = '\n'.join(payload_lines)
        if self.debug:
            print('submit:' + data)
        md5 = hashlib.md5()
        md5.update(data.encode('utf-8'))
        md5_b64 = base64.b64encode(md5.digest()).decode('ascii')
        auth_headers = self.build_auth_headers(
            method='POST', content_md5=md5_b64, content_type=content_type, request_uri=request_uri
        )
        headers['Content-MD5'] = md5_b64
        headers.update(auth_headers)
        response = self.session.post(url, headers=headers, data=data)
        if 'CompleteMultipartUploadResult' not in response.text:
            raise Exception(f'出错了！错误：\n{response.text}')
        if self.debug:
            print(response.text)

    def add(self):
        headers = {
            'Connection': 'keep-alive',
            'sec-ch-ua': '"(Not(A:Brand";v="8", "Chromium";v="98", "Google Chrome";v="98"',
            'Accept': 'application/json',
            'x-transfer-device': self.device_id,
            'sec-ch-ua-mobile': '?0',
            'Content-Type': 'application/json;charset=UTF-8',
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36',
            'sec-ch-ua-platform': '"Windows"',
            'Origin': 'https://musetransfer.com',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://musetransfer.com/',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        if self.transfer_token:
            headers['x-transfer-token'] = self.transfer_token
        code = self.create_info.get('code')
        path = self.create_info.get('uploadPath', '') + os.path.basename(self.filepath)
        basename = os.path.basename(path)
        ext = os.path.splitext(basename)[-1][1:]
        ext = ext if ext else basename
        data = {'code': code, 'path': path, 'name': basename, 'type': ext, 'size': os.path.getsize(self.filepath)}
        response = self.session.post(
            'https://service.tezign.com/transfer/asset/add', headers=headers, data=json.dumps(data)
        )
        self.check_response(response)
        resp_data = response.json()
        self.asset_id = resp_data.get('result', {}).get('id', 0)
        assert self.asset_id > 0

    def finish(self):
        headers = {
            'Connection': 'keep-alive',
            'sec-ch-ua': '"(Not(A:Brand";v="8", "Chromium";v="98", "Google Chrome";v="98"',
            'Accept': 'application/json',
            'x-transfer-device': self.device_id,
            'sec-ch-ua-mobile': '?0',
            'Content-Type': 'application/json;charset=UTF-8',
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36',
            'sec-ch-ua-platform': '"Windows"',
            'Origin': 'https://musetransfer.com',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://musetransfer.com/',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        if self.transfer_token:
            headers['x-transfer-token'] = self.transfer_token
        code = self.create_info.get('code')
        data = {'code': code, 'assetIds': [self.asset_id]}
        response = self.session.post(
            'https://service.tezign.com/transfer/share/finish', headers=headers, data=json.dumps(data)
        )
        self.check_response(response)

    def get_share_info(self):
        headers = {
            'Connection': 'keep-alive',
            'sec-ch-ua': '"(Not(A:Brand";v="8", "Chromium";v="98", "Google Chrome";v="98"',
            'Accept': 'application/json',
            'x-transfer-device': self.device_id,
            'sec-ch-ua-mobile': '?0',
            'Content-Type': 'application/json;charset=UTF-8',
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36',
            'sec-ch-ua-platform': '"Windows"',
            'Origin': 'https://musetransfer.com',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://musetransfer.com/',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        code = self.create_info.get('code')
        data = {'code': code}
        response = self.session.post(
            'https://service.tezign.com/transfer/share/get', headers=headers, data=json.dumps(data)
        )
        self.check_response(response)
        if self.debug:
            print(response.json())


def get_download_url(code):
    url = "https://service.tezign.com/transfer/share/download"
    device_id = ''.join([choice("0123456789abcdef") for i in range(11)])
    payload = {'code': code}
    headers = {
        'Connection': 'keep-alive',
        'sec-ch-ua': '"(Not(A:Brand";v="8", "Chromium";v="98", "Google Chrome";v="98"',
        'Accept': 'application/json',
        'x-transfer-device': device_id,
        'sec-ch-ua-mobile': '?0',
        'Content-Type': 'application/json;charset=UTF-8',
        'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"',
        'Origin': 'https://musetransfer.com',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': 'https://musetransfer.com/',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
    }
    response = requests.request("POST", url, headers=headers, data=json.dumps(payload))

    print(response.text)


def upload(filepath='', transfer_token='', concurrency=3, debug=False):
    uploader = MuseUploader(filepath=filepath, transfer_token=transfer_token, concurrency=concurrency)
    uploader.debug = debug
    return uploader.run()


def send_dingtalk_message(message):
    url = "https://tools.201992.xyz/dingtalk/robot.php"
    requests.post(url=url, data={'message': message})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='可用参数如下：')
    parser.add_argument('filepath', help='上传的文件路径')
    parser.add_argument('-token', default='', help='传输token')
    parser.add_argument('-c', default='3', help='分片上传并发数')
    args = parser.parse_args()
    filepath = args.filepath
    token = args.token
    concurrency = int(args.c)

    code = upload(filepath=filepath, transfer_token=token, concurrency=concurrency, debug=False)
    print(f'上传成功！文件下载地址：https://musetransfer.com/s/{code}')
    name = os.path.splitext(os.path.basename(filepath))[0]
    message = f'文件\'{name}\'上传成功！文件下载地址：https://musetransfer.com/s/{code}'
    send_dingtalk_message(message=message)
