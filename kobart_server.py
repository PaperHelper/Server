from flask import Flask, request, jsonify,make_response
import json
from paper_summarization import main
from data_crawling import get_top_10_papers,get_files,get_random_papers
import os
from threading import Thread

#from flask_restx import Api, Resource

app = Flask(__name__)


@app.route('/interest', methods=['POST'])
def postInterest():
    global interest

    data = request.get_json(silent=True, cache=False, force=True)
    print("Received data:", data)

    interest = data['interest']
    for key in cs.keys():
        interest = interest.replace(key, cs[key])
   
    print("Interests:", interest)
    return jsonify(interest)

def send_summary():

    papers = os.listdir('./paper_kor')
    papers = [f for f in papers if f.endswith('.txt')]
    paper = dict()

    for i,f in enumerate(papers):

        summary = open(f'./kobart_summarized/summarized_{f}','r').read()
        data = open(f'./kobart_paper_data/data_{f}','r').readlines()
        data = [d.strip() for d in data]

        paper['title'+str(i)] = data[0]
        paper['author'+str(i)] = data[1]
        paper['publication'+str(i)] = data[2]
        paper['year'+str(i)] = data[3]
        paper['summary'+str(i)] = summary
        paper['pdf'+str(i)] = data[4]
        paper['tag'+str(i)] = data[5]

    return paper


@app.route('/paper', methods=['GET'])
def getPaper():
    paper = {}

    fields = interest.strip().split('\t')
    print(fields)

    if os.path.exists('./kobart_summarized/'):
        paper = send_summary()
        
    else:
        for i in range(10):
            paper['title'+str(i)] = 'please wait'
            paper['author'+str(i)] = ''
            paper['publication'+str(i)] = ''
            paper['year'+str(i)] = ''
            paper['summary'+str(i)] = ''
            paper['pdf'+str(i)] = ''
            paper['tag'+str(i)] = ''

    response = make_response(json.dumps(paper,ensure_ascii=False).encode('utf-8'))
    print(paper)
    return response

if __name__ == "__main__":
    # paper = send_summary()
    # print(paper)
    app.run(debug=True, host="163.239.28.25", port=5000)
