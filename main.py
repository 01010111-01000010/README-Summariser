#!/usr/bin/env python3
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

'''
contentPrint(bool, URL)
bool: if true, summarise repo content
URL: repo URL string

Collects repo content from the URL & processes it

Returns processed content or an error message if it is not found
'''
def contentPrint(bool, URL):
	req = requests.get(URL, auth=([USERNAME], [OAUTHTOKEN]))

	if req.status_code == requests.codes.ok:
		content = decode(req)
		content = regex(content)
		if bool == True:
			content = summarize(content, words=50)
		return content

	else:
		print('Content was not found')
		return ""

'''
topicsPrint(filtered_content)
filtered_content: pre-processed repo README

The GitHub provided topics for a repo are ranked and a single topic to represent the repo is chosen.
If a topic isn't found the repo header paragraph is processed to find a topic.
In the event a topic is still not determined, the user is asked to provide one.
An error string is provided if the requests are not fulfilled.

Returns the string of the highest ranked topic or an error string
'''
def topicsPrint(filtered_content):
	headers = {'Accept':'application/vnd.github.mercy-preview+json', 'Authorization': [USERNAME]}
	req = requests.get(topicsURL, headers = headers)
	if req.status_code == requests.codes.ok:
		req = req.json()
		content = req['names']

		if len(content) == 0:
			print("Unable to tag")
			currContent = ""
			
			while currContent != "exit":
				currContent = input("Enter a topic for this repo or 'exit' to submit current suggestions: ")
				content.append(currContent)
			content.remove("exit")

			scores = {}

			for x in range(len(content)):
				scores[content[x]] = textdistance.ratcliff_obershelp(filtered_content, content[x])

			print(scores)

			return(max(scores.items(), key=operator.itemgetter(1))[0])

		else:
			scores = {}

			for x in range(len(content)):
				scores[content[x]] = textdistance.ratcliff_obershelp(filtered_content, content[x])


			return(max(scores.items(), key=operator.itemgetter(1))[0])

	else:
		print('Content was not found')
		content = []

		currContent = ""

		while currContent != "exit":
			currContent = input("Enter a topic for this repo or 'exit' to submit current suggestions: ")
			content.append(currContent)
		content.remove("exit")

		scores = {}

		for x in range(len(content)):
			scores[content[x]] = textdistance.ratcliff_obershelp(filtered_content, content[x])

		print(scores)

		return(max(scores.items(), key=operator.itemgetter(1))[0])

'''
topicReq(req)
req: request object for associated topic query

The function regexes the request of a GitHub topic search query & finds up to 5 repos that GitHub first recommend

Returns a string array of API URL's of up to 5 in length or a None if no search results are found

Could be merged with searchReq with a more succinct solution to the spider
'''
def topicReq(req):
	similar = {}
	if req.status_code == requests.codes.ok:
		content = req.content.decode("utf-8")
		content = content.replace('\n', ' ').replace('\r', ' ')
		content = re.findall('<a         href="(.{1,35})"         data-ga-click="Explore, go to repository,', content)#'<a href="/ldionne/dyno"', content) #Regex repo list
		i = 0
		for x in content:
			similar[i] = contentPrint(True, f'https://api.github.com/repos{x}/contents/README.md')
			i += 1
			if i == 5:
				return similar
		return similar
	return None

'''
searchReq(req)
req: request object for associated search query

The function regexes the request of a GitHub search query & finds up to 5 repos that GitHub first recommend

Returns a string array of API URL's of up to 5 in length or a None if no search results are found

Could be merged with topicReq with a more succinct solution to the spider
'''
def searchReq(req):
	similar = {}
	if req.status_code == requests.codes.ok:
		content = req.content.decode("utf-8")
		content = content.replace('\n', ' ').replace('\r', ' ')
		content = re.search('<ul class="repo-list">(.*)</ul>', content) #Regex repo list
		content = content.group(0)
		content = re.findall('&quot;url&quot;:&quot;(.{150})', content) #Pull repo URL's alongside extra tokens to prevent Regex-ing unwanted sections
		i = 0
		for x in content:
			x = x.replace('&', ' ')
			x = re.search('http\S+', x)
			x = x.group(0) #Regex URL from shortened strings
			x = re.sub(r'https://github.com', '', x) # remove initial link
			similar[i] = contentPrint(True, f'https://api.github.com/repos{x}/contents/README.md')
			i += 1
			if i == 5:
				return similar
		return similar
	return None

'''
findSimilar(query)
query: search/topic string used in identifying "similar" repos

The function takes the argument string & checks GitHub for a matching topic in their topic list.
If it is unable to find a topic, it will then use the string as a search term as a backup.
If it is still unable to find any repos as part of the search it will return an error string

Returns an array of repos (in order of prevalence) of the topic, search term, or an error string
'''
def findSimilar(query):
	query = re.sub(r' ', '%20', query)
	req = requests.get(f'https://github.com/topics/{query}')
	req = topicReq(req)
	if req == None or req == {}:
		req = requests.get(f'https://github.com/search?q={query}')
		req = searchReq(req)
		if req == None or req == {}:
			return {"Error, unable to find repos with this topic"}
		return req
	return req

'''
decode(req)
req: GitHub API request object

De-JSON's the request object & extracts the string contents

Returns a string of the webpage content
'''
def decode(req):
	req = req.json()
	content = base64.b64decode(req['content'])
	content = str(content, "utf-8")

	content = content.lower()
	return content

'''
regex(content)
content: string of text content

Performs a series of regex queries to reduce a body of text

Returns the input string minus all the regex terms
'''
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

'''
MAIN
'''
selection = input("Please enter the GitHub repo URL:")
selection = selection.split('/')

present = False
for i, token in enumerate(selection):
	if 'github.com' in token:
		present = True
		loc = i

if not present:
	print("Error: Valid GitHub URL not provided")
	exit()
else:
	user = selection[loc+1]
	repo = selection[loc+2]

repoURL = f'https://api.github.com/repos/{user}/{repo}/contents/README.md'
topicsURL = f'https://api.github.com/repos/{user}/{repo}/topics'

f = open("summa.txt","w+")
fList = {}

'''
Find first 4 regex'ed sentences of repo
'''
sentenceSummary = contentPrint(False, repoURL)
sentenceSummary = sent_tokenize(sentenceSummary)
sentenceSummary = " ".join(sentenceSummary[:4])
sentenceSummary = ''.join([char if ord(char) < 128 else '' for char in sentenceSummary])
fList[0] = "=SENTENC=\n" + sentenceSummary + "\n========="


'''
Find single README summary
'''
READMESummary = contentPrint(True, repoURL)
READMESummary = ''.join([char if ord(char) < 128 else '' for char in READMESummary])
fList[1] = "=README!=\n" + READMESummary + "\n========="

'''
Find similar repo summary
'''
query = topicsPrint(READMESummary)
similarReposList = findSimilar(query)
similarRepoSummary = ""
print(similarReposList)
for i in similarReposList:
	similarRepoSummary += similarReposList[i]
similarRepoSummary = ''.join([char if ord(char) < 128 else '' for char in similarRepoSummary])
similarRepoSummary = summarize(similarRepoSummary, words=50)
fList[2] = "=SIMILAR=\n" + similarRepoSummary + "\n========="

'''
Input user summary
'''
userSummary = ""
index = ""
while index != "END":
	index = input("Enter your summary: (type 'END' to terminate input)\n")
	userSummary += index + '\n'
userSummary = re.sub(r'END', '', userSummary)
print(userSummary)
fList[3] = "=SUBMITD=\n" + userSummary + "========="

'''
Shuffle list & write to file
'''
shuffle(fList)
for i in fList:
	f.write(fList[i] + '\n')

# I will then copy the file & regex out the identifying titles to present while keeping a master copy for scoring