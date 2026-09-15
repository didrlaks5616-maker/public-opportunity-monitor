from __future__ import annotations
import os, re, json, hashlib, logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=os.getenv('LOG_LEVEL','INFO'), format='%(asctime)s %(levelname)s %(message)s')
log=logging.getLogger('monitor')
KST=timezone(timedelta(hours=9))

KEYWORDS='''마케팅 마케팅대행 마케팅운영 마케팅용역 온라인마케팅 디지털마케팅 통합마케팅 해외마케팅 지역마케팅 관광마케팅 브랜드마케팅 홍보 홍보대행 홍보용역 홍보운영 온라인홍보 정책홍보 사업홍보 언론홍보 홍보전략 PR 광고 광고대행 광고운영 광고용역 온라인광고 디지털광고 검색광고 SNS광고 미디어광고 옥외광고 매체광고 광고캠페인 SNS 소셜미디어 유튜브 인스타그램 블로그 페이스북 숏폼 릴스 틱톡 채널운영 SNS운영 SNS콘텐츠 온라인채널 콘텐츠 콘텐츠제작 홍보콘텐츠 영상콘텐츠 영상제작 홍보영상 브랜드영상 유튜브콘텐츠 숏폼콘텐츠 사진촬영 디자인 그래픽디자인 상세페이지 카탈로그 브로슈어 홍보물 인쇄물 브랜드 브랜딩 브랜드개발 BI CI 네이밍 브랜드전략 브랜드홍보 행사 행사대행 행사운영 행사기획 이벤트 이벤트대행 축제 축제운영 축제대행 페스티벌 포럼 컨퍼런스 세미나 설명회 네트워킹 데모데이 쇼케이스 개막식 기념식 전시 전시회 박람회 페어 엑스포 전시운영 박람회운영 공동관 홍보관 전시관 부스 부스운영 부스설치 전시기획 공간기획 판촉 프로모션 캠페인 기획전 판매전 특판전 판촉전 품평회 팝업 팝업스토어 라이브커머스 체험행사 인플루언서 크리에이터 체험단 서포터즈 기자단 홍보단 앰배서더 관광홍보 관광마케팅 지역홍보 지역브랜딩 지역축제 관광콘텐츠 관광상품 지역활성화 상권활성화 용역 입찰 입찰공고 제안요청서 RFP 제안서 제안서평가 사업자선정 수행기관 수행업체 운영업체 대행사 협력업체 계약 협상에의한계약 일반경쟁 제한경쟁 지명경쟁 전자입찰 전자견적 나라장터 사전규격 긴급입찰 재공고 입찰참가 입찰참가자격'''.split()
EXCLUDE='''직원채용 공무원채용 기간제근로자 인사 부동산매각 토목공사 건축공사 전기공사 기계설비 시설보수 단순물품구매 차량구매 사무용품구매 급식 경비 청소 폐기물처리 의료장비 건설자재'''.split()
BID_TERMS='용역 입찰 입찰공고 제안요청서 RFP 제안서 사업자선정 수행업체 운영업체 대행사 협상에의한계약 일반경쟁 제한경쟁 전자입찰'.split()

@dataclass
class Notice:
    title:str; organization:str=''; notice_type:str='SUPPORT'; target:str=''; description:str=''; budget:str=''; deadline:str=''; published_at:str=''; url:str=''; source:str=''; source_id:str=''; bid_number:str=''; bid_method:str=''; contract_method:str=''; project_period:str=''; eligibility:str=''; rfp_url:str=''; raw_text:str=''; content_hash:str=''; unique_key:str=''; status:str='NEW';


def clean(v): return re.sub(r'\s+',' ',str(v or '')).strip()
def parse_date(v):
    s=clean(v)
    m=re.search(r'(20\d{2})[-./]?(\d{2})[-./]?(\d{2})',s)
    return f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else ''
def hash_text(s): return hashlib.sha256(clean(s).encode()).hexdigest()
def unique_key(n): return '|'.join([n.source, n.bid_number or n.source_id or '', clean(n.organization), clean(n.title), n.deadline or ''])

def score_notice(n):
    text=(n.title+' '+n.description+' '+n.raw_text).lower(); hits=[k for k in KEYWORDS if k.lower() in text]
    score=min(100,len(hits)*4)
    if n.notice_type=='BID' and any(t.lower() in text for t in BID_TERMS): score+=20
    combos=[('홍보','용역'),('마케팅','용역'),('행사','운영'),('축제','대행'),('SNS','운영'),('영상','제작'),('광고','대행'),('콘텐츠','제작'),('박람회','운영'),('홍보관','운영'),('팝업스토어','운영')]
    for a,b in combos:
        if a.lower() in text and b.lower() in text: score+=10
    return score,hits

def relevant(n):
    text=(n.title+' '+n.description+' '+n.raw_text).lower()
    s,h=score_notice(n)
    hard_excluded=any(x.lower() in n.title.lower() for x in EXCLUDE)
    mixed=any(k.lower() in text for k in ['홍보','마케팅','행사','축제','콘텐츠','광고','전시','박람회','브랜드','sns'])
    return (s>=8 or mixed) and (not hard_excluded or mixed and n.notice_type=='BID')

def g2b():
    key=os.getenv('G2B_SERVICE_KEY','')
    if not key: return []
    base='https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc'
    now=datetime.now(); start=now-timedelta(days=int(os.getenv('LOOKBACK_DAYS','3')))
    out=[]
    for page in range(1,int(os.getenv('MAX_PAGES','20'))+1):
        p={'serviceKey':key,'type':'json','inqryDiv':'1','inqryBgnDt':start.strftime('%Y%m%d%H%M'),'inqryEndDt':now.strftime('%Y%m%d%H%M'),'numOfRows':100,'pageNo':page}
        r=requests.get(base,params=p,timeout=30); r.raise_for_status(); body=r.json().get('response',{}).get('body',{})
        items=body.get('items') or []; items=items.get('item') if isinstance(items,dict) else items
        if not items: break
        for x in items:
            title=clean(x.get('bidNtceNm')); 
            if not title: continue
            raw=' | '.join(f'{k}:{v}' for k,v in x.items() if v not in (None,''))
            n=Notice(title=title,organization=clean(x.get('ntceInsttNm') or x.get('dminsttNm')),notice_type='BID',description=raw,budget=clean(x.get('presmptPrce') or x.get('bdgtAmt') or x.get('asignBdgtAmt')),deadline=parse_date(x.get('bidClseDt') or x.get('bidNtceEndDt')),published_at=parse_date(x.get('bidNtceDt') or x.get('ntceDt')),url=clean(x.get('bidNtceDtlUrl') or x.get('bidNtceUrl')),source='G2B',source_id=clean(x.get('bidNtceNo')),bid_number=clean(x.get('bidNtceNo')),bid_method=clean(x.get('bidMthdNm')),contract_method=clean(x.get('cntrctCnclsMthdNm')),project_period=clean(x.get('srvcePrd')),raw_text=raw)
            n.content_hash=hash_text(n.raw_text); n.unique_key=unique_key(n); out.append(n)
        if page*100>=int(body.get('totalCount') or 0): break
    return out

def bizinfo():
    key=os.getenv('BIZINFO_API_KEY','')
    if not key: return []
    url=os.getenv('BIZINFO_API_URL','https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do')
    p={'crtfcKey':key,'dataType':'json','searchCnt':100}
    r=requests.get(url,params=p,timeout=30); r.raise_for_status(); data=r.json() if 'json' in r.headers.get('content-type','') else json.loads(r.text)
    items=data.get('jsonArray') or data.get('items') or data.get('data') or []
    if isinstance(items,dict): items=items.get('item') or []
    out=[]
    for x in items:
        title=clean(x.get('pblancNm') or x.get('title') or x.get('사업명'))
        if not title: continue
        raw=' | '.join(f'{k}:{v}' for k,v in x.items() if v not in (None,''))
        n=Notice(title=title,organization=clean(x.get('jrsdInsttNm') or x.get('organization')),notice_type='SUPPORT',target=clean(x.get('trgetNm') or x.get('target')),description=clean(x.get('bsnsSumryCn') or x.get('description')),budget=clean(x.get('suptAmt') or x.get('budget')),deadline=parse_date(x.get('reqstEndDe') or x.get('requestEndDate')),published_at=parse_date(x.get('creatPnttm') or x.get('pblancBeginDe')),url=clean(x.get('pblancUrl') or x.get('detailUrl') or x.get('url')),source='BIZINFO',source_id=clean(x.get('pblancId') or x.get('id')),raw_text=raw)
        n.content_hash=hash_text(n.raw_text); n.unique_key=unique_key(n); out.append(n)
    return out

def notion_request(method,path,token,**kw):
    h={'Authorization':f'Bearer {token}','Notion-Version':os.getenv('NOTION_VERSION','2026-03-11'),'Content-Type':'application/json'}
    for i in range(4):
        r=requests.request(method,'https://api.notion.com/v1'+path,headers=h,timeout=30,**kw)
        if r.status_code==429 or r.status_code>=500:
            import time; time.sleep(min(2*(i+1),10)); continue
        r.raise_for_status(); return r
    r.raise_for_status()

def rt(v): return {'rich_text':[{'type':'text','text':{'content':clean(v)[:2000]}}]} if clean(v) else {'rich_text':[]}
def dt(v): return {'date':{'start':v}} if v else {'date':None}
def urlp(v): return {'url':v} if v else {'url':None}
def sel(v): return {'select':{'name':v}} if v else {'select':None}

def notion_sync(changes):
    token=os.getenv('NOTION_TOKEN'); ds=os.getenv('NOTION_DATA_SOURCE_ID')
    if not token or not ds: raise RuntimeError('NOTION_TOKEN and NOTION_DATA_SOURCE_ID are required for live sync')
    pages=[]; cursor=None
    while True:
        b={'page_size':100};
        if cursor: b['start_cursor']=cursor
        data=notion_request('POST',f'/data_sources/{ds}/query',token,json=b).json(); pages+=data.get('results',[])
        if not data.get('has_more'): break
        cursor=data.get('next_cursor')
    existing={}
    for p in pages:
        props=p.get('properties',{}); key=''.join(x.get('plain_text',x.get('text',{}).get('content','')) for x in props.get('식별키',{}).get('rich_text',[]))
        if key: existing[key]=(p,props)
    for n in changes:
        p={'공고명':{'title':[{'type':'text','text':{'content':n.title[:2000]}}]},'발주·주관기관':rt(n.organization),'참가·지원대상':rt(n.target),'주요내용·예산':rt((n.description[:1500] if n.description else '')+(f' / {n.budget}' if n.budget else '')),'마감일':dt(n.deadline),'원문링크':urlp(n.url),'공고유형':sel(n.notice_type),'식별키':rt(n.unique_key),'내용해시':rt(n.content_hash),'수집처':rt(n.source),'공고번호':rt(n.bid_number),'상태':sel(n.status),'게시일':dt(n.published_at),'예산':rt(n.budget),'입찰방식':rt(n.bid_method),'계약방식':rt(n.contract_method),'사업기간':rt(n.project_period),'참가자격':rt(n.eligibility),'제안서마감':dt(''),'원문RFP':urlp(n.rfp_url)}
        if n.unique_key in existing:
            notion_request('PATCH',f"/pages/{existing[n.unique_key][0]['id']}",token,json={'properties':p})
        else:
            notion_request('POST','/pages',token,json={'parent':{'type':'data_source_id','data_source_id':ds},'properties':p})

def notify(changes):
    if not changes or not os.getenv('NOTIFICATION_TYPE'): return
    lines=[f"[{datetime.now(KST):%Y-%m-%d} 공공사업·입찰] 신규/수정 {len(changes)}건"]
    for n in sorted(changes,key=lambda x:(-score_notice(x)[0],x.deadline or '9999-99-99'))[:30]: lines.append(f'[{n.status}] {n.title}\n기관: {n.organization}\n예산: {n.budget or "-"}\n마감: {n.deadline or "-"}\n{n.url}')
    body='\n\n'.join(lines); typ=os.getenv('NOTIFICATION_TYPE').lower()
    if typ=='telegram' and os.getenv('TELEGRAM_BOT_TOKEN') and os.getenv('TELEGRAM_CHAT_ID'):
        requests.post(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",json={'chat_id':os.environ['TELEGRAM_CHAT_ID'],'text':body[:4000]},timeout=30).raise_for_status()
    elif typ=='slack' and os.getenv('SLACK_WEBHOOK_URL'): requests.post(os.environ['SLACK_WEBHOOK_URL'],json={'text':body[:12000]},timeout=30).raise_for_status()

def main():
    live=os.getenv('DRY_RUN','true').lower() not in {'1','true','yes','on'}
    alln=[]
    for name,fn in [('G2B',g2b),('BIZINFO',bizinfo)]:
        try:
            got=fn(); log.info('%s collected=%s',name,len(got)); alln+=got
        except Exception as e: log.exception('%s failed: %s',name,e)
    rel=[]; seen=set()
    for n in alln:
        if not relevant(n): continue
        if n.unique_key in seen: continue
        seen.add(n.unique_key); rel.append(n)
    if not live:
        print('=== DRY RUN ===')
        for n in sorted(rel,key=lambda x:-score_notice(x)[0]): print(json.dumps({'status':n.status,'type':n.notice_type,'title':n.title,'organization':n.organization,'deadline':n.deadline,'budget':n.budget,'url':n.url,'score':score_notice(n)[0]},ensure_ascii=False))
        return
    notion_sync(rel); notify(rel); log.info('synced=%s',len(rel))

if __name__=='__main__': main()
