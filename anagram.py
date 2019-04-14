#!/usr/bin/python3

import sys


class AnagramFinder():

    def __init__(self, filename, minlength):
        self.words = []
        f = open(filename)
        for line in f:
            word = line.strip().lower()
            if len(word) >= minlength:
                self.words.append(word)
        f.close()
        self.words.sort()

    def find(self, letters, display=None):
        letters = list(letters.lower())
        letters = [l for l in letters if l in 'abcdefghijklmnopqrstuvwxyz']
        return self.search_wordlist(letters, 0, display)

    def search_wordlist(self, letters, start, display=None):
        result = []
        for i in range(start, len(self.words)):
            word = self.words[i]
            if display is not None:
                display(i + 1, len(self.words))
            found, letters_left = self.word_in_letters(word, letters)
            if found:
                if letters_left is not None and len(letters_left) == 0:
                    result.append([word])
                else:
                    next_find = self.search_wordlist(letters_left, i)
                    for n in next_find:
                        result.append([word] + n)
        return result

    def word_in_letters(self, word, letters):
        letters = letters.copy()
        for letter in word:
            if letter in letters:
                letters.remove(letter)
            else:
                return False, []
        return True, letters


def output(i, n):
    line = "{}%".format(round(i / n * 100, 3))
    sys.stdout.write('\r')
    sys.stdout.write(line)
    sys.stdout.write('\033[0K')
    sys.stdout.flush()


if __name__ == '__main__':
    words = ' '.join(sys.argv[1:])
    a = AnagramFinder('words.txt', 3)
    results = a.find(words, output)
    print()
    for result in results:
        print(' '.join(result))
