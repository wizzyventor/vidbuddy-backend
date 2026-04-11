from flask import Flask, request, send_file, jsonify, make_response
from flask_cors import CORS
import yt_dlp
import os
import re
import time

app = Flask(__name__)
CORS(app)

# Ensure the download folder exists
DOWNLOAD_FOLDER = "web_downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/info', methods=['POST'])
def get_info():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "No URL"}), 400

    ydl_opts = {'quiet': True, 'noplaylist': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = [
                {'format_id': f['format_id'], 'resolution': f.get('resolution', 'N/A'), 'ext': f['ext']}
                for f in info.get('formats', []) if f.get('vcodec') != 'none' and f.get('acodec') != 'none'
            ]
            return jsonify({
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'formats': formats[-5:] 
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    video_url = data.get('url')
    format_id = data.get('format_id', 'best')

    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(video_url, download=False)
            video_title = info.get('title', 'vidbuddy_video')
            clean_title = re.sub(r'[\\/*?:"<>|]', "", video_title)
            temp_filename = os.path.join(DOWNLOAD_FOLDER, f"dl_{int(time.time())}.mp4")

        ydl_opts = {
            'format': format_id,
            'outtmpl': temp_filename,
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        file_size = os.path.getsize(temp_filename)

        # Helper to stream the file and delete it afterward
        def generate():
            with open(temp_filename, 'rb') as f:
                yield from f
            # The file is deleted after the browser finishes reading the stream
            try:
                os.remove(temp_filename)
            except:
                pass

        response = make_response(generate())
        response.headers['Content-Type'] = 'video/mp4'
        response.headers['Content-Disposition'] = f"attachment; filename=\"{clean_title}.mp4\""
        response.headers['Content-Length'] = file_size
        response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition, Content-Length'
        
        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/<filename>')
def verify_ad_network(filename):
    if filename.endswith(".html") or filename.endswith(".txt"):
        return send_file(filename)
    return "Not Found", 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
