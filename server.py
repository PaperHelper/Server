from flask import Flask, request, jsonify
import json
from paper_summarization import main
from data_crawling import get_top_10_papers,get_files,get_random_papers
import os
from threading import Thread

#from flask_restx import Api, Resource

app = Flask(__name__)
#api = Api(app)

'''
POST data (json)
{
    'interest': 'cs.ai\tcs.cr'
}
'''

interest = ''

@app.route('/interest', methods=['POST'])
def postInterest():
    global interest

    cs = {"Artificial Intelligence":"cs.ai", 
            "Database":"cs.db", 
            "Operating Systems":"cs.os", 
            "Distributed, Parallel, and Cluster Computing":"cs.dc", 
            "Networking and Internet Architecture":"cs.ni", 
            "Computer Vision and Pattern Recognition":"cs.cv", 
            "Robotics":"cs.ro",
            "Programming Languages":"cs.pl",
            "Data Structures and Algorithms":"cs.ds",
            "Computation and Language":"cs.cl"
            }

    data = request.get_json(silent=True, cache=False, force=True)
    print("Received data:", data)

    interest = data['interest']
    for key in cs.keys():
        interest = interest.replace(key, cs[key])
   
    print("Interests:", interest)
    return jsonify(interest)


'''
GET data (json)
{
    "title0": "title0",
    "author0": "author0",
    "publication0": "publication0",
    "year0": "year0",
    "summary0": "summary0",
    "pdf0": "pdf0"
    "title1": "title1",
    "author1": "author1",
    "publication1": "publication1",
    "year1": "year1",
    "summary1": "summary1",
    "pdf1": "pdf1"
    "title2": "title2",
    "author2": "author2",
    "publication2": "publication2",
    "year2": "year2",
    "summary2": "summary2",
    "pdf2": "pdf2"
}
'''

def send_summary(fields):
    count = 0

    with open('./summary_data_ready.json') as f:
        summary_data = json.load(f)

    paper = {}

    with open('./served_papers_list.txt','a') as f:
        for k in list(summary_data.keys()):
            if count == 3:
                break
            if fields[0] != '':
                if len(set(summary_data[k][tags]) & set(fields)) == 0:
                    continue
            f.write(k+'\n')
            data = summary_data[k]
            ccount = str(count)
            paper['title' + ccount] = data['title']
            paper['author' + ccount] = ','.join(data['author'])
            paper['publication' + ccount] = data['publication']
            paper['year' + ccount] = data['year']
            paper['summary' + ccount] = data['summary']
            paper['pdf' + ccount] = data['pdf']   # pdf URL!
            count += 1

    return paper

def summarization_caching(fields):
    if len(interest) == 0:
        paper_list = get_random_papers()
    else:
        paper_list = get_top_10_papers(fields)

    # download papers for summarization
    get_files(paper_list)

    # summarize given papers
    main(paper_list)

@app.route('/paper', methods=['GET'])
def getPaper():
    paper = {}

    fields = interest.strip().split('\t')
    print(fields)

    if os.path.exists('./summary_data_ready.json'):
        paper = send_summary(fields)
        paper = json.dumps(paper)
        print(paper)

    else:
        print('here!')
        for i in range(3):
            paper['title'+str(i)] = 'please wait'
            paper['author'+str(i)] = ''
            paper['publication'+str(i)] = ''
            paper['year'+str(i)] = ''
            paper['summary'+str(i)] = ''
            paper['pdf'+str(i)] = ''

    thread = Thread(target=summarization_caching,args=(fields,))
    thread.daemon = True
    thread.start()
    paper = json.dumps(paper)
    print(paper)
    return jsonify(paper)

if __name__ == "__main__":
    app.run(debug=True, host="163.239.28.25", port=5000)
