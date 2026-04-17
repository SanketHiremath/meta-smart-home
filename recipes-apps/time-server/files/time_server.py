#!/usr/bin/env python3
import json
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>STM32MP1 Time Server</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: #0d1117;
            color: #f0f6fc;
            font-family: "DejaVu Sans", sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .card {
            text-align: center;
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 14px;
            padding: 48px 64px;
        }
        h1 {
            color: #8b949e;
            font-size: 14px;
            font-weight: normal;
            margin-bottom: 24px;
            letter-spacing: 2px;
            text-transform: uppercase;
        }
        #time {
            font-size: 72px;
            font-weight: bold;
            color: #58a6ff;
            letter-spacing: 4px;
        }
        #date { color: #8b949e; font-size: 16px; margin-top: 16px; }
        #status { color: #3fb950; font-size: 12px; margin-top: 24px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>STM32MP1 Time Server</h1>
        <div id="time">--:--:--</div>
        <div id="date"></div>
        <div id="status">connecting...</div>
    </div>
    <script>
        function update() {
            fetch('/time')
                .then(r => r.json())
                .then(d => {
                    document.getElementById('time').textContent = d.time;
                    document.getElementById('date').textContent = d.date;
                    document.getElementById('status').textContent =
                        'NTP synchronised \u2022 ' + window.location.hostname;
                })
                .catch(() => {
                    document.getElementById('status').textContent = 'reconnecting...';
                });
        }
        update();
        setInterval(update, 1000);
    </script>
</body>
</html>"""


class TimeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress per-request journal noise

    def do_GET(self):
        if self.path == '/time':
            now = datetime.datetime.now()
            body = json.dumps({
                'time': now.strftime('%H:%M:%S'),
                'date': now.strftime('%A, %d %B %Y'),
            }).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            body = HTML.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass


if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 80), TimeHandler)
    print('Serving on http://0.0.0.0:80')
    server.serve_forever()
