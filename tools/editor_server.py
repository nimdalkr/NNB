"""Local-only NNB strategy editor. Stages files; never starts or restarts StarCraft."""
import argparse
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
import json
import math
from pathlib import Path
import subprocess
from urllib.parse import urlsplit,parse_qs
from editor_model import ROOT,baseline,catalog,clone,load_profile,list_profiles,save,stage,validate,compile_profile
from corpus import read_json,find_cases


def terrain():
    result=[]
    for m in catalog()['maps']:
        folder=ROOT/'data/terrain'/m['hash'];geometry=folder/'geometry.json'
        g=read_json(geometry) if geometry.exists() else None
        result.append({**m,'ready':bool(g and g.get('cacheLoadVerified')), 'geometry':g})
    return result


def preview(profile,facts,matchup,map_hash,opening):
    validate(profile)
    if not isinstance(facts,dict) or any(type(v) not in (int,float) or not math.isfinite(v) for v in facts.values()):
        raise ValueError('판단 정보는 이름과 숫자로 입력하세요')
    payload={'policy':compile_profile(profile).get('NNBPolicy',{'enabled':False,'rules':[]}),
             'facts':facts,'matchup':matchup,'map':map_hash,'opening':opening}
    exe=ROOT/'build/native-check/Release/nnb-policy-check.exe'
    result=subprocess.run([str(exe)],input=json.dumps(payload),capture_output=True,text=True,timeout=10)
    if result.returncode:raise ValueError('판단 검사 실패: '+result.stderr)
    return json.loads(result.stdout)


class Handler(BaseHTTPRequestHandler):
    def reply(self,data,status=200,mime='application/json; charset=utf-8'):
        raw=json.dumps(data,ensure_ascii=False).encode() if isinstance(data,(dict,list)) else data
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw)

    def do_GET(self):
        try:
            url=urlsplit(self.path);q=parse_qs(url.query)
            if url.path=='/api/state':return self.reply(dict(profiles=list_profiles(),catalog=catalog(),terrain=terrain(),cohort=read_json(ROOT/'data/summary.json'),lastStage=read_json(ROOT/'data/editor/last-stage.json') if (ROOT/'data/editor/last-stage.json').exists() else None))
            if url.path=='/api/terrain':
                h=q.get('hash',[''])[0]
                if h not in [m['hash'] for m in catalog()['maps']]:raise ValueError('알 수 없는 맵')
                return self.reply(read_json(ROOT/'data/terrain'/h/'input.json'))
            if url.path=='/api/cases':
                target={k:float(q[k][0]) for k in ['workers','armyValue','bases'] if k in q and q[k][0]}
                return self.reply(find_cases(ROOT/'data',q['map'][0],q['matchup'][0].lower(),q['opening'][0],int(q.get('frame',['4000'])[0]),target=target,limit=5))
            assets={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
            if url.path not in assets:return self.reply({'error':'Not found'},404)
            file=ROOT/'editor'/assets[url.path]
            mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8'}[file.suffix]
            return self.reply(file.read_bytes(),mime=mime)
        except (ValueError,KeyError,OSError,TypeError) as e:return self.reply({'error':str(e)},400)

    def do_POST(self):
        try:
            origin=self.headers.get('Origin')
            if origin and origin!=f'http://127.0.0.1:{self.server.server_port}':raise ValueError('다른 사이트의 변경 요청을 거절했습니다')
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('JSON 요청이 필요합니다')
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=2000000:raise ValueError('요청 크기가 잘못되었습니다')
            d=json.loads(self.rfile.read(size))
            if self.path=='/api/clone':return self.reply(clone(d['id']))
            if self.path=='/api/save':return self.reply(save(d['profile']))
            if self.path=='/api/validate':
                validate(d['profile']);compiled=compile_profile(d['profile'])
                return self.reply({'ok':True,'config':compiled,'note':'형식·지원 범위 검사 통과. 빌드 실행과 경기력은 별도 경기 검증이 필요합니다.'})
            if self.path=='/api/stage':return self.reply(stage(load_profile(d['id'])))
            if self.path=='/api/preview':return self.reply(preview(d['profile'],d['facts'],d['matchup'],d['map'],d['opening']))
            return self.reply({'error':'Not found'},404)
        except (ValueError,KeyError,OSError,TypeError,subprocess.SubprocessError) as e:return self.reply({'error':str(e)},400)

    def log_message(self,*args):pass


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8830);a=p.parse_args()
    print(f'NNB editor: http://127.0.0.1:{a.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
