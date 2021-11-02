cmd_timer_preexec() {
    prompt_timer=${prompt_timer:-$SECONDS}
}

# Try to lower the priority of the worker so that disk heavy operations
# like `git status` has less impact on the system responsivity.
prompt_async_renice() {
    if command -v renice >/dev/null; then
        command renice +15 -p $$ > /dev/null
    fi

    if command -v ionice >/dev/null; then
        command ionice -c 3 -p $$ > /dev/null
    fi
}

# The output of this is given as $3 of refresh_prompt_callback (the callback)
update_prompt() {
    local rc="$1" timer_show="$2"
    ~/.prompt zsh "$rc" 0 "$timer_show"
}

refresh() {
    local rc="$1" timer_show="$2"

    async_stop_worker       gitprompt
    async_start_worker      gitprompt -z
    async_register_callback gitprompt refresh_prompt_callback
    async_worker_eval       gitprompt prompt_async_renice
    async_job               gitprompt update_prompt "$rc" "$timer_show"
}

refresh_prompt_callback() {
    local job="$1" err="$2" output="$3" outerr="$5" next_pending="$6"

    if (( next_pending )); then
        return
        # echo "ERROR 37"
    fi

    case $job in
        \[async])
            # Async worker has crashed
            if (( err == 2 )); then
                # ZLE watcher detected an error on the worker fd.
                # Triggered when used with marlonrichert/zsh-autocomplete
                # echo "ERROR 46 ($err): $outerr"
                refresh 0 0
            else
                echo "ERROR 47 ($err): $outerr"
            fi
            ;;
        \[async/eval])
            if (( err )); then
                # async_worker_eval failed
                echo "ERROR 45 ($err): $outerr"
            fi
            ;;
        update_prompt)
            last_prompt="$PROMPT"
            PROMPT="$(echo -n $output)"
            if [[ $last_prompt != $PROMPT ]]; then
                zle .reset-prompt
            fi
            ;;
    esac
}

prompt_precmd() {
    local rc="$?"
    local timer_show
    local gray='%{\e[0;90m%}'
    local reset='%{\e[0m%}'

    if (( prompt_timer )); then
        timer_show=$((SECONDS - prompt_timer))
        timer_show=$(printf '%.*f\n' 0 "$timer_show")
        unset prompt_timer
    fi

    RPROMPT=$(echo -n "$gray$(date +"%1e/%1m %H:%M")$reset")
    PROMPT=$(echo -n "$(~/.prompt zsh 0 1 "")")
    refresh "$rc" "$timer_show"
}

if ! typeset -f async_job > /dev/null; then
    echo "error: fancy-prompt requires zsh-async"
else
    add-zsh-hook preexec cmd_timer_preexec
    add-zsh-hook precmd  prompt_precmd
fi

