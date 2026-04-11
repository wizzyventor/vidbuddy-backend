from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import yt_dlp
import os
import time

app = Flask(__name__)
CORS(app)

DOWNLOAD_FOLDER = "web_downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Feature: Metadata Extraction
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
            # Filter for video+audio combined formats
            formats = [
                {'format_id': f['format_id'], 'resolution': f.get('resolution', 'N/A'), 'ext': f['ext']}
                for f in info.get('formats', []) if f.get('vcodec') != 'none' and f.get('acodec') != 'none'
            ]
            return jsonify({
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'formats': formats[-5:] # Return the top 5 quality options
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    video_url = data.get('url')
    format_id = data.get('format_id', 'best') # Feature: Format Selection
    
    timestamp = int(time.time())
    file_path = os.path.join(DOWNLOAD_FOLDER, f"vid_{timestamp}.mp4")

    ydl_opts = {
        'format': format_id,
        'outtmpl': file_path,
        'quiet': True,
        # Feature: SponsorBlock (strips ads from video content)
        'postprocessors': [{'key': 'SponsorBlock'}], 
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
