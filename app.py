from flask import Flask, render_template, request, jsonify, Response
import requests
import json
import re
import os
from time import time, sleep

app = Flask(__name__)

def download_bilibili_audio(bv, filename):
    url = f'https://www.bilibili.com/video/{bv}'
    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.76",
        "Referer": "https://www.bilibili.com/",
    }

    try:
        resp = requests.get(url=url, headers=header, verify=False)
        if resp.status_code != 200:
            return {"status": "error", "message": "无法获取网页内容"}

        obj = re.compile(r'window.__playinfo__=(.*?)</script>', re.S)
        html_data = obj.findall(resp.text)[0]
        json_data = json.loads(html_data)

        audios = json_data['data']['dash']['audio']
        if not audios:
            return {"status": "error", "message": "未找到音频地址"}

        audio_url = audios[0]['baseUrl']
        return audio_url

    except Exception as e:
        return {"status": "error", "message": f"获取音频地址失败：{str(e)}"}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    bv = data.get('bv')
    filename = data.get('filename') or 'audio'

    if not bv:
        return jsonify({"status": "error", "message": "请输入BV号"})

    audio_url = download_bilibili_audio(bv, filename)
    if isinstance(audio_url, dict):  # 如果返回的是错误信息
        return jsonify(audio_url)

    return jsonify({"status": "success", "audio_url": audio_url, "filename": filename})

@app.route('/progress/<filename>')
def progress(filename):
    def generate_progress(audio_url):
        header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.76",
            "Referer": "https://www.bilibili.com/",
        }
        resp = requests.get(audio_url, headers=header, stream=True, verify=False)
        total_size = int(resp.headers.get('content-length', 0))
        downloaded = 0
        file_path = f"{filename}.mp3"
        start_time = time()

        with open(file_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    current_time = time()
                    elapsed_time = current_time - start_time  # 已用时长（秒）

                    progress = (downloaded / total_size) * 100 if total_size > 0 else 0
                    if progress > 0:
                        estimated_total_time = elapsed_time / (progress / 100)
                        remaining_time = estimated_total_time - elapsed_time  # 剩余时长
                    else:
                        remaining_time = 0

                    yield f"data: {json.dumps({'progress': progress, 'elapsed': elapsed_time, 'remaining': remaining_time})}\n\n"
                    sleep(0.1)  # 模拟延迟，便于观察

        yield f"data: {json.dumps({'progress': 100, 'elapsed': time() - start_time, 'remaining': 0})}\n\n"
        yield "data: done\n\n"

    audio_url = request.args.get('audio_url')
    return Response(generate_progress(audio_url), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8181, debug=True)
