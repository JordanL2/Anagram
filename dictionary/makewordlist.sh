#!/bin/sh

# Convert line endings, filter out words that aren't single words, trim whitespace, add additional words, sort, remove suppressed words
tr -d '\015' < ORIGINAL.txt | grep -E "^\S+\s*$" | sed -e "s/\\s+//g" | cat - additional.txt | sort -u | comm -23 - suppress.txt > output.txt
