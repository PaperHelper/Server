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


# %load_ext google.colab.data_table

def pdf_to_text(filename):
  output_string = StringIO()
  with open(filename, 'rb') as in_file:
      parser = PDFParser(in_file)
      doc = PDFDocument(parser)
      rsrcmgr = PDFResourceManager()
      device = TextConverter(rsrcmgr, output_string, laparams=LAParams())
      interpreter = PDFPageInterpreter(rsrcmgr, device)
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
  else:
    print("Introduction not in paper!")
  if 'Acknowledgements' in text:
    text = text.partition('Acknowledgements')[0].strip()
  elif 'ACKNOWLEDGEMENTS' in text:
    text = text.partition('ACKNOWLEDGEMENTS')[0].strip()
  else:
      print("Acknowledgements not in paper!")
  if 'References' in text:
    text = text.partition('References')[0].strip()
  elif 'REFERENCES' in text:
    text = text.partition('REFERENCES')[0].strip()
  else:
    print("References not in paper or there was Acknowledgements section!")
  # print(text)
  text = re.sub(chr(64256),'ff',text)
  text = re.sub('\([\w\W]+?\)','',text)
  text = re.sub('\[[^a-zA-Z]+\]','',text)
  text = re.sub('-\n','',text)
  text = text.replace('\n','\t')
  text = re.sub('\t{3,}','\n\n\n',text)
  text = re.sub('\t{2}','\n\n',text)
  text = text.replace('.\t','.\n') 
  text = text.replace('al.\n','al. ')
  text = text.replace('\t',' ')
  paragraphs = re.split('\n{2,}',text)
  paragraphs = [p.replace('\n',' ') for p in tqdm(paragraphs) if re.search('[a-z]+',p,re.I)]
  for i,p in enumerate(paragraphs):
    print(i,'th paragraph')
    print(p+'\n')
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

  f = open('text-summary.txt','w')

  for paragraph in tqdm(modified_paragraphs):
      summarized = summarizer(paragraph)
      summarization.append(summarized[0]['summary_text'])
      f.write('text:\n')
      f.write(paragraph+'\n\n')
      f.write('summary:\n')
      f.write(summarized[0]['summary_text']+'\n\n\n\n')

  return summarization

def main(papers):
  logger = logging.getLogger("PaperSummary")
  logger.setLevel(logging.INFO)
  stream_handler = logging.StreamHandler()
  logger.addHandler(stream_handler)

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
    print(f"Processing #{i+1} paper ({f})")

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
  """
  files = [f[:-4] for f in os.listdir('./data/') if f.endswith('.pdf')]
    
  main(files[:1]) 
  """
  summarizer = pipeline(task="summarization", model="facebook/bart-large-cnn")
  tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")
  paragraph="""Since a majority of the mature stock markets, like those in the U.S.A,
Korea, U.K., and France, are weak-form efficient markets [3], many studies have been conducted on predicting stock prices using financial
news. To quantitatively measure market states, various measurement
methods have been applied. One method, the Hurst Exponent, is a
concept used in econophysics to measure market states [3]. The Hurst
Exponent measures long-term memory quantitatively [4]. If the Hurst
Exponent is < 0.5, stock prices can be interpreted as mean-reverting. If
it equals 0.5, it means that stock prices follow a random walk, and if it
is > 0.5, stock prices can be interpreted as following a trend. In other
words, the larger the Hurst Exponent, the greater the effect of past
prices on current prices. If the Hurst Exponent is high, the stock market
is not a weak-form efficient market because it can be predicted with
historical prices. According to Eom et al. [3], the Korean stock market
has a Hurst Exponent of approximately 0.5 so that the Korean stock
market is the weak-form efficient market. Therefore, when predicting
stock prices in the Korean market, it is meaningful to use public information
for analysis, such as financial news, rather than historical
prices.
In research on stock price forecasting through financial news, it is
common to build a keyword dictionary for each company. This dictionary
provides keywords that influence the fluctuations of stocks of
individual companies, and they should be used to predict future stock
prices. Recently, studies on identifying relevant firms [5], and studies
on reflecting the effects of relevant firms based on the Global Industry
Classification Standard (GICS) sector [6,7] emerge. Especially, Shynkevich
et al. [7] constructed an individual firm dictionary, sub-industry
dictionary, industry dictionary, group industry dictionary, and sector
dictionary in the S & P 500 healthcare sector and predicted stock
movements with the combination of them. The results of this study are
as follows: The prediction accuracy of integrating them is higher than
that of news of individual firms only. In other words, the dictionaries
that include higher-level concepts, e.g. sector dictionaries, reflect information
that affects industry characteristics or industries that are not
covered by the concepts of the subordinate individual firms.
Although research has progressed gradually on the basis of the influence
within the GICS sector, it has been conducted based on the
assumption that every firm influences other firms, and the influence
between firms is bidirectional. However, companies in the same GICS
sector may not influence each other, and there is a structure in which a
company affects other companies but not inversely [8]. In this study,
we overcome the limitations of the existing research by applying the
transfer entropy technique, which has been actively studied in the
complex system theory. We find the causal relationships of the firms
within the GICS sectors and predict the stock price based on causal
relationships. Especially, we integrate the effect of the target firm and
the effects of the causal firms by employing Multiple Kernel Learning
method [9]."""
  p2 = """The results show that our approach improves the prediction performance
in comparison with approaches that are based on news on
target firms [10] and on the GICS Sector-based integration approach
[7], which are two state-of-the-art algorithms. Furthermore, the experimental
results show that the proposed method can predict the stock
price directional movements even when there is no financial news on
the target firm, but financial news is published on causal firms. In addition,
we find that the results change by setting the statistical significance
of transfer entropy. Therefore, it is important to set the
threshold of statistical significance through a grid search.
In this study, we make three main contributions: First, in solving
socioeconomic problems, we were able to achieve higher performance
by successfully combining physics theory with machine learning. To the
best of our knowledge, this paper is the first paper to combine complex
system methodology with machine learning. Second, previous studies
have predicted stock prices at the individual level and searched for
relevant companies to consider their impact. This study is the first to
predict stock prices while considering the causality between the companies.
Finally, existing studies were able to predict stock movements only when the news on the company was released. In this paper, we
propose a method for predicting stock movements with a causal relationship
through causality detection, even when no news is published
directly.
We organize the remainder of this paper as follows: Section 2 provides
an overview of the relevant literature on complex networks and
text mining. Section 3 describes news and stock datasets, transfer entropy
analysis, text pre-processing techniques, machine learning approaches
and evaluation metrics. Section 4 describes the experimental
results. Section 5 presents the study's conclusions and outlines directions
for future work."""
  summarized = summarizer(paragraph)
  print('text:\n')
  print(paragraph+'\n\n')
  print('summary:\n')
  print(summarized[0]['summary_text']+'\n\n\n\n')

  summarized = summarizer(p2)
  print('text:\n')
  print(paragraph+'\n\n')
  print('summary:\n')
  print(summarized[0]['summary_text']+'\n\n\n\n')
