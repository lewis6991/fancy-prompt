update_prompt() {
    cd $1
    echo "$(~/.prompt zsh $2)"
}

refresh_prompt() {
    PROMPT="$3"
    zle reset-prompt
}

async_start_worker      gitprompt
async_register_callback gitprompt refresh_prompt

prompt_precmd() {
    rc=$?
    PROMPT=$(echo "$(~/.prompt zsh $rc 1)")
    async_flush_jobs gitprompt
    async_job gitprompt update_prompt $(pwd) $rc
}

add-zsh-hook precmd prompt_precmd
