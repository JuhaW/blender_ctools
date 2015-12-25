#! /bin/bash

cd ~/tmp

# メインリポジトリ
mkdir main
cd main
touch test
git init
git add test
git commit -m '1st'

# ベアリポジトリ作成
cd ..
git clone --bare main

# メインリポジトリでベアリポジトリを登録、push
cd main
git remote add origin sui@crmo:/home/sui/tmp/main.git
git push -u origin master

# subtree用のリポジトリ
cd ..
mkdir sub
cd sub
touch test
git init
git add test
git commit -m '1st'

# subtree用のベアリポジトリ作成
cd ..
git clone --bare sub

# サブリポジトリでベアリポジトリを登録、push
cd sub
git remote add origin sui@crmo:/home/sui/tmp/sub.git
git push -u origin master

# メインリポジトリにサブのベアリポジトリを追加
cd ../main
git subtree add --prefix=sub sui@crmo:/home/sui/tmp/sub.git master --squash

# サブに何か追加してみる
touch sub/subtree_test
git add sub/subtree_test
git commit -m 'subtree test'
git push origin master
git subtree push --prefix=sub sui@crmo:/home/sui/tmp/sub.git master --squash

git pull origin master

# こちらにもファイルが追加されている
cd ../sub
git pull origin master
