fcp_set_prompt() {
    last_prompt="$PROMPT"
    PROMPT="$(echo -n $1)"
    if [[ $last_prompt != $PROMPT ]] && zle ; then
        zle reset-prompt
    fi
}

fcp_cmd_timer_preexec() {
    local OSC133_EXEC="\e]133;C\e\\"
    # Omit OSC133 command executed
    print -n "$OSC133_EXEC"
    prompt_timer=${prompt_timer:-$SECONDS}
}

# Try to lower the priority of the worker so that disk heavy operations
# like `git status` has less impact on the system responsiveness.
fcp_prompt_async_renice() {
    if command -v renice >/dev/null; then
        command renice +15 -p $$ > /dev/null
    fi

    if command -v ionice >/dev/null; then
        command ionice -c 3 -p $$ > /dev/null
    fi
}

# The output of this is given as $3 of refresh_prompt_callback (the callback)
fcp_update_prompt_sub() {
    local rc="$1"
    local timer_show="$2"
    $BASE/prompt zsh "$rc" 0 "$timer_show"
}

fcp_refresh() {
    local rc="$1"
    local timer_show="$2"

    async_stop_worker       gitprompt
    async_start_worker      gitprompt -z
    async_register_callback gitprompt fcp_refresh_prompt_callback
    async_worker_eval       gitprompt fcp_prompt_async_renice
    async_job               gitprompt fcp_update_prompt_sub "$rc" "$timer_show"
}

fcp_refresh_prompt_callback() {
    local job="$1"
    local err="$2"
    local output="$3"
    local outerr="$5"
    local next_pending="$6"

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
                fcp_refresh 0 0
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
        fcp_update_prompt_sub)
            fcp_set_prompt "$output"
            ;;
    esac
}

fcp_prompt_precmd() {
    local rc="$?"
    local timer_show

    if (( prompt_timer )); then
        timer_show=$((SECONDS - prompt_timer))
        timer_show=$(printf '%.*f\n' 0 "$timer_show")
        unset prompt_timer
    fi

    fcp_set_prompt "$($BASE/prompt zsh 0 1 "")"
    fcp_refresh "$rc" "$timer_show"
}

add-zsh-hook preexec fcp_cmd_timer_preexec
add-zsh-hook precmd  fcp_prompt_precmd
