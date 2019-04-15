#!/usr/bin/python3

import sys
import multiprocessing


class AnagramFinder():

    def __init__(self, filename):
        self.allowed_letters = 'abcdefghijklmnopqrstuvwxyz'

        self.thread_count = 10
        multiprocessing.set_start_method('fork')

        self.words = []
        letter_frequency = {}
        f = open(filename)
        for line in f:
            word = line.strip()
            self.words.append(word)
            for letter in word:
                if letter not in letter_frequency:
                    letter_frequency[letter] = 0
                letter_frequency[letter] += 1
        f.close()
        self.words.sort(key=len, reverse=True)
        self.word_count = len(self.words)

        # Index of wordlist by length, so when we only have eg 5 letters,
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

        # Start the threads
        max_t = self.thread_count
        threads = []
        queue = multiprocessing.Queue()
        for t in range(0, max_t):
            thread = multiprocessing.Process(
                target=self.do_thread, 
                args=(queue, letter_map, t, max_t, display), 
                daemon=True)
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()

        # Combine and return the results
        result = []
        while not queue.empty():
            result.extend(queue.get())
        return result

    def do_thread(self, queue, letter_map, t, max_t, display):
        result = self.search_wordlist(letter_map, t, max_t, t, display)
        queue.put(result)

    def search_wordlist(self, letter_map, t, max_t, start, display=None):
        l = self.letter_map_count(letter_map)
        if l < self.shortest_word_length:
            return []
        if l in self.word_length_index:
            if self.word_length_index[l] > start:
                rem = start % max_t
                start = self.word_length_index[l]
                start_rem = start % max_t
                rem_diff = start_rem - rem
                start -= rem_diff

        result = []

        for i in range(start, self.word_count, max_t):
            word = self.words[i]
            if display is not None:
                display(t, i + 1, self.word_count)
            found, letters_left = self.word_in_letters(word, letter_map)
            if found:
                if self.letter_map_count(letters_left) == 0:
                    result.append([word])
                else:
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
    sys.stdout.write(line)
    sys.stdout.flush()


if __name__ == '__main__':
    words = ''.join(sys.argv[1:])
    a = AnagramFinder('words.txt')
    results = a.find(words, output)
    print()
    for result in results:
        print(' '.join(result))
