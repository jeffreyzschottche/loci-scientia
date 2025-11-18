#!/usr/bin/env bash

REPO="jeffreyzschottche/loci-scientia"

current_title=""
current_body=""
processing_block=false

flush_issue() {
  if [ -n "$current_title" ]; then
    echo ""
    echo "Maak issue: $current_title"
    echo "-----------------------------------"

    gh issue create \
      --repo "$REPO" \
      --title "$current_title" \
      --body "$current_body"
  fi

  current_title=""
  current_body=""
}

while IFS= read -r line || [ -n "$line" ]; do

  # Begin van een nieuw blok?
  if [[ "$line" =~ ^(Feature|Chore)\ #[0-9]+: ]]; then
    # Als er al een blok bezig was → issue maken
    flush_issue
    processing_block=true

    # Titelregel splitsen op :::
    if [[ "$line" == *":::"* ]]; then
      current_title="${line%%:::*}"
      current_body="${line#*:::}"
    else
      # Mocht er ooit een blok zonder ::: zijn (bijv. typefout)
      current_title="$line"
      current_body=""
    fi

  else
    # Regel hoort bij de body van het huidige blok
    if [ "$processing_block" = true ]; then
      current_body="$current_body"$'\n'"$line"
    fi
  fi

done < issues.txt

# Last block flushen
flush_issue
