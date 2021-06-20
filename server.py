from flask import Flask, request, jsonify,make_response
import json
from paper_summarization import main
from data_crawling import get_top_10_papers,get_files,get_random_papers
import os
from threading import Thread

#from flask_restx import Api, Resource

app = Flask(__name__)

interest = 'UNK'

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

@app.route('/interest', methods=['POST'])
def postInterest():
    global interest

    data = request.get_json(silent=True, cache=False, force=True)
    print("Received data:", data)

    interest = data['interest']
    for key in cs.keys():
        interest = interest.replace(key, cs[key])
   
    print("Interests:", interest)

    with open('./save_fields.txt','w') as f:
        f.write(interest)

    return jsonify(interest)

def generate_tags(tags, publication):
    tag = ""
    list_of_values = list(cs.values())
    list_of_keys = list(cs.keys())

    for t in tags:
        tag += '#'+list_of_keys[list_of_values.index(t)].replace(' ','_')+' '

    tag += '#'+publication

    return tag

def send_summary(fields):
    count = 0

    with open('./summary_data_ready.json') as f:
        summary_data = json.load(f)

    paper = {}

    with open('./served_papers_list.txt','a') as f:
        for k in list(summary_data.keys()):
            if count == 10:
                break
            if fields[0] != '' and fields[0] != 'UNK':
                if len(set(summary_data[k]['tags']) & set(fields)) == 0:
                    continue
            f.write(k+'\n')
            data = summary_data[k]
            ccount = str(count)
            paper['title' + ccount] = data['title']
            paper['author' + ccount] = ','.join(data['authors'])
            paper['publication' + ccount] = data['comments']
            paper['year' + ccount] = data['year']
            paper['summary' + ccount] = data['summary']
            paper['pdf' + ccount] = data['pdf']   # pdf URL!
            paper['tag' + ccount] = generate_tags(data['tags'],data['publication'])
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

    if os.path.exists('./save_fields.txt') and interest == 'UNK':
        interest = open('./save_fields.txt','r').read()

    fields = interest.strip().split('\t')
    print(fields)

    if os.path.exists('./summary_data_ready.json'):
        paper = send_summary(fields)
        
    else:
        for i in range(10):
            paper['title'+str(i)] = 'please wait'
            paper['author'+str(i)] = ''
            paper['publication'+str(i)] = ''
            paper['year'+str(i)] = ''
            paper['summary'+str(i)] = ''
            paper['pdf'+str(i)] = ''
            paper['tag'+str(i)] = ''

    if interest != 'UNK':
        thread = Thread(target=summarization_caching,args=(fields,))
        thread.daemon = True
        thread.start()
    response = make_response(json.dumps(paper,ensure_ascii=False).encode('utf-8'))
    print(paper)
    return response

if __name__ == "__main__":
    app.run(debug=True, host="163.239.28.25", port=5000)
