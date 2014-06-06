import requests
import nltk
from nltk.corpus import stopwords
from nltk.collocations import *
import urllib
import urlparse
from multiprocessing import Lock, Process, Queue, current_process

def unicode_escape(unistr):
    """
    Tidys up unicode entities into HTML friendly entities

    Takes a unicode string as an argument

    Returns a unicode string
    """
    import htmlentitydefs
    escaped = ""

    for char in unistr:
        if ord(char) in htmlentitydefs.codepoint2name:
            name = htmlentitydefs.codepoint2name.get(ord(char))
            entity = htmlentitydefs.name2codepoint.get(name)
            escaped +="&#" + str(entity)

        else:
            escaped += char

    return escaped

def find_anchors(page):
	ngrams = []

	try:
		r = requests.get(page)

		if r.status_code == 200:
			#cleaned page text
			raw = nltk.clean_html(r.text)
			raw = unicode_escape(raw)

			#tokenize and convert to text
			tokens = nltk.tokenize.RegexpTokenizer(r'\w+').tokenize(raw)
			text = nltk.Text(tokens)

			#bigrams collocations
			bigram_measures = nltk.collocations.BigramAssocMeasures()
			trigram_measures = nltk.collocations.TrigramAssocMeasures()

			finder = BigramCollocationFinder.from_words(text)
			finder.apply_freq_filter(2)

			ignored_words = stopwords.words('english')

			#apply client word filter
			finder.apply_word_filter(lambda w: len(w) < 3 or w.lower() in ignored_words or w.lower() == 'wolf' or w.lower() == 'badger')

			ngrams.append(finder.nbest(bigram_measures.pmi, 10))

			#trigram collocations
			finder = TrigramCollocationFinder.from_words(text)
			finder.apply_freq_filter(2)

			ignored_words = stopwords.words('english')

			#apply client word filter
			finder.apply_word_filter(lambda w: len(w) < 3 or w.lower() in ignored_words or w.lower() == 'wolf' or w.lower() == 'badger')

			ngrams.append(finder.nbest(trigram_measures.pmi, 10))
	except Exception, e:
		print e.message

	return ngrams

def edit_url(url,anchors):
	try:
		if anchors:
			string = '#{'

			bigrams = anchors[0]
			trigrams = anchors[1]

			ngrams = bigrams + trigrams

			rng = len(ngrams)
			for i in range(rng):
				string +=' '.join(ngrams[i])

				if i == rng - 1:
					string += '}'
				else:
					string += '|'

			return url.rstrip('\n') + string
		else:
			return url
	except Exception, e:
		print e.message


def worker(work_queue, done_queue):
	text_file = open("anchors.txt", "a")
	try:
		for url in iter(work_queue.get, 'STOP'):
			new_line = str(edit_url(url, find_anchors(url)))
			text_file.write(new_line)
	        done_queue.put("%s - %s was good" % (current_process().name, url))
	except Exception, e:
	   		done_queue.put("%s failed on %s with: %s" % (current_process().name, url, e.message))
	text_file.close()
	return True

def main():
	workers = 5
	work_queue = Queue()
	done_queue = Queue()

	processes = []

	with open("links.txt", "r") as ifile:
	    for line in ifile:
			work_queue.put(line)

	for w in xrange(workers):
		p = Process(target=worker, args=(work_queue, done_queue))
		p.start()
		processes.append(p)
		work_queue.put('STOP')

	for p in processes:
		p.join()

	done_queue.put('STOP')

	for status in iter(done_queue.get, 'STOP'):
		print status


if __name__ == '__main__':
    main()
