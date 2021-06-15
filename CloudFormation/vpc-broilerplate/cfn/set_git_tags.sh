#!/bin/bash

# gets the current git branch
function parse_git_branch() {
  git branch --no-color 2> /dev/null | sed -e '/^[^*]/d' -e "s/* \(.*\)/\1/"
}

# get last commit hash prepended with @ (i.e. @8a323d0)
function parse_git_hash() {
  git rev-parse --short HEAD 2> /dev/null | sed "s/\(.*\)/\1/"
}

python3 ./update_cfn-cli-param.py -i ./cfn-cli.yaml -p au:git:commit -v $(parse_git_hash)
python3 ./update_cfn-cli-param.py -i ./cfn-cli.yaml -p au:git:branch -v $(parse_git_branch)