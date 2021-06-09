# -*- coding: utf-8 -*-
"""캡스톤디자인_논문요약.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1yAPCVIlePmahMfISR_R34YDY3QQo8unQ
"""

import re

from io import StringIO
import urllib.request
import pandas as pd
import time

from transformers import pipeline, BartTokenizer

from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser

import nltk
# nltk.download('punkt')

import logging
from tqdm import tqdm

import json
import os

logger = logging.getLogger("PaperSummary")
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
logger.addHandler(stream_handler)


# %load_ext google.colab.data_table

def pdf_to_text(filename):
  output_string = StringIO()
  with open(filename, 'rb') as in_file:
      parser = PDFParser(in_file)
      doc = PDFDocument(parser)
      rsrcmgr = PDFResourceManager()
      device = TextConverter(rsrcmgr, output_string, laparams=LAParams())
      interpreter = PDFPageInterpreter(rsrcmgr, device)
      logger.info("Converting pdf to text ...")
      for page in PDFPage.create_pages(doc):
          interpreter.process_page(page)
  return output_string.getvalue()

def preprocess_text(filename):
  text = pdf_to_text(filename)
  print('paper wordcount:',len(text))
  original_text_length = len(text)

  if 'Introduction' in text:
    text = text.partition('Introduction')[2]
  elif 'INTRODUCTION' in text:
    text = text.partition('INTRODUCTION')[2]
  if 'Acknowledgements' in text:
    text = text.partition('Acknowledgements')[0].strip()
  elif 'ACKNOWLEDGEMENTS' in text:
    text = text.partition('ACKNOWLEDGEMENTS')[0].strip()
  if 'References' in text:
    text = text.partition('References')[0].strip()
  elif 'REFERENCES' in text:
    text = text.partition('REFERENCES')[0].strip()
  # print(text)
  text = re.sub('ﬀ','ff',text)
  text = re.sub('[(].+[)]','',text)
  text = re.sub('\[[^a-zA-Z]+\]','',text)
  text = re.sub('-\n','',text)
  text = re.sub('\n',' ',text)
  text = re.sub('\d+\.\s','',text)
  paragraphs = re.split('\s{2,}',text)
  """for p in paragraphs:
    print(p+'\n')"""
  logger.info("Splitting paragraphs ...")
  new_paragraphs = [p for p in tqdm(paragraphs) if re.search('[a-z]+',p,re.I)]

  paragraphs = []
  new_p = ""
  for p in new_paragraphs:
    if len(new_p) != 0:
      new_p += ' '+p
      if p.endswith('.') and re.search('al\s*.$',p) == None:
        paragraphs.append(new_p)
        new_p = ""
    else:
      if p.endswith('.') and re.search('al\s*.$',p) == None:
        paragraphs.append(p)
      else:
        new_p = p

  new_paragraphs = [p for p in paragraphs if re.search('Table.+:',p) == None and re.search('Fig.+:',p) == None]

  return new_paragraphs, original_text_length

def generate_chunks(new_paragraphs,tokenizer):
  flag = False
  large_paragraph = ""
  modified_paragraphs = []
  for paragraph in tqdm(new_paragraphs):
    if len(tokenizer.encode(paragraph)) > 1024:
      if flag:
        modified_paragraphs.append(large_paragraph)
        large_paragraph = ""
        flag = False
        continue
      sents = nltk.sent_tokenize(paragraph)
      small_paragraph = ""
      paragraphs = []
      for sent in sents:
        if len(tokenizer.encode(small_paragraph))+len(tokenizer.encode(sent)) < 1024:
          small_paragraph += ' '+sent
        else:
          paragraphs.append(small_paragraph)
          small_paragraph = ""
      modified_paragraphs.extend(paragraphs)
    else:
      if len(tokenizer.encode(large_paragraph)) + len(tokenizer.encode(paragraph)) < 1024:
        large_paragraph += ' '+paragraph
      else:
        modified_paragraphs.append(large_paragraph)
        # print(len(large_paragraph))
        large_paragraph = paragraph
      flag = True
  return modified_paragraphs

def generate_summarization(modified_paragraphs,summarizer):
  summarization = []

  for paragraph in tqdm(modified_paragraphs):
      summarized = summarizer(paragraph)
      summarization.append(summarized[0]['summary_text'])

  return summarization

def main(papers):
  files = [f'./data/{p}.pdf' for p in papers]
  
  logger.info("Initializing Summarizer & Tokenizer ...")
  # max seq length for this model = 1024
  summarizer = pipeline(task="summarization", model="facebook/bart-large-cnn")
  tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")
  logger.info("Done Initializing!")

  with open('./mapper.json','r') as f:
    mapper = json.load(f)

  summary_data = dict()
  if os.path.exists('./summary_data_ready.json'):
    with open('./summary_data_ready.json') as f:
        summary_data = json.load(f)

  for i,f in enumerate(files):
    logger.info("Preprocessing Paper ...")
    paragraphs,original_text_length = preprocess_text(f)
    # print(paragraphs)

    logger.info("Generating Chunks ...")
    chunks = generate_chunks(paragraphs,tokenizer)

    logger.info("Generating Summarization ...")
    summary = generate_summarization(chunks,summarizer)

    summary = '\n\n'.join(summary)
    print(summary)
    print("summary word count:",len(summary))

    summary_data[papers[i]] = mapper[papers[i]]
    summary_data[papers[i]]['summary'] = summary
    summary_data[papers[i]]['paper_char_count'] = original_text_length
    summary_data[papers[i]]['summary_char_count'] = len(summary)
  
  with open('./summary_data_ready.json','w') as f:
    json.dump(summary_data,f)

if __name__ == '__main__':
    
    files = [f for f in os.listdir('./data/') if f.endswith('.pdf')]
    
    for f in files:
        main(f)