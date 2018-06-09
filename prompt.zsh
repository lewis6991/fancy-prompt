update_prompt() {
    cd $1
    rc=$2
    cols=$3
    ~/.prompt zsh $rc 0 $cols
}

refresh_prompt() {
    PROMPT=$(echo "$3")
    zle reset-prompt
}

async_start_worker      gitprompt
async_register_callback gitprompt refresh_prompt

prompt_precmd() {
    rc=$?
    cols=$(tput cols)
    # Set initial prompt without scm info
    PROMPT=$(echo "$(~/.prompt zsh $rc 1 $cols)")
    async_flush_jobs gitprompt
    async_job gitprompt update_prompt "$(pwd)" "$rc" "$cols"
}

add-zsh-hook precmd prompt_precmd
