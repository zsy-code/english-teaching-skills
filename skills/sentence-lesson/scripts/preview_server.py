"""Local preview with byte ranges for seeking WAV narration. Bind loopback only."""
import argparse
import functools
import os
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.wav':'audio/wav'}
    def send_head(self):
        filename=self.translate_path(self.path)
        value=self.headers.get('Range')
        if not value or not os.path.isfile(filename):
            return super().send_head()
        size=os.path.getsize(filename)
        match=re.fullmatch(r'bytes=(\d*)-(\d*)',value)
        if not match or not any(match.groups()):
            self.send_error(416);return None
        first,last=match.groups()
        start=int(first) if first else max(0,size-int(last))
        end=min(int(last),size-1) if first and last else size-1
        if start>=size or end<start:
            self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.end_headers();return None
        f=open(filename,'rb');f.seek(start)
        self.send_response(206)
        self.send_header('Content-Type',self.guess_type(filename));self.send_header('Accept-Ranges','bytes')
        self.send_header('Content-Range',f'bytes {start}-{end}/{size}');self.send_header('Content-Length',str(end-start+1));self.end_headers()
        self.remaining=end-start+1
        return f
    def copyfile(self,source,output):
        remaining=getattr(self,'remaining',None)
        if remaining is None:return super().copyfile(source,output)
        try:
            while remaining:
                block=source.read(min(65536,remaining))
                if not block:break
                output.write(block);remaining-=len(block)
        finally:
            del self.remaining
    def log_message(self,*args):pass

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory');p.add_argument('--port',type=int,default=4176);a=p.parse_args()
    print(f'预览：http://127.0.0.1:{a.port}/',flush=True)
    ThreadingHTTPServer(('127.0.0.1',a.port),functools.partial(Handler,directory=a.directory)).serve_forever()
