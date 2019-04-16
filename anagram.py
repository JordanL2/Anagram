#!/usr/bin/python3

import sys
import multiprocessing
from queue import Empty


class AnagramFinder():

    def __init__(self, filename):
        self.allowed_letters = 'abcdefghijklmnopqrstuvwxyz'

        self.thread_count = 10
        multiprocessing.set_start_method('fork')

        # Load dictionary of words
        self.words = []
        f = open(filename)
        for line in f:
            word = line.strip()
            if len([l for l in word if l not in self.allowed_letters]) > 0:
                raise Exception("Invalid word in dictionary: '{}'".format(word))
            self.words.append(word)
        f.close()
        self.word_count = len(self.words)

        # Sort the word list by word length, longest words first
        self.words.sort(key=len, reverse=True)

        # Index of word list by length, so when we only have eg 5 letters,
        # we can jump to the part of the list with words of that length
        self.word_length_index = {}
        for i, word in enumerate(self.words):
            l = len(word)
            if l not in self.word_length_index:
                self.word_length_index[l] = i
                self.shortest_word_length = l

        # For each word, makes a mapping of each letter in the word and the
        # number of times it occurs
        self.word_letter_map = {}
        for word in self.words:
            self.word_letter_map[word] = self.word_to_letter_map(word)

    def find(self, letters, display=None):
        # Make all letters lowercase and filter out characters that aren't allowed
        letters = letters.lower()
        letters = [l for l in letters if l in self.allowed_letters]
        # Turn string into a map of each letter and the number of times it occurs
        letter_map = self.word_to_letter_map(letters)

        args = [[letter_map, display]] * self.thread_count
        return self.multithreaded_job(self.do_thread, args)

    def multithreaded_job(self, target, args):
        # Start a thread for each set of arguments
        max_t = len(args)
        threads = []
        queue = multiprocessing.Queue()
        for t in range(0, max_t):
            thread = multiprocessing.Process(
                target=target,
                args=[t, max_t, queue] + args[t],
                daemon=True)
            thread.start()
            threads.append(thread)

        # Read results from threads while waiting for them to finish
        result = []
        for thread in threads:
            while thread.is_alive():
                while True:
                    try:
                        r = queue.get(block=False)
                        result.append(r)
                    except Empty:
                        break

        # Add the last of the queue to the results, and return them
        while not queue.empty():
            result.append(queue.get())
        return result

    def do_thread(self, t, max_t, queue, letter_map, display):
        result = self.search_wordlist(letter_map, t, max_t, t, display)
        for r in result:
            queue.put(r)

    def search_wordlist(self, letter_map, t, max_t, start, display=None):
        # Get total number of letters we're searching
        l = self.letter_map_count(letter_map)
        if l < self.shortest_word_length:
            # If the number of letters is shorter than the shortest
            # word, we can stop immediately
            return []
        # If possible, we can jump to the part of the word list with
        # the words that have the number of letters that we're searching
        if l in self.word_length_index:
            if self.word_length_index[l] > start:
                rem = start % max_t
                start = self.word_length_index[l]
                start_rem = start % max_t
                rem_diff = rem - start_rem
                start += rem_diff

        result = []

        for i in range(start, self.word_count, max_t):
            word = self.words[i]
            if display is not None:
                display(t, i + 1, self.word_count)
            # See if this word can be found in the letters we're searching,
            # and if so, what letters are left over afterwards
            found, letters_left = self.word_in_letters(word, letter_map)
            if found:
                if self.letter_map_count(letters_left) == 0:
                    # There are no remaining letters, so we have a result
                    result.append([word])
                else:
                    # There are remaining letters, so we have to see what words
                    # can be found in them, combining the results with this word
                    next_find = self.search_wordlist(letters_left, 0, 1, i)
                    for n in next_find:
                        result.append([word] + n)

        if display is not None:
            display(t, self.word_count, self.word_count)
        return result

    def word_in_letters(self, word, letter_map):
        this_word_letter_map = self.word_letter_map[word]
        for letter in this_word_letter_map.keys():
            if letter not in letter_map or this_word_letter_map[letter] > letter_map[letter]:
                return False, None
        letters_left = letter_map.copy()
        for letter in this_word_letter_map.keys():
            letters_left[letter] -= this_word_letter_map[letter]
        return True, letters_left

    def word_to_letter_map(self, word):
        letter_map = {}
        for letter in word:
            if letter not in letter_map:
                letter_map[letter] = 0
            letter_map[letter] += 1
        return letter_map

    def letter_map_count(self, letter_map):
        return sum(letter_map.values())


def output(t, i, n):
    line = '\r'
    if t > 0:
        line += ('\033[' + str(t * 8) + 'C')
    line += "{:6.2f}%".format(i / n * 100)
    sys.stderr.write(line)
    sys.stderr.flush()


if __name__ == '__main__':
    words = ''.join(sys.argv[1:])
    a = AnagramFinder('words.txt')
    results = a.find(words, output)
    sys.stderr.write("\n")
    sys.stderr.flush()
    for result in results:
        print(' '.join(result))
