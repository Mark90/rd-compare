#!/bin/bash

# Compares a 'base' version against a 'new' version of redis_dict
# 
# Dependencies: 
# - redis instance
# - python 2.7 env with requirements.txt

# Configure branch and commit of the 'base' version
branch_base=master
commit_base=b673d7df2c0f15e76ae9e600d66edd289787c000

# Configure branch and commit of the 'new' version
branch_new=v2
commit_new=

# Interpreter to use
py=python 

function die() {
  echo -e "Error: $1"
  exit 1
}

$py -c "import redis" 2>/dev/null || die "redis package not installed"

dir_base=redis_dict_${branch_base}
dir_new=redis_dict_${branch_new}

# Fetch the base and new version into separate directories, optionally reset them to specific commits
git clone --quiet --branch=$branch_base https://github.com/Attumm/redis-dict $dir_base >/dev/null || die "failed to checkout 'base' branch $branch_base"
[ -n "$commit_base" ] && cd $dir_base && git reset --hard ${commit_base} >/dev/null && cd ..
echo -e "\n## 'base' branch $branch_base is at commit:\n`git --git-dir=$dir_base/.git log -1 | cat`\n" 

git clone --quiet --branch=$branch_new https://github.com/Attumm/redis-dict $dir_new >/dev/null || die "failed to checkout 'new' branch $branch_new"
[ -n "$commit_new" ] && cd $dir_new && git reset --hard ${commit_new} >/dev/null && cd ..
echo -e "\n## 'new' branch $branch_new is at commit:\n`git --git-dir=$dir_new/.git log -1 | cat`\n" 

# Make each folder a python package
touch $dir_base/__init__.py $dir_new/__init__.py

# Run comparison tests
V1=$dir_base V2=$dir_new $py compare_versions.py -v

# Cleanup
rm -rf "$dir_base" "$dir_new"
