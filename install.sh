#!/bin/bash

function link_file {
    rm -rf $2
    ln -srv $1 $2
    # If last command failed then coreutils probably doesn't support -r switch
    # (<8.16)
    if [ $? -ne 0 ]; then
        echo "link failed... attempting alternate command that doesn't use -r"
        local current_dir=$(pwd)
        pushd $(dirname $2)
        ln -sv $current_dir/$1 $(basename $2)
        popd
    fi
}

link_file $(dirname "$BASH_SOURCE")/prompt ~/.prompt
