#!/bin/sh

# Convert line endings, filter out words that aren't pure lowercase a-z and at least three letters long, trim whitespace
tr -d '\015' < brit-a-z.txt | grep -E "^\S\S\S\S+\s*$" | sed -e "s/\\s+//g" > unsortedoutput.txt
# Append list of allowed 1-2 letter words
cat shortwords.txt >> unsortedoutput.txt
cat unsortedoutput.txt | sort -u > output.txt
