#!/usr/bin/env python3
import sys
import base64
import requests
import string
import re
import heapq
import operator
import textdistance
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from summa.summarizer import summarize
from rake_nltk import Rake
from random import shuffle

def decode(req):
	req = req.json()
	content = base64.b64decode(req['content'])
	content = str(content, "utf-8")

	content = content.lower()
	return content

def regex(content):
	filtered_content = re.sub(r'\`\`\`.*\`\`\`', '', content, flags = re.MULTILINE|re.DOTALL) # remove code segments
	filtered_content = re.sub(r'\|.*\|', '', filtered_content) # remove code segments
	filtered_content = re.sub(r'\<.*\>', '', filtered_content) # remove any '<WORD>'
	filtered_content = re.sub(r'\`.*\`', '', filtered_content) # remove any '`WORD`'
	filtered_content = re.sub(r'http\S+', '', filtered_content) # remove links
	filtered_content = re.sub(r'\[', '', filtered_content) # remove opening square brace
	filtered_content = re.sub(r'\]', '', filtered_content) # remove closing square brace
	filtered_content = re.sub(r'\n\s*\n', '\n', filtered_content) # remove empty lines
	filtered_content = re.sub(r'\_', '', filtered_content) # remove underscore
	filtered_content = re.sub(r'\#', '', filtered_content) # remove hash symbol
	filtered_content = re.sub(r':', '', filtered_content) # remove colon
	filtered_content = re.sub(r'=', '', filtered_content) # remove equals

	return filtered_content

init = 1
if len(sys.argv) > 1:
	init = int(sys.argv[1])

for iter in range(init, 100):
	url = 'http://reporeapers.github.io/results/' + str(iter) + '.html'
	req = requests.get(url)
	print('\n PAGE: ' + str(iter) + '\n')
	totalC = 0
	noneC = 0
	shortC = 0
	okayC = 0

	if req.status_code == requests.codes.ok:
		req = req.text

		urls = re.findall('(https://ap[\w_-]+(?:(?:\.[\w_-]+)+)[\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])', req)
		
		for item in urls:
			gitURL = item + '/contents/README.md'
			topicsURL = item + '/topics'
			req = requests.get(gitURL, auth=([USERNAME], [OAUTH TOKEN]))
			if req.status_code == requests.codes.ok:
				content = decode(req)
				content = regex(content)
				

				if len(content) > 250:
					okayC += 1
				else:
					shortC += 1
				totalC += 1

			else:
				noneC += 1
				totalC += 1
		print("Total: " + str(totalC))
		print("404: " + str(noneC))
		print("200: " + str(shortC + okayC))
		print("Short: " + str(shortC))
		print("Sufficient: " + str(okayC))
		
	else:
		print('Content was not found')