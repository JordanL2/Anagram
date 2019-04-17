#!/bin/sh

# Convert line endings, filter out words that aren't pure lowercase a-z and at least three letters long, trim whitespace
tr -d '\015' < brit-a-z.txt | grep -E "^\S\S\S+\s*$" | sed -e "s/\\s+//g" > output.txt
# Append list of allowed 1-2 letter words
cat shortwords.txt >> output.txt
