from flask import Flask, request, send_file, jsonify, make_response
from flask_cors import CORS
import yt_dlp
import os
import re
import time
import subprocess

app = Flask(__name__)
CORS(app)

DOWNLOAD_FOLDER = "web_downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/')
def home():
    # NEW FEATURE: Environment Health Check
    # Verifies that Node and FFmpeg are present in the Docker container
    try:
        node = subprocess.check_output(['node', '--version']).decode().strip()
        ffmpeg = subprocess.check_output(['ffmpeg', '-version']).splitlines()[0].decode().strip()
        return f"VidBuddy Active | Node: {node} | FFmpeg: {ffmpeg}", 200
    except:
        return "VidBuddy API is Active (Check Environment)", 200

@app.route('/info', methods=['POST'])
def get_info():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    # ORIGINAL FEATURE: Bot Bypass & Client Rotation
    ydl_opts = {
        'quiet': True, 
        'noplaylist': True,
        'impersonate': 'chrome',
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'web_safari'],
                'skip': ['dash', 'hls']
            }
        }
    }
    
    # ORIGINAL FEATURE: Cookie Support
    if os.path.exists('cookies.txt'):
        ydl_opts['cookiefile'] = 'cookies.txt'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = [
                {'format_id': f['format_id'], 'resolution': f.get('resolution', 'N/A'), 'ext': f['ext']}
                for f in info.get('formats', []) 
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none'
            ]
            return jsonify({
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'formats': formats[-3:] 
            })
    except Exception as e:
        print(f"Extraction Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    video_url = data.get('url')
    format_id = data.get('format_id', 'best')

    try:
        ydl_opts_meta = {'quiet': True, 'impersonate': 'chrome'}
        if os.path.exists('cookies.txt'):
            ydl_opts_meta['cookiefile'] = 'cookies.txt'

        with yt_dlp.YoutubeDL(ydl_opts_meta) as ydl:
            info = ydl.extract_info(video_url, download=False)
            video_title = info.get('title', 'video')
            clean_title = re.sub(r'[\\/*?:"<>|]', "", video_title)[:50]
            temp_filename = os.path.join(DOWNLOAD_FOLDER, f"dl_{int(time.time())}.mp4")

        ydl_opts_dl = {
            'format': format_id,
            'outtmpl': temp_filename,
            'quiet': True,
            'impersonate': 'chrome',
            'external_downloader': 'builtin' 
        }
        if os.path.exists('cookies.txt'):
            ydl_opts_dl['cookiefile'] = 'cookies.txt'
        
        with yt_dlp.YoutubeDL(ydl_opts_dl) as ydl:
            ydl.download([video_url])

        file_size = os.path.getsize(temp_filename)

        def generate():
            with open(temp_filename, 'rb') as f:
                yield from f
            try:
                os.remove(temp_filename)
            except:
                pass

        response = make_response(generate())
        response.headers['Content-Type'] = 'video/mp4'
        response.headers['Content-Disposition'] = f'attachment; filename={clean_title}.mp4'
        response.headers['Content-Length'] = file_size
        response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition, Content-Length'
        return response

    except Exception as e:
        print(f"Download Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
