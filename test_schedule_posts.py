import json
import unittest
from pathlib import Path
from schedule_posts import topics, create_input, with_utm, caption, media_url, PLATFORM_OFFSETS

ROOT=Path(__file__).resolve().parent
PRODS=json.loads((ROOT/'products.json').read_text())
for k,v in PRODS.items():
    v['url']=f'https://whop.com/cheapeasy/test-{k}/'

class SchedulerTests(unittest.TestCase):
    def test_media_quantity(self):
        self.assertEqual(len(list((ROOT/'media').glob('*.jpg'))),108)
    def test_topics(self):
        self.assertEqual(len(topics(PRODS)),36)
        self.assertEqual(topics(PRODS)[:3],[('flips',0),('adhd',0),('hospital',0)])
    def test_each_channel_uses_all_topics(self):
        order = topics(PRODS)
        for service, offset in PLATFORM_OFFSETS.items():
            selections = [order[(n + offset) % len(order)] for n in range(len(order))]
            self.assertEqual(len(set(selections)), 36, service)
    def test_utm_tracking(self):
        url=with_utm('https://whop.com/cheapeasy/test/?foo=bar','pinterest','flips')
        self.assertIn('foo=bar',url)
        self.assertIn('utm_source=pinterest',url)
    def test_pinterest_board(self):
        channel={'id':'abc','service':'pinterest'}
        data=create_input(channel,PRODS['hospital'],'hospital',0,'owner/repo','main','board123')
        self.assertEqual(data['metadata']['pinterest']['boardServiceId'],'board123')
        self.assertEqual(data['metadata']['pinterest']['url'].split('?')[0],PRODS['hospital']['url'])
    def test_instagram_caption(self):
        channel={'id':'abc','service':'instagram'}
        data=create_input(channel,PRODS['adhd'],'adhd',0,'owner/repo','main')
        self.assertEqual(data['metadata']['instagram']['type'],'post')
        self.assertIn('profile link',data['text'])
        self.assertNotIn('https://',data['text'])
    def test_facebook_metadata(self):
        channel={'id':'abc','service':'facebook'}
        data=create_input(channel,PRODS['flips'],'flips',0,'owner/repo','main')
        self.assertEqual(data['metadata']['facebook']['type'],'post')
        self.assertIn('utm_source=facebook',data['text'])
    def test_media(self):
        self.assertEqual(media_url('x/y','main','flips',0,'pinterest'),
            'https://raw.githubusercontent.com/x/y/main/media/flips_00_pinterest.jpg')

if __name__=='__main__': unittest.main()
