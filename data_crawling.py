from requests import get  # to make GET request
from selenium import webdriver
import requests
import time
from bs4 import BeautifulSoup
import re
import os
import json
import tqdm

pubs = {
            'cs.ai': ['nips','ieee','eccv','cvpr','iccv','aaai','icml','iclr','iswc','neurlps'],
            'cs.db': ['sigir','sigmod','WWW','acm','ieee','icde','wsdm','cikm','icwsm'],
            'cs.os': ['ieee', 'acm', 'asplos', 'usenix', 'fast', 'eurosys', 'osdi', 'sosp', 'jss', 'tecs' ],
            'cs.dc': ['acm','icdcs','hpdc', 'ieee', 'ppopp','ndss', 'tpds', 'jpdc', 'socc', 'dc'],
            'cs.ni': ['globecom','ieee','icc','infocom','sigcomm','sigmetrics','acm'],
            'cs.cv': ['bmvc','cvpr','eccv','iccv','scia','ssiai','ieee','acmmm','iros'],
            'cs.pl': ['ecoop','esop','acm','sigplan','icfp','iclp','oopsla','popl','pldi'],
            'cs.ds': ['stoc','focs','soda','spaa','wads','esa','swat','acm','ieee','isaac'],
            'cs.cl': ['acl','emnlp','naacl','tacl','SemEval','coling','eacl','conll','lrec','sigdial'],
            'cs': ['acm','ieee','iclr','nips','icml','acs']
        }

def download(url, file_name):
    with open(file_name, "wb") as file:   # open in binary mode
        response = get(url)               # get request
        file.write(response.content)      # write to file

def get_random_papers():
    return get_top_10_papers(['cs'])

def get_top_10_papers(fields):
    
    def get_papers(fields,size):
        URL = f"https://arxiv.org/search/advanced"
        param = {
                'advanced' : '',
                'classification-computer_science' : 'y',
                'date-date_type' : 'submitted_date',
                'abstracts' : 'show',
                'size' : '50',
                'order' : '-announced_date_first'
                }

        cnt = 0
        for field in fields:
            for pub in pubs[field]:
                param[f'terms-{cnt}-operator'] = 'AND' if cnt==0 else 'OR'
                param[f'terms-{cnt}-term'] = field
                param[f'terms-{cnt}-field'] = 'cross_list_category'
                cnt += 1
                param[f'terms-{cnt}-operator'] = 'AND'
                param[f'terms-{cnt}-term'] = pub
                param[f'terms-{cnt}-field'] = 'comments'
                cnt += 1

        response = requests.get(URL,params=param)
        print(response)
        print(response.url)
        print(response.status_code)
    
        soup = BeautifulSoup(response.content, 'html.parser')

        names = soup.find_all(attrs={'class':'list-title is-inline-block'})
        codes = [re.findall('.*>arXiv:(.*)</a>\s',str(name))[0] for name in names]
        titles = [t.text.strip() for t in soup.find_all(attrs={'class':'title is-5 mathjax'})]
        authors = [[author.text.strip() for author in a.find_all(name='a')] for a in soup.find_all(attrs={'class':'authors'})]
        comments = soup.find_all(attrs={'class':'has-text-grey-dark mathjax'})
        tags = [t.text.lower().strip().split('\n') for t in soup.find_all(attrs={'class':'tags is-inline-block'})]
        keywords = [t.text.strip() for t in soup.find_all(attrs={'class':'search-hit mathjax'})]

        mapper = dict()
        print(list(pubs.keys()))
        print(tags[0])
        print([t for t in tags[0] if t in list(pubs.keys())])

        for i in range(size):
            mapper[codes[i]] = {
                    'title':titles[i],
                    'authors':authors[i],
                    'comments':comments[i].text.strip(),
                    'year':'20'+codes[i][:2],
                    'tags':[t for t in tags[i] if t in list(pubs.keys())],
                    'publication':keywords[i],
                    'pdf':'https://arxiv.org/pdf/'+codes[i]+'.pdf'
                    }

        return mapper
    
    size = 50
    mapper = dict()
    new_mapper = get_papers(fields,size)

    if os.path.exists('./mapper.json'):
        with open('./mapper.json','r') as f:
            mapper = json.load(f)

    mapper.update(new_mapper)

    with open('./mapper.json','w') as f:
       json.dump(mapper,f)

    while True:
        ret = check_served(mapper)
        if ret != -1:
            break
        mapper.update(get_titles_codes(fields,size+10))
        size += 10

    print(ret)
    return ret 

def check_served(mapper):
    if not os.path.exists('./served_papers_list.txt'):
        return list(mapper.keys())[:10]

    with open('./served_papers_list.txt','r') as f:
        served_codes = f.read().split('\n')

    new_codes = [c for c in mapper.keys() if c not in served_codes]
    if len(new_codes) >= 10:
        return new_codes[:10]
    else:
        return -1

def get_files(papers):
    if not os.path.exists('./data/'):
        os.mkdir('./data/')
    for p in papers:
        download(f'https://arxiv.org/pdf/{p}.pdf',f'./data/{p}.pdf')
        print(f'{p}.pdf download completed.')

if __name__ == '__main__':
    papers = get_top_10_papers(['cs.cl'])
    get_files(papers)
