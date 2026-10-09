"""Local preview with HTTP Range support for reliable MP4 seeking. Bind localhost only."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import re

class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def send_head(self):
        self.remaining = None
        path = self.translate_path(self.path)
        request_range = self.headers.get('Range')
        if not os.path.isfile(path) or not request_range:
            return super().send_head()
        size = os.path.getsize(path)
        match = re.fullmatch(r'bytes=(\d+)-(\d*)', request_range)
        if not match:
            self.send_error(416); return None
        start = int(match[1]); end = min(int(match[2]) if match[2] else size-1, size-1)
        if start > end:
            self.send_response(416); self.send_header('Content-Range', f'bytes */{size}'); self.end_headers(); return None
        source = open(path, 'rb'); source.seek(start)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Length', str(end-start+1))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers(); self.remaining = end-start+1
        return source

    def copyfile(self, source, outputfile):
        try:
            if self.remaining is None:
                return super().copyfile(source, outputfile)
            while self.remaining > 0:
                chunk = source.read(min(65536, self.remaining))
                if not chunk: break
                outputfile.write(chunk); self.remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(f'Open http://127.0.0.1:{args.port}/tempo.html', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, directory=str(root))).serve_forever()
