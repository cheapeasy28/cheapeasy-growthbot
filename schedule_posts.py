"""Cheap&Easy Growthbot v0.1 — queue reviewed, pre-rendered posts via Buffer GraphQL.

Preview is the default. Actual scheduling requires LIVE_POSTING=true and API key.
Runs once daily in GitHub Actions and commits progress in state/posted.json.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

ROOT = Path(__file__).resolve().parent
API = 'https://api.buffer.com'
ALLOWED = {'pinterest', 'instagram', 'facebook'}
PLATFORM_OFFSETS = {'pinterest': 0, 'instagram': 12, 'facebook': 24}


def required_urls(products):
    bad = [key for key, cfg in products.items() if not str(cfg.get('url', '')).startswith('https://')]
    if bad:
        raise ValueError('Enter the REAL public Whop product URLs in products.json for: ' + ', '.join(bad))


def with_utm(url, platform, product):
    parts = urlsplit(url)
    old = [(k,v) for k,v in parse_qsl(parts.query) if not k.lower().startswith('utm_')]
    params = old + [('utm_source', platform), ('utm_medium', 'organic_social'), ('utm_campaign', 'cheapeasy_growthbot'), ('utm_content', product)]
    return urlunsplit((parts.scheme,parts.netloc,parts.path,urlencode(params),parts.fragment))


def graph(token, query, variables=None):
    data = json.dumps({'query':query, 'variables': variables or {}}).encode('utf-8')
    req = urllib.request.Request(API,data=data,headers={'Authorization':'Bearer '+token, 'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as ex:
        raise RuntimeError(f'Buffer API HTTP {ex.code}; check credentials and channel permissions') from ex
    if result.get('errors'):
        raise RuntimeError('Buffer GraphQL error: '+str([e.get('message','error') for e in result['errors']]))
    return result.get('data',{})


def get_org(token):
    res=graph(token,'query { account { organizations { id name } } }')
    orgs=res.get('account',{}).get('organizations',[])
    specified=os.environ.get('BUFFER_ORG_ID','').strip()
    if specified:
        if orgs and specified not in {o['id'] for o in orgs}:
            raise ValueError('BUFFER_ORG_ID is not found in your Buffer account')
        return specified
    if len(orgs)!=1:
        raise ValueError(f'Found {len(orgs)} Buffer organizations; set BUFFER_ORG_ID explicitly.')
    return orgs[0]['id']


def get_channels(token, org):
    res=graph(token,'query ($input: ChannelsInput!) { channels(input:$input) { id name service isQueuePaused } }',{'input':{'organizationId':org}})
    return [c for c in res.get('channels',[]) if c.get('service','').lower() in ALLOWED and not c.get('isQueuePaused')]


def get_pinterest_board(token, channel_id):
    override = os.getenv('PINTEREST_BOARD_ID','').strip()
    if override: return override
    query='query ($input: ChannelInput!) { channel(input:$input) { metadata { ... on PinterestMetadata { boards { serviceId } } } } }'
    data=graph(token,query,{'input':{'id':channel_id}})
    boards = data.get('channel',{}).get('metadata',{}).get('boards',[]) or []
    if len(boards)!=1:
        raise ValueError(f'Pinterest has {len(boards)} boards. Create one public board for Cheap&Easy or specify PINTEREST_BOARD_ID.')
    return boards[0]['serviceId']


def topics(products):
    # Mix products evenly; e.g. flips0, adhd0, hospital0, flips1...
    keys = [key for key in ('flips','adhd','hospital') if key in products]
    seen = []
    for i in range(max(len(products[k]['tips']) for k in keys)):
        for key in keys:
            if i < len(products[key]['tips']):
                seen.append((key, i))
    return seen


def caption(cfg, key, index, platform):
    item=cfg['tips'][index]
    headline=item['hook'].strip()
    tip=item['tip'].strip()
    if platform=='instagram':
        cta=f'For more practical tools, find {cfg["title"]} via our profile link.'
    else:
        cta=f'Our {cfg["title"]} guide includes more practical templates. See it here: {with_utm(cfg["url"],platform,key)}'
    text = f'{headline}\n\n{tip}\n\n{cta}'
    if key=='hospital':
        text+='\n\nIndependent organisational resource; follow your healthcare team’s advice.'
    return text


def media_url(repo, branch, key, tip_idx, service):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):
        raise ValueError('GH_REPO must be owner/repository, like username/cheapeasy-growthbot')
    if not re.fullmatch(r'[A-Za-z0-9_./-]+', branch):
        raise ValueError('GH_BRANCH is not a valid branch name')
    return f'https://raw.githubusercontent.com/{repo}/{branch}/media/{key}_{tip_idx:02d}_{service}.jpg'


def create_input(channel, cfg, key, tip_idx, repo, branch, board_id=None):
    service=channel['service'].lower()
    asset = media_url(repo,branch,key,tip_idx,service)
    post={'text':caption(cfg,key,tip_idx,service), 'channelId':channel['id'],
          'schedulingType':'automatic', 'mode':'addToQueue',
          'assets':[{'image':{'url':asset}}], 'aiAssisted':True}
    if service=='instagram':
        post['metadata']={'instagram':{'type':'post','shouldShareToFeed':True}}
    elif service=='facebook':
        post['metadata']={'facebook':{'type':'post'}}
    elif service=='pinterest':
        if not board_id: raise ValueError('Pinterest needs a board ID')
        post['metadata']={'pinterest':{'boardServiceId':board_id,
                                    'title':cfg['tips'][tip_idx]['hook'][:95],
                                    'url':with_utm(cfg['url'],service,key)}}
    return post


def post_buffer(token, payload):
    query='''mutation ($input: CreatePostInput!) { createPost(input:$input) { ... on PostActionSuccess { post { id dueAt } } ... on MutationError { message } } }'''
    data=graph(token,query,{'input':payload})
    r=data.get('createPost') or {}
    if not r.get('post') or not r['post'].get('id'):
        raise RuntimeError('Buffer rejected the post: '+str(r.get('message','unknown error')))
    return r['post']


def main():
    live=os.getenv('LIVE_POSTING','').strip().lower()=='true'
    products=json.loads((ROOT/'products.json').read_text(encoding='utf-8'))
    required_urls(products)
    topic_list=topics(products)
    repo = os.getenv('GH_REPO') or os.getenv('GITHUB_REPOSITORY') or ''
    branch=os.getenv('GH_BRANCH') or os.getenv('GITHUB_REF_NAME') or 'main'
    if not repo and live:
        raise ValueError('Set GH_REPO, or run this in a GitHub Actions repository.')
    if not repo: repo='EXAMPLE/cheapeasy-growthbot' # preview placeholder only
    state_file=ROOT/'state'/'posted.json'
    state=json.loads(state_file.read_text(encoding='utf-8'))
    token=os.getenv('BUFFER_API_KEY','').strip()
    if live and not token: raise ValueError('Missing BUFFER_API_KEY secret')
    print('MODE:', 'QUEUE REAL POSTS' if live else 'PREVIEW ONLY — no posting')
    if token:
        org=get_org(token)
        channels=get_channels(token,org)
    else:
        channels=[{'id':k+'_preview','name':k.title()+' (example)','service':k,'isQueuePaused':False} for k in ('pinterest','instagram','facebook')]
    if not channels:
        raise ValueError('No supported Buffer channels connected: Pinterest, Instagram or Facebook.')
    any_success=False
    for ch in channels:
        service=ch['service'].lower()
        rec=state.setdefault('channels',{}).setdefault(ch['id'],{})
        n=rec.get('next_index', 0)
        if n>=len(topic_list):
            print(f'{service}: all {len(topic_list)} unique posts queued. No recycling; add fresh reviewed tips.')
            continue
        # All channels get all 36 reviewed topics, with a different starting point.
        key, tip_idx = topic_list[(n + PLATFORM_OFFSETS[service]) % len(topic_list)]
        board_id=None
        if service=='pinterest':
            board_id=get_pinterest_board(token,ch['id']) if live else 'PREVIEW_BOARD'
        post=create_input(ch,products[key],key,tip_idx,repo,branch,board_id)
        print(f'{service} / {key} #{tip_idx+1}: {post["text"][:105]!r}')
        print('  Image:',post['assets'][0]['image']['url'])
        if not live:
            continue
        try:
            result=post_buffer(token,post)
            print(f'  QUEUED {result["id"]} for {result.get("dueAt")}')
        except Exception as exc:
            # Continue to other channels; preserve successful channels' state.
            print('  ERROR:',exc,file=sys.stderr)
            continue
        rec['next_index']=n+1
        rec.setdefault('history',[]).append({'post_id':result['id'],'key':key,'tip':tip_idx,
                                          'queued_at':datetime.now(timezone.utc).isoformat(),
                                          'due_at':result.get('dueAt')})
        any_success=True
    if any_success:
        state_file.write_text(json.dumps(state,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Done.', 'Progress saved.' if any_success else 'No changes.')


if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        sys.exit(1)
