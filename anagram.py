#!/usr/bin/python3

import sys
import multiprocessing
from queue import Empty
from time import sleep


class AnagramFinder():

    def __init__(self, filename):
        self.allowed_letters = 'abcdefghijklmnopqrstuvwxyz'

        self.proc_count = 1

        self.caching_enabled = False
        self.cache_limit = 1000000
        self.cache_clear_fraction = 0.1

        self.fast_path_enabled = True
        self.fast_path_cutoff = 0.1

        # Load dictionary of words
        self.words = []
        f = open(filename)
        for line in f:
            word = line.strip()
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
        # Mapping of word sorted alphabetically to the word
        self.word_normalised_map = {}
        # Mapping of word to its index
        self.word_reversed_index = {}
        for i, word in enumerate(self.words):
            self.word_letter_map[word] = self.word_to_letter_map(word)
            key = self.normalise_word(word)
            if self.fast_path_enabled:
                if key not in self.word_normalised_map:
                    self.word_normalised_map[key] = []
                self.word_normalised_map[key].append(word)
                self.word_reversed_index[word] = i

    def find(self, letters, display=None):
        # Turn string into a map of each letter and the number of times it occurs
        letter_map = self.word_to_letter_map(letters)

        args = [[letter_map, display]] * self.proc_count
        results = self.multiprocess_job(self.do_proc, args)
        return self.sort_results(results)

    def multiprocess_job(self, target, args):
        # Start a process for each set of arguments
        max_t = len(args)
        procs = []
        queue = multiprocessing.Queue()
        for t in range(0, max_t):
            proc = multiprocessing.Process(
                target=target,
                args=[t, max_t, queue] + args[t],
                daemon=True)
            proc.start()
            procs.append(proc)

        # Read results from processes while waiting for them to finish
        results = []
        for proc in procs:
            while proc.is_alive():
                sleep(0.001)
                while True:
                    try:
                        r = queue.get(block=False)
                        results.append(r)
                    except Empty:
                        break

        # Add the last of the queue to the results, and return them
        while not queue.empty():
            results.append(queue.get())
        return results

    def do_proc(self, t, max_t, queue, letter_map, display):
        self.result_cache = {}
        results = self.search_wordlist(letter_map, t, max_t, t, True, display)
        for result in results:
            queue.put(result)

    def search_wordlist(self, letter_map, t, max_t, start, toplevel, display=None):
        key = self.letter_map_to_key(letter_map)
        cache_stop = None
        if self.caching_enabled and key in self.result_cache:
            self.result_cache[key][2] += 1
            if self.result_cache[key][1] <= start:
                return self.results_as_list(self.result_cache[key][0], start)
            else:
                cache_stop = self.result_cache[key][1]

        # Get total number of letters we're searching
        letter_count = self.letter_map_count(letter_map)
        if letter_count < self.shortest_word_length:
            # If the number of letters is shorter than the shortest
            # word, we can stop immediately
            return []

        # If possible, we can jump to the part of the word list with
        # the words that have the number of letters that we're searching
        if letter_count in self.word_length_index:
            if self.word_length_index[letter_count] > start:
                rem = start % max_t
                start = self.word_length_index[letter_count]
                start_rem = start % max_t
                rem_diff = rem - start_rem
                start += rem_diff

        results = []

        # If we have a small number of letters, it's faster to iterate through every possible
        # combination of letters and see if it's an anagram of any words
        letter_index_count = 1
        for c in letter_map.values():
            letter_index_count *= (c + 1)
        if not toplevel and self.fast_path_enabled and letter_index_count < (self.word_count - start) * self.fast_path_cutoff and cache_stop is None:

            # Mapping of index to letter
            index_to_letter = [l for l in sorted(letter_map.keys())]
            # Mapping of index to count of that letter
            letter_max = [letter_map[l] for l in sorted(letter_map.keys())]
            # Index as we step through every combination of letters
            letter_index = [0] * len(letter_map.keys())
            stop = False
            while not stop:
                
                # Increment index
                letter_index[-1] += 1
                for i in range(len(letter_index) - 1, -1, -1):
                    if letter_index[i] > letter_max[i]:
                        if i == 0:
                            stop = True
                            break
                        letter_index[i] = 0
                        letter_index[i - 1] += 1

                if not stop:
                    letters = ''.join([index_to_letter[i] * letter_index[i] for i in range(0, len(letter_index))])

                    if letters in self.word_normalised_map:
                        words = [w for w in self.word_normalised_map[letters] if self.word_reversed_index[w] >= start]
                        if len(words) > 0:
                            # Calcuate what letters are left over
                            letters_left = letter_map.copy()
                            for i in range(0, len(letter_index)):
                                l = index_to_letter[i]
                                letters_left[l] -= letter_index[i]
                                if letters_left[l] == 0:
                                    del letters_left[l]
                            letters_left_count = self.letter_map_count(letters_left)

                            # Store these results
                            for word in words:
                                wordi = self.word_reversed_index[word]
                                if letters_left_count == 0:
                                    self.add_to_results(results, wordi, word)
                                else:
                                    next_find = self.search_wordlist(letters_left, 0, 1, wordi, False)
                                    for n in next_find:
                                        self.add_to_results(results, wordi, word + ' ' + n)

        else:

            # Otherwise, we iterate through all the words and see if they can be made
            # using the letters we have

            for wordi in range(start, self.word_count, max_t):
                if self.caching_enabled and cache_stop is not None and wordi >= cache_stop and key in self.result_cache:
                    self.merge_results(results, self.result_cache[key][0])
                    break
                word = self.words[wordi]
                if toplevel and display is not None:
                    display(t, wordi + 1, self.word_count)
                # See if this word can be found in the letters we're searching,
                # and if so, what letters are left over afterwards
                found, letters_left = self.word_in_letters(word, letter_map)
                if found:
                    if self.letter_map_count(letters_left) == 0:
                        # There are no remaining letters, so we have a result
                        self.add_to_results(results, wordi, word)
                    else:
                        # There are remaining letters, so we have to see what words
                        # can be found in them, combining the results with this word
                        next_find = self.search_wordlist(letters_left, 0, 1, wordi, False)
                        for n in next_find:
                            self.add_to_results(results, wordi, word + ' ' + n)
                if toplevel and self.caching_enabled:
                    self.clear_cache()

        if toplevel and display is not None:
            display(t, self.word_count, self.word_count)
        
        if not toplevel and self.caching_enabled:
            if key not in self.result_cache:
                self.result_cache[key] = [results, start, 0]
            elif self.result_cache[key][1] > start:
                self.result_cache[key] = [results, start, self.result_cache[key][2] + 1]

        return self.results_as_list(results)

    def add_to_results(self, results, i, result):
        results.append((i, result))

    def merge_results(self, results1, results2):
        results1.extend(results2)

    def results_as_list(self, results, start=0):
        return [r[1] for r in results if r[0] >= start]

    def get_cache_size(self):
        return len(self.result_cache)

    def clear_cache(self):
        cache_size = self.get_cache_size()
        if cache_size > self.cache_limit:
            amount_to_remove = (cache_size - self.cache_limit) + (self.cache_limit * self.cache_clear_fraction)
            cache_usage = {}
            for c in self.result_cache.values():
                n = c[2]
                if n not in cache_usage:
                    cache_usage[n] = 0
                cache_usage[n] += 1
            total_n = 0
            remove_used = []
            for used in sorted(cache_usage.keys()):
                n = cache_usage[used]
                remove_used.append(used)
                total_n += n
                if total_n >= amount_to_remove:
                    break
            self.result_cache = dict([(k, v) for k, v in self.result_cache.items() if v[2] not in remove_used])

    def word_in_letters(self, word, letter_map):
        this_word_letter_map = self.word_letter_map[word]
        for letter in this_word_letter_map.keys():
            if letter not in letter_map or this_word_letter_map[letter] > letter_map[letter]:
                return False, None
        letters_left = letter_map.copy()
        for letter in this_word_letter_map.keys():
            letters_left[letter] -= this_word_letter_map[letter]
            if letters_left[letter] == 0:
                del letters_left[letter]
        return True, letters_left

    def word_to_letter_map(self, word):
        letter_map = {}
        for letter in word:
            letter = letter.lower()
            if letter in self.allowed_letters:
                if letter not in letter_map:
                    letter_map[letter] = 0
                letter_map[letter] += 1
        return letter_map

    def letter_map_count(self, letter_map):
        return sum(letter_map.values())

    def letter_map_to_key(self, letter_map):
        return ''.join([l * n for l, n in sorted(letter_map.items())])

    def normalise_word(self, word):
        return self.letter_map_to_key(self.word_to_letter_map(word))

    def sort_results(self, results):
        new_result = set()
        for result in results:
            new_result.add(' '.join(sorted(result.split(' '))))
        return sorted(list(new_result))


def output(t, i, n):
    line = '\r'
    if t > 0:
        line += ('\033[' + str(t * 8) + 'C')
    line += "{:6.2f}%".format(i / n * 100)
    sys.stderr.write(line)
    sys.stderr.flush()

def argument(arg):
    if arg.startswith('--'):
        if '=' in arg:
            key = arg[2:arg.index('=')]
            value = arg[arg.index('=') + 1:]
            return (key, value)
        else:
            return (arg[2:], None)
    return None


if __name__ == '__main__':
    a = AnagramFinder('dictionary/output.txt')
    words = []
    for arg in sys.argv[1:]:
        arg_found = argument(arg)
        if arg_found is None:
            words.append(arg)
        else:
            key = arg_found[0]
            value = arg_found[1]
            if key == 'procs':
                a.proc_count = int(value)
            elif key == 'cache':
                a.caching_enabled = True
            elif key == 'cachesize':
                a.cache_limit = int(value)
            elif key == 'help':
                print("Usage: ./anagram.py [<OPTIONS>] <WORDS>")
                print()
                print("Options:")
                print("    --procs=<N>     Runs N many processes, default is 1")
                print("    --cache         Enables cache, default is off")
                print("    --cachesize=<N> Sets the max number of results to cache, default 1000000")
                print("    --help          Displays this help")
                print()
                sys.exit()
            else:
                raise Exception("No such argument: {}".format(key))
    results = a.find(''.join(words), output)
    sys.stderr.write("\n")
    sys.stderr.flush()
    for result in results:
        print(result)
