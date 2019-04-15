#!/bin/sh

tr -d '\015' < brit-a-z.txt | grep -E "^[a-z]+\s*$" | grep -Ev '^\w\w\s*$' | sed -e "s/\\s+//g" > britwordlist.txt
cat allowed2letters.txt >> britwordlist.txt
