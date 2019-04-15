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

        # Mapping for each word to an ordered version of it, with least common letters
        # first, to optimise the word/letter comparison - more likely to fail earlier
        self.words_ordered = {}
        for word in self.words:
            ordered_word = list(word)
            ordered_word.sort(key=lambda x: letter_frequency[x])
            self.words_ordered[word] = ''.join(ordered_word)

    def find(self, letters, display=None):
        letters = list(letters.lower())
        letters = [l for l in letters if l in self.allowed_letters]
        return self.search_wordlist(letters, 0, display)

    def search_wordlist(self, letters, start, display=None):
        l = len(letters)
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
            found, letters_left = self.word_in_letters(word, letters)
            if found:
                if len(letters_left) == 0:
                    result.append([word])
                else:
                    next_find = self.search_wordlist(letters_left, i)
                    for n in next_find:
                        result.append([word] + n)

        return result

    def word_in_letters(self, word, letters):
        letters = letters.copy()
        for letter in self.words_ordered[word]:
            if letter in letters:
                letters.remove(letter)
            else:
                return False, None
        return True, letters


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
