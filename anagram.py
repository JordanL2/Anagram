#!/usr/bin/python3

import sys


class AnagramFinder():

    def __init__(self, filename):
        self.allowed_letters = 'abcdefghijklmnopqrstuvwxyz'

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

        # For each word, makes a list of each letter in the word and the
        # number of times it occurs
        self.word_letter_map = {}
        for word in self.words:
            self.word_letter_map[word] = self.word_to_letter_map(word)

    def find(self, letters, display=None):
        letters = list(letters.lower())
        letters = [l for l in letters if l in self.allowed_letters]
        return self.search_wordlist(self.word_to_letter_map(letters), 0, display)

    def search_wordlist(self, letter_map, start, display=None):
        l = self.letter_map_count(letter_map)
        if l < self.shortest_word_length:
            return []
        if l in self.word_length_index:
            if self.word_length_index[l] > start:
                start = self.word_length_index[l]

        result = []

        for i in range(start, self.word_count):
            word = self.words[i]
            if display is not None:
                display(i + 1, self.word_count)
            found, letters_left = self.word_in_letters(word, letter_map)
            if found:
                if self.letter_map_count(letters_left) == 0:
                    result.append([word])
                else:
                    next_find = self.search_wordlist(letters_left, i)
                    for n in next_find:
                        result.append([word] + n)

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


def output(i, n):
    line = "{}%".format(round(i / n * 100, 3))
    sys.stdout.write('\r')
    sys.stdout.write(line)
    sys.stdout.write('\033[0K')
    sys.stdout.flush()


if __name__ == '__main__':
    words = ''.join(sys.argv[1:])
    a = AnagramFinder('words.txt')
    results = a.find(words, output)
    print()
    for result in results:
        print(' '.join(result))
