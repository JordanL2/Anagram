#!/usr/bin/python3

import sys
import multiprocessing
from queue import Empty
from time import sleep
import pprint


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

        self.max_key_size = 30

        # Load dictionary of words
        self.words = []
        f = open(filename)
        for line in f:
            word = line.strip()
            self.words.append(word)
        f.close()

    def find(self, letters, display=None):
        # Turn string into a map of each letter and the number of times it occurs
        letter_map = self.word_to_letter_map(letters)

        args = [[letter_map, display]] * self.proc_count
        results = self.multiprocess_job(self.do_proc, args)
        return self.sort_results(results)

    def sort_results(self, results):
        new_result = set()
        for result in results:
            new_result.add(result)
        return sorted(list(new_result))

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
        self.init_wordlist(letter_map)

        self.result_cache = {}
        results = self.search_wordlist(letter_map, t, max_t, display)
        for i in range(0, len(results), self.result_batch_size):
            next_i = i + self.result_batch_size
            if next_i >= len(results):
                queue.put(results[i:])
            else:
                queue.put(results[i:next_i])

    def init_wordlist(self, letter_map):
        # Create a list of all words organised by the letters they contain,
        # so words that are anagrams of each other are grouped together
        self.normalised_word_map = {}
        for word in self.words:
            word_letter_map = self.word_to_letter_map(word)
            found, letters_left = self.word_in_letters(word_letter_map, letter_map)
            if found:
                key = self.letter_map_to_key(word_letter_map)
                if key not in self.normalised_word_map:
                    self.normalised_word_map[key] = (key, word_letter_map, [])
                self.normalised_word_map[key][2].append(word)

        # Sort the word list by word length, longest words first
        self.letter_map_to_words = sorted(self.normalised_word_map.values(), key=lambda x: len(x[0]), reverse=True)
        self.letter_map_to_words_count = len(self.letter_map_to_words)

        # Make the word tree
        self.word_tree = {}
        for lmw in self.letter_map_to_words:
            tree_pointer = self.word_tree
            for l in lmw[0]:
                if l not in tree_pointer:
                    tree_pointer[l] = {}
                tree_pointer = tree_pointer[l]
            tree_pointer['key'] = lmw[0]
            tree_pointer['letter_map'] = lmw[1]
            tree_pointer['words'] = lmw[2]

    def search_wordlist(self, letter_map, t, max_t, display=None):
        results = []

        for wordi in range(t, self.letter_map_to_words_count, max_t):
            word_letter_map = self.letter_map_to_words[wordi][1]
            if display is not None:
                display(t, wordi + 1, self.letter_map_to_words_count)
            # See if this word can be found in the letters we're searching,
            # and if so, what letters are left over afterwards
            found, letters_left = self.word_in_letters(word_letter_map, letter_map)
            if found:
                words = self.letter_map_to_words[wordi][2]
                word_key = self.letter_map_to_words[wordi][0]
                if len(letters_left) == 0:
                    # There are no remaining letters, so we have a result
                    for word in words:
                        results.append(word)
                else:
                    # There are remaining letters, so we have to see what words
                    # can be found in them, combining the results with this word
                    next_find = self.search_wordtree(letters_left, word_key)
                    for word in words:
                        for n in next_find:
                            results.append(' '.join(sorted((word + ' ' + n).split(' '))))

            if self.caching_enabled:
                self.clear_cache()

        if display is not None:
            display(t, self.letter_map_to_words_count, self.letter_map_to_words_count)

        return results

    def search_wordtree(self, letter_map, comparison_key):
        key = self.letter_map_to_key(letter_map)
        cache_stop = None
        if self.caching_enabled and key in self.result_cache:
            self.result_cache[key][2] += 1
            if not self.key_is_after(self.result_cache[key][1], comparison_key):
                return self.results_as_list(self.result_cache[key][0], comparison_key)
            else:
                cache_stop = self.result_cache[key][1]

        results = []

        find_word_results = self.find_words(letter_map, comparison_key, self.word_tree)
        find_word_results.sort(key=lambda x: self.normalise_key(x[1]['key']))

        for find_word_result in find_word_results:
            letters_left = find_word_result[0]
            tree_pointer = find_word_result[1]
            words = tree_pointer['words']
            word_key = tree_pointer['key']
            if self.caching_enabled and cache_stop is not None and not self.key_is_after(cache_stop, word_key) and key in self.result_cache:
                self.merge_results(results, self.result_cache[key][0])
                break
            if len(letters_left) == 0:
                self.add_results(results, words, word_key)
            else:
                next_find = self.search_wordtree(letters_left, word_key)
                results_to_add = []
                for word in words:
                    for n in next_find:
                        results_to_add.append(word + ' ' + n)
                self.add_results(results, results_to_add, word_key)

        if self.caching_enabled:
            if key not in self.result_cache:
                self.result_cache[key] = [results, comparison_key, 0]
            elif self.key_is_after(self.result_cache[key][1], comparison_key):
                self.result_cache[key] = [results, comparison_key, self.result_cache[key][2] + 1]

        return self.results_as_list(results)

    def find_words(self, letter_map, comparison_key, tree_pointer):
        if 'key' in tree_pointer and self.key_is_after(comparison_key, tree_pointer['key']):
            return []
        results = []

        if 'words' in tree_pointer:
            results.append((letter_map, tree_pointer))
        
        for l in sorted(letter_map):
            if l in tree_pointer:
                new_letter_map = letter_map.copy()
                new_letter_map[l] -= 1
                if new_letter_map[l] == 0:
                    del new_letter_map[l]
                results.extend(self.find_words(new_letter_map, comparison_key, tree_pointer[l]))

        return results

    def add_results(self, results, results_to_add, word_key):
        if len(results_to_add) > 0:
            results.append((word_key, results_to_add))

    def merge_results(self, results1, results2):
        results1.extend(results2)

    def results_as_list(self, results, word_key=None):
        results_to_return = []
        for result in results:
            if word_key is None or not self.key_is_after(word_key, result[0]):
                results_to_return.extend(result[1])
        return results_to_return

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
        return True, self.letter_map_subtract(letter_map, word_letter_map)

    def word_to_letter_map(self, word):
        letter_map = {}
        for letter in word:
            letter = letter.lower()
            if letter in self.allowed_letters:
                if letter not in letter_map:
                    letter_map[letter] = 0
                letter_map[letter] += 1
        return letter_map

    def letter_map_to_key(self, letter_map):
        return ''.join([l * n for l, n in sorted(letter_map.items())])

    def letter_map_subtract(self, letter_map1, letter_map2):
        new_letter_map = letter_map1.copy()
        for letter in letter_map2.keys():
            new_letter_map[letter] -= letter_map2[letter]
            if new_letter_map[letter] == 0:
                del new_letter_map[letter]
        return new_letter_map

    def key_is_after(self, key1, key2):
        return self.normalise_key(key1) > self.normalise_key(key2)

    def normalise_key(self, key):
        return key + '|' * (self.max_key_size - len(key))


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
