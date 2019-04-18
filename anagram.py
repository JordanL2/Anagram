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
        for word in self.words:
            self.word_letter_map[word] = self.word_to_letter_map(word)

    def find(self, letters, display=None):
        # Turn string into a map of each letter and the number of times it occurs
        letter_map = self.word_to_letter_map(letters)

        args = [[letter_map, display]] * self.proc_count
        results = self.multiprocess_job(self.do_proc, args)
        return self.dedupe_results(results)

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
                return self.result_cache[key][0]
            else:
                cache_stop = self.result_cache[key][1]

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

        results = []

        for i in range(start, self.word_count, max_t):
            if self.caching_enabled and cache_stop is not None and i >= cache_stop and key in self.result_cache:
                results.extend(self.result_cache[key][0])
                break
            word = self.words[i]
            if display is not None:
                display(t, i + 1, self.word_count)
            # See if this word can be found in the letters we're searching,
            # and if so, what letters are left over afterwards
            found, letters_left = self.word_in_letters(word, letter_map)
            if found:
                if self.letter_map_count(letters_left) == 0:
                    # There are no remaining letters, so we have a result
                    results.append([word])
                else:
                    # There are remaining letters, so we have to see what words
                    # can be found in them, combining the results with this word
                    next_find = self.search_wordlist(letters_left, 0, 1, i, False)
                    for n in next_find:
                        results.append([word] + n)

        if display is not None:
            display(t, self.word_count, self.word_count)
        
        if self.caching_enabled:
            if not toplevel:
                if key not in self.result_cache:
                    self.result_cache[key] = [results, start, 0]
                elif self.result_cache[key][1] > start:
                    self.result_cache[key] = [results, start, self.result_cache[key][2]]
            if len(self.result_cache) >= self.cache_limit:
                self.clear_cache()

        return results

    def clear_cache(self):
        amount_to_remove = self.cache_limit * self.cache_clear_fraction
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

    def dedupe_results(self, results):
        new_result = set()
        for result in results:
            new_result.add(' '.join(sorted(result)))
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
                print("    --cachesize=<N> Sets the maximum number of results to cache, default is")
                print("                    1000000 results. Each result uses roughly 300 bytes of")
                print("                    memory per process.")
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
