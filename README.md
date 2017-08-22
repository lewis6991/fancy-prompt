Features
========
* Provides a nice colourful prompt.
* Gives you basic information about your git or svn checkout.
* Supports bash, csh and tcsh.

Screenshot
==========

![img](screen.png)

Installation for Bash
=====================
```bash
./install.sh
```
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
```bash
./install.sh
```
Add the following to your `.cshrc`:
```csh
alias precmd 'set prompt="`~/.prompt csh $?`"'
```
