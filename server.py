from flask import Flask, request, jsonify
import json
#from flask_restx import Api, Resource

app = Flask(__name__)
#api = Api(app)

'''
POST data (json)
{
    'interest': 'cs.ai\tcs.cr'
}
'''
@app.route('/interest', methods=['POST'])
def postInterest():
    cs = {"Artificial Intelligence":"cs.ai", 
            "Database":"cs.db", 
            "Operating Systems":"cs.os", 
            "Distributed, Parallel, and Cluster Computing":"cs.dc", 
            "Networking and Internet Architecture":"cs.ni", 
            "Computer Vision and Pattern Recognition":"cs.cv", 
            "Robotics":"cs.ro",
            "Programming Languages":"cs.pl",
            "Data Structures and Algorithms":"cs.ds",
            "Cryptography and Security":"cs.cr"
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
    'paper': [
        {
            "title": "title1",
            "author": "author1",
            "publication": "publication1",
            "year": "year1",
            "summary": "summary1",
            "pdf": "pdf1"
        },
        {
            "title": "title2",
            "author": "author2",
            "publication": "publication2",
            "year": "year2",
            "summary": "summary2",
            "pdf": "pdf2"
        },
        {   
            "title": "title3",
            "author": "author3",
            "publication": "publication3",
            "year": "year3",
            "summary": "summary3",
            "pdf": "pdf3"
        }
    }
'''
@app.route('/paper', methods=['GET'])
def getPaper():
    json_object = {'paper': []}

    for i in range(3):
        paper = {}
        paper['title'] = 'title' + str(i)
        paper['author'] = 'author' + str(i)
        paper['publication'] = 'publication' + str(i)
        paper['year'] = 'year' + str(i)
        paper['summary'] = 'summary' + str(i)
        paper['pdf'] = 'pdf' + str(i)   # pdf URL!
        json_object['paper'].append(paper)


    json_object = json.dumps(json_object)
    print(json_object)

    return jsonify(json_object)

if __name__ == "__main__":
    app.run(debug=True, host="163.239.28.25", port=5000)
