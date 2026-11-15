"""仅回环地址的 HTTP 契约教学实验，临时进程内数据，无生产认证。"""

import hashlib
import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class Conflict(Exception):
    pass


class MemoryRepository:
    def __init__(self):
        self.items = {}
        self.keys = {}
        self.lock = threading.Lock()

    def create_once(self, key, fingerprint, title):
        with self.lock:
            if key in self.keys:
                old_fingerprint, item_id = self.keys[key]
                if old_fingerprint != fingerprint:
                    raise Conflict("key reused with different content")
                return dict(self.items[item_id]), False
            item_id = len(self.items) + 1
            item = {"id": item_id, "title": title}
            self.items[item_id] = item
            self.keys[key] = (fingerprint, item_id)
            return dict(item), True


class DocumentService:
    def __init__(self, repository):
        self.repository = repository

    def create(self, payload, key):
        if not isinstance(payload, dict) or not isinstance(payload.get("title"), str):
            raise ValueError("title must be a string")
        title = payload["title"].strip()
        if not 1 <= len(title) <= 80:
            raise ValueError("title length must be 1..80")
        if not key or len(key) > 80:
            raise ValueError("Idempotency-Key length must be 1..80")
        fingerprint = hashlib.sha256(title.encode()).hexdigest()
        return self.repository.create_once(key, fingerprint, title)


def handler_factory(service):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send_json(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.path != "/documents":
                self.send_json(404, {"error": "route_not_found"})
                return
            if self.headers.get_content_type() != "application/json":
                self.send_json(415, {"error": "json_required"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 1 <= length <= 4096:
                    self.send_json(413, {"error": "body_size_out_of_range"})
                    return
                payload = json.loads(self.rfile.read(length))
                item, created = service.create(payload, self.headers.get("Idempotency-Key", ""))
                self.send_json(201 if created else 200, {"item": item, "created": created})
            except (ValueError, UnicodeDecodeError):
                self.send_json(422, {"error": "invalid_request"})
            except Conflict:
                self.send_json(409, {"error": "idempotency_conflict"})

    return Handler


@contextmanager
def local_server():
    repository = MemoryRepository()
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(DocumentService(repository)))
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port), repository
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def send(base_url, payload, key="demo-1", path="/documents"):
    request = Request(base_url + path, data=json.dumps(payload).encode(), method="POST",
                      headers={"Content-Type": "application/json", "Idempotency-Key": key})
    try:
        with urlopen(request, timeout=3) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        with error:
            return error.code, json.load(error)


def demo():
    with local_server() as (url, repository):
        results = [send(url, {"title": "通知"}), send(url, {"title": "通知"}),
                   send(url, {"title": "另一个标题"}), send(url, {"title": " "}, key="empty")]
        return {"scope": "loopback_http_temporary_memory", "responses": results, "stored_items": len(repository.items)}


if __name__ == "__main__":
    print(json.dumps(demo(), ensure_ascii=False, indent=2))
