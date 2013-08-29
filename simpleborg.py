#!/usr/local/env python

from __future__ import with_statement

import	errno
import	os
import	random
import	re
import	traceback

import cProfile
import pstats

class SimpleBorg(object):
	# Stores all learned lines in (sentence_hash, {seen, sentence}) pairs.
	_LINES = {}
	# Store word information in (word, {seen, pointer_list}) pairs.
	_WORDS = {}
	# This is set to True after the lines file is read.
	_PARSED = False
	# Storing the settings in a dictionary allows them to be replaced by another
	# dictionary like storage system (eg. dict4ini, etc.)
	settings = {
		# Set to False if you don't want to add more lines to a file.
		'learn' : True,
		# File all the lines are stored in
		'file' : 'lines2.txt',
		# Ignore these words.
		'ignore' : ['!.', '?.', "'", ',', ';'],
		# A list of patterns for various emotes to look for.
		'emotes' : {
			'?.?':re.compile('([~!@#$%^&*no0](\.|_+)[~!@#$%^&*no0])'),
		},
		# Set to True to get a verbose explaination of what's going on
		'debug' : False
	}

	def __init__(self, settings=None):
		if settings:
			self.settings = settings

		# Precompile each regular expression.
		if 'emotes' in self.settings:
			for (key, expr) in self.settings['emotes'].items():
				self.settings['emotes'][key] = re.compile(expr)

	def debug(self, message):
		if self.settings['debug']:
			print(message)

	def _clean_sentence(self, sentence):
		'''_clean_sentence(str sentence) -> str'''
		sentence = sentence.lower()

		# Filter out newlines and cariage returns
		sentence = sentence.replace('\n', '')
		sentence = sentence.replace('\r', '')

		# Remove leading and trailing whitespace
		sentence = sentence.strip()

		sentence = sentence.replace(";", " ; ")
		sentence = sentence.replace("?", " ? ")
		sentence = sentence.replace("!", " ! ")
		sentence = sentence.replace(".", " . ")
		sentence = sentence.replace(",", " , ")
		sentence = sentence.replace("'", " ' ")
		sentence = sentence.replace(":", " : ")
		sentence = sentence.replace("*", " * ")

		# Find ! and ? and append full stops.
		sentence = sentence.replace(". ", ".. ")
		sentence = sentence.replace("? ", "?. ")
		sentence = sentence.replace("! ", "!. ")

		#And correct the '...'
		sentence = sentence.replace("..  ..  .. ", ".... ")

		# Splitting and recombining the sentence cleans up excess white space.
		# eg. 'bacon ,  eggs and toast ? '
		sentence = ' '.join(sentence.split())

		# Tack on a trailing space so it can split for '. '
		return '%s ' % sentence

	def _is_emote(self, word):
		pass

	def _fix_sentence(self, sentence):
		'''_fix_sentence(str sentence) -> str

		Attempt to fix some formatting errors required to build the sentences.
		eg. "you ' re" and "bacon ?"

		'''

		sentence = sentence.replace(" ?", "?")
		sentence = sentence.replace(" !", "!")
		sentence = sentence.replace(" .", ".")
		sentence = sentence.replace(" ;", ";")
		sentence = sentence.replace(" ,", ",")
		sentence = sentence.replace(" ' ", "'")
		sentence = sentence.replace(" :", ":")
		sentence = sentence.replace(" *", "*")

		return sentence

	def read_lines(self):
		print("Reading Lines File (%s)..." % self.settings['file'])
		try:
			f = open(self.settings['file'], 'r')
			lines = f.readlines()
			f.close()
		except IOError as e:
			if e.errno == errno.ENOENT:
				print(os.strerror(e.errno))
				print("Creating blank file (%s)" % self.settings['file'])
				f = open(self.settings['file'], 'w+')
				lines = f.readlines()
				f.close()
			else:
				traceback.print_exc()

		print("Learning (%s)..." % self.settings['file'])
		for line in lines:
			self.learn(line)

		print("done.")
		print("I know %d lines!" % len(self._LINES))
		self._PARSED = True

	def save_lines(self):
		if self.settings['learn']:
			print("Writing Lines to File...")
			f = open(self.settings['file'], 'w')
			for line in self._LINES.values():
				for x in range(line['seen']):
					f.write('%s\n' % self._fix_sentence(line['sentence']))
			f.close()
			print('done.')

	def learn(self, line):
		'''learn(str line) -> None

		Manages all the overhead for learning a line.
		This passes ready sentence to _learn, meaning it's clean and properly split.

		'''
		line = self._clean_sentence(line)
		for sentence in line.split('. '):
			self._learn(sentence)

	def _learn(self, sentence):
		'''_learn(str sentence) -> None

		Learn a sentence, creating [sentence_hash, position] pointers for each word.

		'''

		# If learning is disabled then wait until we've learned our saved lines.
		if self._PARSED and not self.settings['learn']:
			return

		# There is a 1 in 2^32 chance of a collision.
		sentence_hash = hash(sentence)

		if not sentence or sentence_hash in self._LINES:
			return

		# Loads self._WORDS into the local scope for faster acessing
		self._WORDS = self._WORDS
		#words = re.sub('[^a-zA-Z_0-9 ]', '', sentence.lower())
		words = sentence.split()

		# Ignore sentences with only one word.
		if len(words) <= 1:
			return

		for i in range(len(words)):
			word = words[i]

			# Make sure each word has a dictionary
			if word not in self._WORDS:
				self._WORDS[word] = {'seen':0, 'pointers':[]}

			# Record the number of times a word is seen.
			self._WORDS[word]['seen'] += 1

			#Record the sentence 'word' is used in and it's position.
			self._WORDS[word]['pointers'].append([sentence_hash, i])

		if sentence_hash not in self._LINES:
			self._LINES[sentence_hash] = {'sentence':sentence, 'seen':0}

		self._LINES[sentence_hash]['seen'] += 1
		if self._PARSED:
			 self.debug('Learning: %s' % sentence)


	def build_reply(self, input_):
		reply = ''
		input_ = self._clean_sentence(input_)

		word_list = self._filter_split(input_)

		# Retrun the least seen known word in the sentence.
		leftword = self._choose_word(word_list)

		# If we don't know any of the words return a random sentence.
		if not leftword:
			return self._finalize_reply('')#random.choice(self._LINES.values() or [{'sentence':''}])['sentence'])

		self.debug("Left Word: %s" % leftword)

		# Build the sentence backwards starting from 'leftword'
		leftside = self._build_left([leftword])

		self.debug("Left Side: %s" % ' '.join(leftside))

		# FIXME: We want -both- sides, we also don't want the progrma to crash ;]
		#return _finalize_reply(leftside)

		rightside = self._build_right(leftside[-2:])

		self.debug("Right Side: %s" % ' '.join(rightside))
		reply = ' '.join(leftside[:-2] + rightside)
		return self._finalize_reply(reply)

	def _filter_split(self, sentences):
		'''_filter_split(str sentences) -> list'''
		# Combine any sentences into a single word list.
		word_list = []
		for sentence in sentences.split('. '):
			word_list.extend(sentence.split())

		word_list = [word for word in word_list if word in self._WORDS
					 and word not in self.settings['ignore'] and not word.isdigit()]

		return word_list


	def _choose_word(self, word_list):
		'''_choose_word(list word_list) -> str'''
		self._WORDS = self._WORDS
		# Build a list of the words we've seen as close to 'at_least'
		# as possible.
		choices = ['']
		# We need to have seen a word at least 3 times to consider it.
		at_least = 3
		at_most = 0
		for word in word_list:
			if word not in self._WORDS:
				continue

			seen = self._WORDS[word]['seen']
			# If we find matching seen numbers. Append to the list.
			if seen == at_most: #and word not in choices:
				choices.append(word)
			# Look for words that we've seen less than 'at_most' and
			# more than 'at_least'
			elif (not at_most or seen < at_most) and seen >= at_least:
				# If we find one start the seach over
				choices = [word]
				# And lower the threshold
				at_most = seen

		# Return a random word from the list
		return random.choice(choices)

	def _decide_on_word(self, sorted_words, reply_list):
		# Build a list of number's we'll use to get a word
		# This system gives words we've seen less a higher chance of getting picked.

		# We start off the first word and build from there.
		chances = [sorted_words[0][1]]
		for x in range(1, len(sorted_words)):
			# Each new item is the number of times 'x' word has been seen
			# added to the number of times the word before it has been seen.
			chances.append(sorted_words[x][1] + chances[x - 1])

		# A custom random.choice
		# Get a random number within the total range.
		# This number limits the choices considerably because more frequent
		# words are given a smaller number.
		chosen = random.randint(0, chances[-1])
		for x in range(0, len(chances)):
			if chances[x] >= chosen:
				# Set 'chosen' to be the corisponding word.
				#chosen = sorted_words[x][1]
				chosen_word = sorted_words[x][0]
				# We don't want duplicate words, so toss out words we've
				# previously chosen.
				if chosen_word in reply_list:
					continue

				# If we find a usable word then break.
				break

		while chosen_word in reply_list:
			x += 1
			if x >= len(sorted_words):
				chosen_word = ''
				break
			chosen_word = sorted_words[x][0]

		#if not chosen_word:
			# If we don't find a word then we're done with the left side.
		#	return []

		# Split the word, to account for words like 'you '' which pop up.
		# Append 'chosen' to the front of the list.
		# This leaves the original word in the center of the sentence.
		chosen_word = chosen_word.split()
		return chosen_word

	def _build_left(self, reply_list):
		'''_build_left(list reply_list) -> list

		Build the left side of the sentence from the center out word by word.

		'''
		assert isinstance(reply_list, list)

		word = reply_list[0]
		left_side = {'':0}
		# Build a list of how many times we've seen 'word' paired with the word
		# before it, or just seen in general if it's the only word.
		for (sentence, pos) in self._WORDS[word]['pointers']:
			sample_words = self._LINES[sentence]['sentence'].split()
			# Words in sentences we've seen more get higher chance to be picked.
			seen = self._LINES[sentence]['seen']
			# Ignore the sentence if the sentence begins with 'word'
			if not pos:
				left_side[''] += seen
				continue

			# TODO: Explain the logic here
			if len(reply_list) > 1 and len(sample_words) > (pos + 1):
				# Skip sentences
				if reply_list[1] != sample_words[pos + 1]:
					continue

			next_word = sample_words[pos - 1]
			if next_word in self.settings['ignore'] and pos > 1:
				next_word = '%s %s' % (sample_words[pos - 2], next_word)


			left_side[next_word] = left_side.get(next_word, 0) + seen
			#if not left_side.has_key(next_word):
			#	left_side[next_word] = seen
			#else:
			#	left_side[next_word] += seen

		# Sort the words accending based on how often they're seen.
		sorted_words = list(left_side.items())
		sorted_words.sort(key=lambda x: x[1], reverse=True)

		chosen_word = self._decide_on_word(sorted_words, reply_list)
		if not chosen_word:
			return reply_list

		chosen_word.reverse()
		for part in chosen_word:
			reply_list.insert(0, part)
		return self._build_left(reply_list)

	def _build_right(self, reply_list):
		'''_build_right(list reply_list) -> list

		Build the right side of the sentence from the center out word by word.

		'''
		assert isinstance(reply_list, list)

		word = reply_list[-1]
		right_side = {'':0}
		# Build a list of how many times we've seen 'word' paired with the word
		# before it, or just seen in general if it's the only word.
		for (sentence, pos) in self._WORDS[word]['pointers']:
			sample_words = self._LINES[sentence]['sentence'].split()
			# Words in sentences we've seen more get higher chance to be picked.
			seen = self._LINES[sentence]['seen']

			# TODO: Explain the logic here
			if len(reply_list) > 1:
				# Skip sentences
				if reply_list[-2] != sample_words[pos - 1]:
					continue

			# Ignore the sentence if the sentence ends with 'word'
			if pos >= (len(sample_words) - 1):
				right_side[''] += 1
				continue


			# Look ahead for the next word
			next_word = sample_words[pos + 1]
			if next_word in self.settings['ignore'] and pos < (len(sample_words) - 2):
				next_word = '%s %s' % (next_word, sample_words[pos + 2])

			right_side[next_word] = right_side.get(next_word, 0) + seen
			#if not right_side.has_key(next_word):
			#	right_side[next_word] = seen
			#else:
			#	right_side[next_word] += seen

		# Sort the words deccending based on how often they're seen.
		sorted_words = list(right_side.items())
		sorted_words.sort(key=lambda x: x[1], reverse=True)

		chosen_word = self._decide_on_word(sorted_words, reply_list)
		if not chosen_word:
			return reply_list

		for part in chosen_word:
			reply_list.append(part)
		return self._build_right(reply_list)

	def _finalize_reply(self, reply):
		return self._fix_sentence(reply)

def main(*args):
	queen = SimpleBorg()
	queen.read_lines()
	input_ = input('> ')
	while input_ and input_ != 'quit':
		reply = "%s" % queen.build_reply(input_)
		queen.learn(input_)
		print(reply)
		input_ = input('> ')

	queen.save_lines()

def profile():
	queen = SimpleBorg()
	queen.read_lines()
	queen.settings['learn'] = False
	input_ = [
		'Good morning',
		'How are you?',
		'My name is Patrick, what is yours?',
		'Do you enjoy bacon?',
		'I\'m going to ask you random questions, is this ok?',
		'First off, how do you feel about life?',
		'How do you feel about Patrick?',
		'How does it makes you feel that youre being tested on?',
		'That\'s good.'
		'Welp, good bye'
	]
	for x in range(1000):
		for line in input_:
			queen.build_reply(line)
			queen.learn(line)

if __name__ == "__main__":
	if False:
		cProfile.run('profile()', 'simpleborg-results.prof')
		with open('simpleborg-results.txt', 'wb+') as f:
			stats = pstats.Stats('simpleborg-results.prof', stream=f)
			stats.strip_dirs()
			#stats.sort_stats('calls')
			stats.print_stats()
		print('DONE!')
	main()
