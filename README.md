Features
========
* Provides a nice colourful prompt.
* Gives you basic information about your git or svn checkout.
* Supports bash, csh and tcsh.

Installation for Bash
=====================
Add the following to your `.bashrc`:
```bash
export PROMPT_COMMAND=__prompt_command

function __prompt_command() {
    EXIT=$?
    PS1=`~/.prompt bash ${EXIT}`
}
```

Installation for Csh/Tcsh
=========================
Add the following to your `.cshrc`:
```csh
alias precmd 'set prompt="`~/.prompt csh $?`"'
```
