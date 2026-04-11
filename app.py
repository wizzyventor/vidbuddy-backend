from flask import Flask, request, send_file, jsonify, make_response
from flask_cors import CORS
import yt_dlp
import os
import re
import time

app = Flask(__name__)
# Enable CORS so your frontend can talk to this backend
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

    ydl_opts = {
        'quiet': True, 
        'noplaylist': True,
        'impersonate': 'chrome', # Helps with TikTok/YouTube blocks
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            # Filter for formats that have both video and audio
            formats = [
                {
                    'format_id': f['format_id'], 
                    'resolution': f.get('resolution', 'N/A'), 
                    'ext': f['ext']
                }
                for f in info.get('formats', []) 
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none'
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
    format_id = data.get('format_id', 'best')

    if not video_url:
        return jsonify({"error": "Missing URL"}), 400

    try:
        # 1. Fetch metadata to get a clean filename
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(video_url, download=False)
            video_title = info.get('title', 'vidbuddy_video')
            # Remove characters that break file systems
            clean_title = re.sub(r'[\\/*?:"<>|]', "", video_title)
            # Shorten very long titles to avoid Header errors
            display_title = (clean_title[:50] + '..') if len(clean_title) > 50 else clean_title
            
            temp_filename = os.path.join(DOWNLOAD_FOLDER, f"dl_{int(time.time())}.mp4")

        # 2. Download the file to the server
        ydl_opts = {
            'format': format_id,
            'outtmpl': temp_filename,
            'quiet': True,
            'impersonate': 'chrome',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        if not os.path.exists(temp_filename):
            return jsonify({"error": "File failed to download on server"}), 500

        file_size = os.path.getsize(temp_filename)

        # 3. Generator to stream file and delete after transfer
        def generate():
            with open(temp_filename, 'rb') as f:
                yield from f
            try:
                os.remove(temp_filename)
                print(f"Successfully deleted {temp_filename}")
            except Exception as e:
                print(f"Cleanup error: {e}")

        # 4. Create Response with Correct Headers
        response = make_response(generate())
        
        # We use f-strings carefully to avoid the extra quotes that caused the 400 error
        response.headers['Content-Type'] = 'video/mp4'
        response.headers['Content-Disposition'] = f'attachment; filename={display_title}.mp4'
        response.headers['Content-Length'] = file_size
        # Expose headers so the Frontend JavaScript can see the filename and size
        response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition, Content-Length'
        
        return response

    except Exception as e:
        # If something fails, try to delete the partial file if it exists
        if 'temp_filename' in locals() and os.path.exists(temp_filename):
            os.remove(temp_filename)
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return "VidBuddy API is running!", 200

@app.route('/<filename>')
def verify_ad_network(filename):
    """Allows ad network bots to find verification files in the root."""
    if filename.endswith(".html") or filename.endswith(".txt"):
        return send_file(filename)
    return "Not Found", 404

if __name__ == '__main__':
    # Get port from environment variable (required for Render)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
