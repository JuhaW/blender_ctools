#! /bin/bash

cd ~/tmp

# メインリポジトリ
mkdir main
cd main
touch test
git init
git add test
git commit -m 'main init'

# ベアリポジトリ作成
cd ..
git clone --bare main

# メインリポジトリでベアリポジトリを登録、push
cd main
# デフォルトポート(22)なら sui@crmo:/home/sui/tmp/main.git でよい
git remote add origin ssh://sui@crmo:65432/home/sui/tmp/main.git
git push -u origin master

# subtree用のリポジトリ
cd ..
mkdir sub
cd sub
touch test
git init
git add test
git commit -m 'sub init'

# subtree用のベアリポジトリ作成
cd ..
git clone --bare sub

# サブリポジトリでベアリポジトリを登録、push
cd sub
git remote add origin ssh://sui@crmo:65432/home/sui/tmp/sub.git
git push -u origin master

# メインリポジトリにサブのベアリポジトリを追加
cd ../main
git subtree add --prefix=sub ssh://sui@crmo:65432/home/sui/tmp/sub.git master --squash

# メインリポジトリの中でサブに何か追加してみる
touch sub/subtree_test
git add sub/subtree_test
git commit -m 'subtree change in main'
git push origin master
git subtree push --prefix=sub ssh://sui@crmo:65432/home/sui/tmp/sub.git master # --squash は 'add', 'merge', 'pull' のみ

git pull origin master

# サブの方にもファイルが追加されている
cd ../sub
git pull origin master

# サブに変更を加えてメインで取り込む
echo 'subtree_change' > subtree_test
git commit -am 'subtree change in sub'
git push
cd ../main
git pull  # これでは変化無し
git subtree pull --prefix=sub ssh://sui@crmo:65432/home/sui/tmp/sub.git master --squash  # これで取り込みとマージが行われる
git push

