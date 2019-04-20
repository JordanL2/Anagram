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
        self.fast_path_iter_rel_speed = 0.3

        self.result_batch_size = 1000

        # Load dictionary of words
        self.normalised_word_map = {}
        f = open(filename)
        for line in f:
            word = line.strip()
            letter_map = self.word_to_letter_map(word)
            key = self.letter_map_to_key(letter_map)
            if key not in self.normalised_word_map:
                self.normalised_word_map[key] = (key, letter_map, [])
            self.normalised_word_map[key][2].append(word)
        f.close()
        
        # Sort the word list by word length, longest words first
        self.letter_map_to_words = sorted(self.normalised_word_map.values(), key=lambda x: len(x[0]), reverse=True)
        self.letter_map_to_words_count = len(self.letter_map_to_words)
        self.letter_map_reverse = dict([(l[0], i) for i, l in enumerate(self.letter_map_to_words)])

        # Index of word list by length, so when we only have eg 5 letters,
        # we can jump to the part of the list with words of that length
        self.word_length_index = {}
        for i, lmw in enumerate(self.letter_map_to_words):
            l = len(lmw[0])
            if l not in self.word_length_index:
                self.word_length_index[l] = i

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
                        results.extend(r)
                    except Empty:
                        break

        # Add the last of the queue to the results, and return them
        while not queue.empty():
            results.extend(queue.get())
        return results

    def do_proc(self, t, max_t, queue, letter_map, display):
        self.result_cache = {}
        results = self.search_wordlist(letter_map, t, max_t, t, 0, display)
        for i in range(0, len(results), self.result_batch_size):
            next_i = i + self.result_batch_size
            if next_i >= len(results):
                queue.put(results[i:])
            else:
                queue.put(results[i:next_i])

    def search_wordlist(self, letter_map, t, max_t, start, level, display=None):
        toplevel = level == 0
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

        # If possible, we can jump to the part of the word list with
        # the words that have the number of letters that we're searching
        if letter_count in self.word_length_index:
            if self.word_length_index[letter_count] > start:
                if max_t > 1:
                    rem = start % max_t
                    start = self.word_length_index[letter_count]
                    start_rem = start % max_t
                    rem_diff = rem - start_rem
                    start += rem_diff
                else:
                    start = self.word_length_index[letter_count]

        results = []

        # If we have a small number of letters, it's faster to iterate through every possible
        # combination of letters and see if it's an anagram of any words, although each iteration
        # of this path is roughly 8x slower than the default path
        letter_combinations = 1
        for c in letter_map.values():
            letter_combinations *= (c + 1)
        if not toplevel and self.fast_path_enabled and letter_combinations < (self.letter_map_to_words_count - start) * self.fast_path_iter_rel_speed and cache_stop is None:

            letter_index_length = len(letter_map)
            # Mapping of index to letter
            index_to_letter = []
            # Mapping of index to count of that letter
            letter_max = []
            for l in sorted(letter_map.keys()):
                index_to_letter.append(l)
                letter_max.append(letter_map[l])
            # Index as we step through every combination of letters
            letter_index = letter_max.copy()

            while True:
                
                # Put together the letters we're looking at this iteration
                letters = ''
                for i in range(0, letter_index_length):
                    letters += index_to_letter[i] * letter_index[i]
                if letters == '':
                    break
                
                # Find the words that are anagrams of these letters
                if letters in self.normalised_word_map:
                    wordi = self.letter_map_reverse[letters]
                    if wordi >= start:
                        words = self.normalised_word_map[letters][2]
                        
                        # Calculate what letters are left over
                        letters_left = letter_map.copy()
                        for i in range(0, letter_index_length):
                            l = index_to_letter[i]
                            letters_left[l] -= letter_index[i]
                            if letters_left[l] == 0:
                                del letters_left[l]
                        letters_left_count = self.letter_map_count(letters_left)

                        # Store these results
                        if letters_left_count == 0:
                            for word in words:
                                self.add_to_results(results, wordi, word)
                        else:
                            next_find = self.search_wordlist(letters_left, 0, 1, wordi, level + 1)
                            for word in words:
                                for n in next_find:
                                    self.add_to_results(results, wordi, word + ' ' + n)

                # Decrement index
                letter_index[-1] -= 1
                for i in range(letter_index_length - 1, -1, -1):
                    if letter_index[i] == -1:
                        letter_index[i] = letter_max[i]
                        letter_index[i - 1] -= 1
                    else:
                        break

        else:

            # Otherwise, we iterate through all the words and see if they can be made
            # using the letters we have

            for wordi in range(start, self.letter_map_to_words_count, max_t):
                if self.caching_enabled and cache_stop is not None and wordi >= cache_stop and key in self.result_cache:
                    self.merge_results(results, self.result_cache[key][0])
                    break
                word_letter_map = self.letter_map_to_words[wordi][1]
                if toplevel and display is not None:
                    display(t, wordi + 1, self.letter_map_to_words_count)
                # See if this word can be found in the letters we're searching,
                # and if so, what letters are left over afterwards
                found, letters_left = self.word_in_letters(word_letter_map, letter_map)
                if found:
                    words = self.letter_map_to_words[wordi][2]
                    if self.letter_map_count(letters_left) == 0:
                        # There are no remaining letters, so we have a result
                        for word in words:
                            self.add_to_results(results, wordi, word)
                    else:
                        # There are remaining letters, so we have to see what words
                        # can be found in them, combining the results with this word
                        next_find = self.search_wordlist(letters_left, 0, 1, wordi, level + 1)
                        for word in words:
                            for n in next_find:
                                self.add_to_results(results, wordi, word + ' ' + n)
                if toplevel and self.caching_enabled:
                    self.clear_cache()

        if toplevel and display is not None:
            display(t, self.letter_map_to_words_count, self.letter_map_to_words_count)
        
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

    def word_in_letters(self, word_letter_map, letter_map):
        for letter in word_letter_map.keys():
            if letter not in letter_map or word_letter_map[letter] > letter_map[letter]:
                return False, None
        letters_left = letter_map.copy()
        for letter in word_letter_map.keys():
            letters_left[letter] -= word_letter_map[letter]
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
